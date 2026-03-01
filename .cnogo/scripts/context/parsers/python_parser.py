"""Python language parser using tree-sitter.

Extracts symbols, imports, calls, heritage, and type references from Python
source code using the tree-sitter-python grammar.
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_python

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

PY_LANGUAGE = tree_sitter.Language(tree_sitter_python.language())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_docstring(block_node: tree_sitter.Node) -> str:
    """Extract docstring from the first statement of a block."""
    if not block_node.children:
        return ""
    first = block_node.children[0]
    if first.type == "expression_statement" and first.children:
        expr = first.children[0]
        if expr.type == "string":
            text = _get_text(expr)
            # Strip triple quotes
            for q in ('"""', "'''"):
                if text.startswith(q) and text.endswith(q):
                    return text[3:-3].strip()
            # Single-quoted string docstring
            for q in ('"', "'"):
                if text.startswith(q) and text.endswith(q):
                    return text[1:-1].strip()
            return text
    return ""


def _build_signature(node: tree_sitter.Node) -> str:
    """Build function/method signature from a function_definition node."""
    parts: list[str] = []
    name = ""
    params = ""
    return_type = ""
    for child in node.children:
        if child.type == "identifier":
            name = _get_text(child)
        elif child.type == "parameters":
            params = _get_text(child)
        elif child.type == "type":
            return_type = _get_text(child)
    sig = f"def {name}{params}"
    if return_type:
        sig += f" -> {return_type}"
    return sig


def _get_name(node: tree_sitter.Node) -> str:
    """Get the name identifier from a definition node."""
    for child in node.children:
        if child.type == "identifier":
            return _get_text(child)
    return ""


class PythonParser(LanguageParser):
    """Parser for Python source files using tree-sitter."""

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser(PY_LANGUAGE)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse Python source and return extracted IR."""
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
        if node.type == "function_definition":
            self._extract_function(node, result, enclosing_class, enclosing_func)
        elif node.type == "class_definition":
            self._extract_class(node, result, enclosing_class)
        elif node.type == "import_statement":
            self._extract_import(node, result)
        elif node.type == "import_from_statement":
            self._extract_from_import(node, result)
        elif node.type == "call":
            self._extract_call(node, result, enclosing_class, enclosing_func)
        else:
            for child in node.children:
                self._walk(child, result, enclosing_class, enclosing_func)

    def _extract_function(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract a function or method definition."""
        name = _get_name(node)
        if not name:
            return

        kind = "method" if enclosing_class else "function"
        signature = _build_signature(node)
        start_line = node.start_point.row + 1  # 1-based
        end_line = node.end_point.row + 1

        # Extract docstring from block
        docstring = ""
        for child in node.children:
            if child.type == "block":
                docstring = _get_docstring(child)
                break

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind=kind,
                start_line=start_line,
                end_line=end_line,
                signature=signature,
                docstring=docstring,
                class_name=enclosing_class,
            )
        )

        # Extract return type annotation
        for child in node.children:
            if child.type == "type":
                result.type_refs.append(
                    TypeRef(
                        name=_get_text(child),
                        kind="return_type",
                        line=child.start_point.row + 1,
                    )
                )

        # Extract parameter type annotations
        for child in node.children:
            if child.type == "parameters":
                self._extract_param_types(child, result)

        # Recurse into the function body
        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _extract_param_types(
        self, params_node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract type annotations from function parameters."""
        for child in params_node.children:
            if child.type == "typed_parameter":
                for sub in child.children:
                    if sub.type == "type":
                        result.type_refs.append(
                            TypeRef(
                                name=_get_text(sub),
                                kind="annotation",
                                line=sub.start_point.row + 1,
                            )
                        )
            elif child.type == "typed_default_parameter":
                for sub in child.children:
                    if sub.type == "type":
                        result.type_refs.append(
                            TypeRef(
                                name=_get_text(sub),
                                kind="annotation",
                                line=sub.start_point.row + 1,
                            )
                        )

    def _extract_class(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
    ) -> None:
        """Extract a class definition."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Build signature
        bases_text = ""
        for child in node.children:
            if child.type == "argument_list":
                bases_text = _get_text(child)
        signature = f"class {name}{bases_text}" if bases_text else f"class {name}"

        # Extract docstring from block
        docstring = ""
        for child in node.children:
            if child.type == "block":
                docstring = _get_docstring(child)
                break

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="class",
                start_line=start_line,
                end_line=end_line,
                signature=signature,
                docstring=docstring,
                class_name=enclosing_class,
            )
        )

        # Extract base classes as heritage and type_refs
        for child in node.children:
            if child.type == "argument_list":
                for base in child.children:
                    if base.type == "identifier":
                        base_name = _get_text(base)
                        result.heritage.append((name, base_name, "extends"))
                        result.type_refs.append(
                            TypeRef(
                                name=base_name,
                                kind="base_class",
                                line=base.start_point.row + 1,
                            )
                        )
                    elif base.type == "attribute":
                        base_name = _get_text(base)
                        result.heritage.append((name, base_name, "extends"))
                        result.type_refs.append(
                            TypeRef(
                                name=base_name,
                                kind="base_class",
                                line=base.start_point.row + 1,
                            )
                        )

        # Recurse into class body
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, name, "")

    def _extract_import(
        self, node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract `import x` statement."""
        line = node.start_point.row + 1
        for child in node.children:
            if child.type == "dotted_name":
                module_name = _get_text(child)
                result.imports.append(
                    ImportInfo(module=module_name, line=line)
                )
            elif child.type == "aliased_import":
                name_node = None
                alias_node = None
                for sub in child.children:
                    if sub.type == "dotted_name":
                        name_node = sub
                    elif sub.type == "identifier":
                        alias_node = sub
                if name_node:
                    result.imports.append(
                        ImportInfo(
                            module=_get_text(name_node),
                            alias=_get_text(alias_node) if alias_node else "",
                            line=line,
                        )
                    )

    def _extract_from_import(
        self, node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract `from x import y` statement."""
        line = node.start_point.row + 1
        module = ""
        names: list[str] = []

        for child in node.children:
            if child.type == "dotted_name":
                if not module:
                    module = _get_text(child)
                else:
                    names.append(_get_text(child))
            elif child.type == "relative_import":
                module = _get_text(child)
            elif child.type == "wildcard_import":
                names.append("*")

        result.imports.append(
            ImportInfo(module=module, names=names, line=line)
        )

    def _extract_call(
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
        elif callee_node.type == "attribute":
            callee = _get_text(callee_node)
        else:
            # Complex call (e.g., func()())  — skip
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

        # Recurse into arguments to find nested calls
        for child in node.children:
            if child.type == "argument_list":
                for arg in child.children:
                    self._walk(arg, result, enclosing_class, enclosing_func)
