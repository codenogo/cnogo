"""Go language parser using tree-sitter.

Extracts symbols, imports, calls, heritage, and type references from
Go source code (functions, methods, structs, interfaces).
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_go

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

GO_LANGUAGE = tree_sitter.Language(tree_sitter_go.language())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_name(node: tree_sitter.Node, name_types: tuple[str, ...] = ("identifier", "type_identifier")) -> str:
    """Get the name from a definition node."""
    for child in node.children:
        if child.type in name_types:
            return _get_text(child)
    return ""


class GoParser(LanguageParser):
    """Parser for Go source files using tree-sitter."""

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser(GO_LANGUAGE)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse Go source and return extracted IR."""
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

    def _handle_function_declaration(
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

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Build signature
        params = ""
        return_type = ""
        for child in node.children:
            if child.type == "parameter_list":
                params = _get_text(child)
            elif child.type == "type_identifier" or child.type == "pointer_type":
                return_type = _get_text(child)
            elif child.type == "parameter_list" and params:
                # Second parameter_list is return types
                return_type = _get_text(child)

        # Check for result parameters (return types)
        result_node = node.child_by_field_name("result")
        if result_node:
            return_type = _get_text(result_node)

        sig = f"func {name}{params}"
        if return_type:
            sig += f" {return_type}"

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="function",
                start_line=start_line,
                end_line=end_line,
                signature=sig,
            )
        )

        # Extract parameter type refs
        self._extract_param_types(node, result)

        # Return type ref
        if return_type:
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        # Recurse into body
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, name)

    def _handle_method_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract method declaration (function with receiver)."""
        # Method name is a field_identifier in Go AST
        name_node = node.child_by_field_name("name")
        name = _get_text(name_node) if name_node else ""
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Extract receiver type
        receiver_type = ""
        for child in node.children:
            if child.type == "parameter_list":
                # First parameter_list is the receiver
                for param in child.children:
                    if param.type == "parameter_declaration":
                        for sub in param.children:
                            if sub.type == "type_identifier":
                                receiver_type = _get_text(sub)
                            elif sub.type == "pointer_type":
                                for ptr_child in sub.children:
                                    if ptr_child.type == "type_identifier":
                                        receiver_type = _get_text(ptr_child)
                break  # Only first parameter_list is receiver

        # Build signature
        params = ""
        param_lists = [c for c in node.children if c.type == "parameter_list"]
        if len(param_lists) >= 2:
            params = _get_text(param_lists[1])

        return_type = ""
        result_node = node.child_by_field_name("result")
        if result_node:
            return_type = _get_text(result_node)

        sig = f"func ({receiver_type}) {name}{params}"
        if return_type:
            sig += f" {return_type}"

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="method",
                start_line=start_line,
                end_line=end_line,
                signature=sig,
                class_name=receiver_type,
            )
        )

        # Type refs
        if return_type:
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        # Recurse into body
        func_name = f"{receiver_type}.{name}" if receiver_type else name
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, receiver_type, func_name)

    def _handle_type_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract type declarations (struct, interface)."""
        for child in node.children:
            if child.type == "type_spec":
                self._handle_type_spec(child, result)

    def _handle_type_spec(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
    ) -> None:
        """Handle a single type_spec node."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        for child in node.children:
            if child.type == "struct_type":
                result.symbols.append(
                    SymbolInfo(
                        name=name,
                        kind="class",
                        start_line=start_line,
                        end_line=end_line,
                        signature=f"type {name} struct",
                    )
                )
                # Extract embedded fields as heritage
                self._extract_struct_heritage(child, name, result)
                return
            elif child.type == "interface_type":
                result.symbols.append(
                    SymbolInfo(
                        name=name,
                        kind="interface",
                        start_line=start_line,
                        end_line=end_line,
                        signature=f"type {name} interface",
                    )
                )
                # Extract embedded interfaces as heritage
                self._extract_interface_heritage(child, name, result)
                return

        # Other type declarations (type alias, etc.)
        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="type_alias",
                start_line=start_line,
                end_line=end_line,
                signature=_get_text(node).strip(),
            )
        )

    def _extract_struct_heritage(
        self,
        struct_node: tree_sitter.Node,
        struct_name: str,
        result: ParseResult,
    ) -> None:
        """Extract embedded struct fields as 'extends' heritage."""
        for child in struct_node.children:
            if child.type == "field_declaration_list":
                for field in child.children:
                    if field.type == "field_declaration":
                        # Embedded field: only has a type, no name
                        children = [c for c in field.children if c.type != "comment"]
                        if len(children) == 1:
                            type_child = children[0]
                            if type_child.type == "type_identifier":
                                parent = _get_text(type_child)
                                result.heritage.append((struct_name, parent, "extends"))
                                result.type_refs.append(
                                    TypeRef(name=parent, kind="base_class", line=type_child.start_point.row + 1)
                                )
                            elif type_child.type == "pointer_type":
                                for sub in type_child.children:
                                    if sub.type == "type_identifier":
                                        parent = _get_text(sub)
                                        result.heritage.append((struct_name, parent, "extends"))
                                        result.type_refs.append(
                                            TypeRef(name=parent, kind="base_class", line=sub.start_point.row + 1)
                                        )

    def _extract_interface_heritage(
        self,
        iface_node: tree_sitter.Node,
        iface_name: str,
        result: ParseResult,
    ) -> None:
        """Extract embedded interfaces as 'extends' heritage."""
        for child in iface_node.children:
            # Embedded interface references appear as type_identifier children
            if child.type == "type_identifier":
                parent = _get_text(child)
                result.heritage.append((iface_name, parent, "extends"))
            # Or inside method_spec_list / interface body
            for sub in child.children if hasattr(child, 'children') else []:
                if sub.type == "type_identifier":
                    # Check if this is a standalone type (embedded interface)
                    # vs a method return type
                    if child.type not in ("method_spec",):
                        parent = _get_text(sub)
                        result.heritage.append((iface_name, parent, "extends"))

    def _handle_import_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract import declarations."""
        line = node.start_point.row + 1
        for child in node.children:
            if child.type == "import_spec":
                self._extract_import_spec(child, result, line)
            elif child.type == "import_spec_list":
                for spec in child.children:
                    if spec.type == "import_spec":
                        self._extract_import_spec(spec, result, spec.start_point.row + 1)

    def _extract_import_spec(
        self,
        spec_node: tree_sitter.Node,
        result: ParseResult,
        line: int,
    ) -> None:
        """Extract a single import spec."""
        alias = ""
        module = ""
        for child in spec_node.children:
            if child.type == "interpreted_string_literal":
                module = _get_text(child).strip('"')
            elif child.type == "package_identifier" or child.type == "dot":
                alias = _get_text(child)
            elif child.type == "blank_identifier":
                alias = "_"

        if module:
            result.imports.append(
                ImportInfo(module=module, alias=alias, line=line)
            )

    def _handle_call_expression(
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
        elif callee_node.type == "selector_expression":
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
            if child.type == "argument_list":
                for arg in child.children:
                    self._walk(arg, result, enclosing_class, enclosing_func)

    def _extract_param_types(
        self, func_node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract type references from function parameters."""
        for child in func_node.children:
            if child.type == "parameter_list":
                for param in child.children:
                    if param.type == "parameter_declaration":
                        for sub in param.children:
                            if sub.type == "type_identifier":
                                type_text = _get_text(sub)
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
        "function_declaration": _handle_function_declaration,
        "method_declaration": _handle_method_declaration,
        "type_declaration": _handle_type_declaration,
        "import_declaration": _handle_import_declaration,
        "call_expression": _handle_call_expression,
    }
