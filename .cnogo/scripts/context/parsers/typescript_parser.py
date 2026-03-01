"""TypeScript language parser using tree-sitter.

Extracts symbols, imports, calls, heritage, and type references from
TypeScript source code (including interfaces, type aliases, and enums).
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_typescript

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

TS_LANGUAGE = tree_sitter.Language(tree_sitter_typescript.language_typescript())
TSX_LANGUAGE = tree_sitter.Language(tree_sitter_typescript.language_tsx())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_name(node: tree_sitter.Node, name_types: tuple[str, ...] = ("identifier", "type_identifier", "property_identifier")) -> str:
    """Get the name from a definition node."""
    for child in node.children:
        if child.type in name_types:
            return _get_text(child)
    return ""


class TypeScriptParser(LanguageParser):
    """Parser for TypeScript source files using tree-sitter."""

    def __init__(self, tsx: bool = False) -> None:
        lang = TSX_LANGUAGE if tsx else TS_LANGUAGE
        self._parser = tree_sitter.Parser(lang)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse TypeScript source and return extracted IR."""
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

        # Build signature
        params = ""
        return_type = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)
            elif child.type == "type_annotation":
                return_type = _get_text(child).lstrip(": ").strip()

        sig = f"function {name}{params}"
        if return_type:
            sig += f": {return_type}"

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

        # Return type ref
        if return_type:
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        # Extract param type annotations
        for child in node.children:
            if child.type == "formal_parameters":
                self._extract_param_types(child, result)

        # Recurse into body
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
        return_type = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)
            elif child.type == "type_annotation":
                return_type = _get_text(child).lstrip(": ").strip()

        sig = f"{name}{params}"
        if return_type:
            sig += f": {return_type}"

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

        if return_type:
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        for child in node.children:
            if child.type == "formal_parameters":
                self._extract_param_types(child, result)

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

        # Build heritage info
        heritage_text = ""
        for child in node.children:
            if child.type == "class_heritage":
                heritage_text = _get_text(child)
                self._extract_heritage(child, name, result)

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

        # Recurse into class body
        for child in node.children:
            if child.type == "class_body":
                for stmt in child.children:
                    self._walk(stmt, result, name, "")

    def _extract_heritage(
        self,
        heritage_node: tree_sitter.Node,
        class_name: str,
        result: ParseResult,
    ) -> None:
        """Extract extends/implements from class_heritage node."""
        for child in heritage_node.children:
            if child.type == "extends_clause":
                for sub in child.children:
                    if sub.type in ("identifier", "type_identifier", "member_expression"):
                        parent = _get_text(sub)
                        result.heritage.append((class_name, parent, "extends"))
                        result.type_refs.append(
                            TypeRef(name=parent, kind="base_class", line=sub.start_point.row + 1)
                        )
            elif child.type == "implements_clause":
                for sub in child.children:
                    if sub.type in ("identifier", "type_identifier", "generic_type"):
                        iface = _get_text(sub)
                        result.heritage.append((class_name, iface, "implements"))
                        result.type_refs.append(
                            TypeRef(name=iface, kind="base_class", line=sub.start_point.row + 1)
                        )

    def _handle_interface(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract interface declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Check for extends
        for child in node.children:
            if child.type == "extends_type_clause":
                for sub in child.children:
                    if sub.type in ("identifier", "type_identifier"):
                        parent = _get_text(sub)
                        result.heritage.append((name, parent, "extends"))

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="interface",
                start_line=start_line,
                end_line=end_line,
                signature=f"interface {name}",
            )
        )

    def _handle_type_alias(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract type alias declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="type_alias",
                start_line=start_line,
                end_line=end_line,
                signature=_get_text(node).rstrip(";").strip(),
            )
        )

    def _handle_enum(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract enum declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="enum",
                start_line=start_line,
                end_line=end_line,
                signature=f"enum {name}",
            )
        )

    def _handle_import(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract import statement."""
        line = node.start_point.row + 1
        module = ""
        names: list[str] = []

        # Find the module string
        for child in node.children:
            if child.type == "string":
                module = _get_text(child).strip("\"'")
            elif child.type == "import_clause":
                names = self._extract_import_names(child)

        if module:
            result.imports.append(
                ImportInfo(module=module, names=names, line=line)
            )

    def _extract_import_names(self, clause_node: tree_sitter.Node) -> list[str]:
        """Extract imported names from an import_clause."""
        names: list[str] = []
        for child in clause_node.children:
            if child.type == "identifier":
                names.append(_get_text(child))
            elif child.type == "named_imports":
                for sub in child.children:
                    if sub.type == "import_specifier":
                        for name_node in sub.children:
                            if name_node.type == "identifier":
                                names.append(_get_text(name_node))
                                break
            elif child.type == "namespace_import":
                for sub in child.children:
                    if sub.type == "identifier":
                        names.append(f"* as {_get_text(sub)}")
                        break
        return names

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
        """Extract a function/method call."""
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

        # Recurse into arguments
        for child in node.children:
            if child.type == "arguments":
                for arg in child.children:
                    self._walk(arg, result, enclosing_class, enclosing_func)

    def _handle_arrow_function(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract arrow function (only when assigned to a variable)."""
        # Arrow functions are handled through variable declarations
        # Recurse into body for calls
        for child in node.children:
            if child.type == "statement_block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, enclosing_func)

    def _handle_lexical_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Handle const/let/var declarations — detect arrow functions and require()."""
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
            if child.type in ("identifier", "property_identifier"):
                name = _get_text(child)
            elif child.type == "arrow_function":
                value_node = child
            elif child.type == "call_expression":
                value_node = child

        if name and value_node and value_node.type == "arrow_function":
            start_line = node.start_point.row + 1
            end_line = node.end_point.row + 1
            params = ""
            return_type = ""
            for child in value_node.children:
                if child.type == "formal_parameters":
                    params = _get_text(child)
                elif child.type == "type_annotation":
                    return_type = _get_text(child).lstrip(": ").strip()
            kind = "method" if enclosing_class else "function"
            sig = f"const {name} = {params} =>"
            if return_type:
                sig += f": {return_type}"
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
            # Recurse into arrow body
            func_name = f"{enclosing_class}.{name}" if enclosing_class else name
            for child in value_node.children:
                if child.type == "statement_block":
                    for stmt in child.children:
                        self._walk(stmt, result, enclosing_class, func_name)

        # Recurse to find any calls
        for child in node.children:
            self._walk(child, result, enclosing_class, enclosing_func)

    def _extract_param_types(
        self, params_node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract type annotations from function parameters."""
        for child in params_node.children:
            if child.type == "required_parameter" or child.type == "optional_parameter":
                for sub in child.children:
                    if sub.type == "type_annotation":
                        type_text = _get_text(sub).lstrip(": ").strip()
                        if type_text:
                            result.type_refs.append(
                                TypeRef(
                                    name=type_text,
                                    kind="annotation",
                                    line=sub.start_point.row + 1,
                                )
                            )

    # Handler dispatch table
    _handlers: dict[str, object] = {
        "function_declaration": _handle_function,
        "class_declaration": _handle_class,
        "method_definition": _handle_method,
        "interface_declaration": _handle_interface,
        "type_alias_declaration": _handle_type_alias,
        "enum_declaration": _handle_enum,
        "import_statement": _handle_import,
        "export_statement": _handle_export,
        "call_expression": _handle_call,
        "arrow_function": _handle_arrow_function,
        "lexical_declaration": _handle_lexical_declaration,
        "variable_declaration": _handle_lexical_declaration,
    }
