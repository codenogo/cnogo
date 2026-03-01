"""JavaScript language parser using tree-sitter.

Extends the TypeScript parser approach for JavaScript-specific patterns:
CommonJS require(), module.exports, and JSX. Uses tree-sitter-javascript grammar.
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_javascript

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

JS_LANGUAGE = tree_sitter.Language(tree_sitter_javascript.language())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_name(node: tree_sitter.Node, name_types: tuple[str, ...] = ("identifier", "property_identifier")) -> str:
    """Get the name from a definition node."""
    for child in node.children:
        if child.type in name_types:
            return _get_text(child)
    return ""


class JavaScriptParser(LanguageParser):
    """Parser for JavaScript source files using tree-sitter."""

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser(JS_LANGUAGE)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse JavaScript source and return extracted IR."""
        tree = self._parser.parse(content.encode("utf-8"))
        result = ParseResult()
        self._walk(tree.root_node, result, enclosing_class="", enclosing_func="")
        return result

    def _walk(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Recursively walk the AST extracting information."""
        handler = self._handlers.get(node.type)
        if handler:
            handler(self, node, result, enclosing_class, enclosing_func)
        else:
            for child in node.children:
                self._walk(child, result, enclosing_class, enclosing_func)

    def _handle_function(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract function declaration."""
        name = _get_name(node)
        if not name:
            return

        kind = "method" if enclosing_class else "function"
        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        params = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)

        sig = f"function {name}{params}"

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind=kind,
                start_line=start_line,
                end_line=end_line,
                signature=sig,
                class_name=enclosing_class,
            )
        )

        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _handle_method(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract method definition inside a class."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        params = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)

        sig = f"{name}{params}"

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="method",
                start_line=start_line,
                end_line=end_line,
                signature=sig,
                class_name=enclosing_class,
            )
        )

        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _handle_class(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract class declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Extract heritage (JS only has extends, no implements)
        # In JS tree-sitter, class_heritage children are: "extends" keyword + identifier
        # (unlike TS which wraps in extends_clause)
        heritage_text = ""
        for child in node.children:
            if child.type == "class_heritage":
                heritage_text = _get_text(child)
                for sub in child.children:
                    if sub.type in ("identifier", "member_expression"):
                        parent = _get_text(sub)
                        result.heritage.append((name, parent, "extends"))
                        result.type_refs.append(
                            TypeRef(name=parent, kind="base_class", line=sub.start_point.row + 1)
                        )

        sig = f"class {name}"
        if heritage_text:
            sig += f" {heritage_text}"

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="class",
                start_line=start_line,
                end_line=end_line,
                signature=sig,
                class_name=enclosing_class,
            )
        )

        for child in node.children:
            if child.type == "class_body":
                for stmt in child.children:
                    self._walk(stmt, result, name, "")

    def _handle_import(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract ESM import statement."""
        line = node.start_point.row + 1
        module = ""
        names: list[str] = []

        for child in node.children:
            if child.type == "string":
                module = _get_text(child).strip("\"'")
            elif child.type == "import_clause":
                for sub in child.children:
                    if sub.type == "identifier":
                        names.append(_get_text(sub))
                    elif sub.type == "named_imports":
                        for spec in sub.children:
                            if spec.type == "import_specifier":
                                for name_node in spec.children:
                                    if name_node.type == "identifier":
                                        names.append(_get_text(name_node))
                                        break
                    elif sub.type == "namespace_import":
                        for ns in sub.children:
                            if ns.type == "identifier":
                                names.append(f"* as {_get_text(ns)}")
                                break

        if module:
            result.imports.append(ImportInfo(module=module, names=names, line=line))

    def _handle_export(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract export statement — recurse into exported declarations."""
        for child in node.children:
            self._walk(child, result, enclosing_class, enclosing_func)

    def _handle_call(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract function/method call."""
        if not node.children:
            return

        callee_node = node.children[0]
        callee = ""
        if callee_node.type == "identifier":
            callee = _get_text(callee_node)
        elif callee_node.type == "member_expression":
            callee = _get_text(callee_node)
        else:
            callee = _get_text(callee_node)

        if callee:
            result.calls.append(
                CallInfo(
                    caller=enclosing_func,
                    callee=callee,
                    line=node.start_point.row + 1,
                    confidence=1.0,
                )
            )

        for child in node.children:
            if child.type == "arguments":
                for arg in child.children:
                    self._walk(arg, result, enclosing_class, enclosing_func)

    def _handle_lexical_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Handle const/let/var — detect arrow functions and require()."""
        for child in node.children:
            if child.type == "variable_declarator":
                self._handle_variable_declarator(child, result, enclosing_class, enclosing_func)

    def _handle_variable_declarator(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Handle a single variable declarator."""
        name = ""
        value_node = None
        for child in node.children:
            if child.type == "identifier":
                name = _get_text(child)
            elif child.type == "arrow_function":
                value_node = child
            elif child.type == "call_expression":
                value_node = child

        if name and value_node and value_node.type == "arrow_function":
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1
            params = ""
            for child in value_node.children:
                if child.type == "formal_parameters":
                    params = _get_text(child)
            kind = "method" if enclosing_class else "function"
            sig = f"const {name} = {params} =>"
            result.symbols.append(
                SymbolInfo(
                    name=name,
                    kind=kind,
                    start_line=start_line,
                    end_line=end_line,
                    signature=sig,
                    class_name=enclosing_class,
                )
            )
            func_name = f"{enclosing_class}.{name}" if enclosing_class else name
            for child in value_node.children:
                if child.type == "statement_block":
                    for stmt in child.children:
                        self._walk(stmt, result, enclosing_class, func_name)

        # Recurse to find calls
        for child in node.children:
            self._walk(child, result, enclosing_class, enclosing_func)

    def _handle_arrow_function(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Recurse into arrow function body."""
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, enclosing_func)

    _handlers: dict[str, object] = {
        "function_declaration": _handle_function,
        "class_declaration": _handle_class,
        "method_definition": _handle_method,
        "import_statement": _handle_import,
        "export_statement": _handle_export,
        "call_expression": _handle_call,
        "arrow_function": _handle_arrow_function,
        "lexical_declaration": _handle_lexical_declaration,
        "variable_declaration": _handle_lexical_declaration,
    }
