"""Rust language parser using tree-sitter.

Extracts symbols, imports, calls, heritage, and type references from
Rust source code (functions, methods, structs, enums, traits).
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_rust

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

RUST_LANGUAGE = tree_sitter.Language(tree_sitter_rust.language())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_name(node: tree_sitter.Node, name_types: tuple[str, ...] = ("identifier", "type_identifier")) -> str:
    """Get the name from a definition node."""
    for child in node.children:
        if child.type in name_types:
            return _get_text(child)
    return ""


class RustParser(LanguageParser):
    """Parser for Rust source files using tree-sitter."""

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser(RUST_LANGUAGE)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse Rust source and return extracted IR."""
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

    def _handle_function_item(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract function/method declaration."""
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
            if child.type == "parameters":
                params = _get_text(child)
            elif child.type == "type_identifier" or child.type == "generic_type" or child.type == "scoped_type_identifier":
                return_type = _get_text(child)

        # Check for return type via -> syntax
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            return_type = _get_text(ret_node)

        sig = f"fn {name}{params}"
        if return_type:
            sig += f" -> {return_type}"

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

        # Extract parameter type refs
        self._extract_param_types(node, result)

        # Return type ref
        if return_type:
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        # Recurse into body
        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _handle_struct_item(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract struct declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="class",
                start_line=start_line,
                end_line=end_line,
                signature=f"struct {name}",
            )
        )

    def _handle_enum_item(
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

    def _handle_trait_item(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract trait declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="interface",
                start_line=start_line,
                end_line=end_line,
                signature=f"trait {name}",
            )
        )

    def _handle_type_item(
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

    def _handle_impl_item(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract impl block — methods and trait implementations."""
        # Determine the target type and optional trait
        trait_name = ""
        type_name = ""

        # Check for `impl Trait for Type` pattern
        type_node = node.child_by_field_name("type")
        trait_node = node.child_by_field_name("trait")

        if type_node:
            type_name = _get_text(type_node)
        if trait_node:
            trait_name = _get_text(trait_node)

        # Record heritage if this is a trait impl
        if trait_name and type_name:
            result.heritage.append((type_name, trait_name, "implements"))
            result.type_refs.append(
                TypeRef(name=trait_name, kind="base_class", line=node.start_point.row + 1)
            )

        # Recurse into impl body with type as enclosing_class
        impl_class = type_name or enclosing_class
        for child in node.children:
            if child.type == "declaration_list":
                for stmt in child.children:
                    self._walk(stmt, result, impl_class, "")

    def _handle_use_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract use declarations (imports)."""
        line = node.start_point.row + 1
        # Get the full path text, stripping 'use' keyword and semicolon
        text = _get_text(node).strip()
        if text.startswith("use "):
            text = text[4:]
        text = text.rstrip(";").strip()

        if text:
            # Extract module path and imported names
            module = text
            names: list[str] = []

            # Handle `use foo::bar::{Baz, Qux}` pattern
            if "::{" in text:
                parts = text.split("::{", 1)
                module = parts[0]
                if len(parts) > 1:
                    name_part = parts[1].rstrip("}")
                    names = [n.strip() for n in name_part.split(",") if n.strip()]
            elif "::" in text:
                # `use foo::bar::Baz` — module is path, name is last segment
                parts = text.rsplit("::", 1)
                module = parts[0]
                if len(parts) > 1 and parts[1] != "*":
                    names = [parts[1]]

            result.imports.append(
                ImportInfo(module=module, names=names, line=line)
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
        elif callee_node.type == "scoped_identifier":
            callee = _get_text(callee_node)
        elif callee_node.type == "field_expression":
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

    def _extract_param_types(
        self, func_node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract type references from function parameters."""
        for child in func_node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "parameter":
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
        "function_item": _handle_function_item,
        "struct_item": _handle_struct_item,
        "enum_item": _handle_enum_item,
        "trait_item": _handle_trait_item,
        "type_item": _handle_type_item,
        "impl_item": _handle_impl_item,
        "use_declaration": _handle_use_declaration,
        "call_expression": _handle_call_expression,
    }
