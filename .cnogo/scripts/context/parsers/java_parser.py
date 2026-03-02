"""Java language parser using tree-sitter.

Extracts symbols, imports, calls, heritage, and type references from
Java source code (classes, interfaces, enums, methods, constructors).
"""

from __future__ import annotations

import tree_sitter
import tree_sitter_java

from ..parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)

JAVA_LANGUAGE = tree_sitter.Language(tree_sitter_java.language())


def _get_text(node: tree_sitter.Node) -> str:
    """Extract decoded text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _get_name(node: tree_sitter.Node, name_types: tuple[str, ...] = ("identifier", "type_identifier")) -> str:
    """Get the name from a definition node."""
    for child in node.children:
        if child.type in name_types:
            return _get_text(child)
    return ""


class JavaParser(LanguageParser):
    """Parser for Java source files using tree-sitter."""

    def __init__(self) -> None:
        self._parser = tree_sitter.Parser(JAVA_LANGUAGE)

    def parse(self, content: str, file_path: str = "") -> ParseResult:
        """Parse Java source and return extracted IR."""
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

    def _handle_class_declaration(
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

        # Extract heritage
        for child in node.children:
            if child.type == "superclass":
                for sub in child.children:
                    if sub.type == "type_identifier":
                        parent = _get_text(sub)
                        result.heritage.append((name, parent, "extends"))
                        result.type_refs.append(
                            TypeRef(name=parent, kind="base_class", line=sub.start_point.row + 1)
                        )
            elif child.type == "super_interfaces":
                self._extract_interfaces(child, name, "implements", result)

        sig = f"class {name}"
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

    def _handle_interface_declaration(
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

        # Extract extends for interfaces
        for child in node.children:
            if child.type == "extends_interfaces":
                self._extract_interfaces(child, name, "extends", result)

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="interface",
                start_line=start_line,
                end_line=end_line,
                signature=f"interface {name}",
            )
        )

        # Recurse into interface body
        for child in node.children:
            if child.type == "interface_body":
                for stmt in child.children:
                    self._walk(stmt, result, name, "")

    def _handle_enum_declaration(
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

        # Extract implements for enums
        for child in node.children:
            if child.type == "super_interfaces":
                self._extract_interfaces(child, name, "implements", result)

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="enum",
                start_line=start_line,
                end_line=end_line,
                signature=f"enum {name}",
            )
        )

        # Recurse into enum body
        for child in node.children:
            if child.type == "enum_body":
                for stmt in child.children:
                    self._walk(stmt, result, name, "")

    def _handle_method_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract method declaration."""
        # Use field-based access — the return type (type_identifier) appears
        # before the method name (identifier) in child order
        name_node = node.child_by_field_name("name")
        name = _get_text(name_node) if name_node else ""
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        # Build signature
        params = ""
        return_type = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)
            elif child.type == "type_identifier" or child.type == "void_type" or child.type == "integral_type" or child.type == "floating_point_type" or child.type == "boolean_type" or child.type == "generic_type" or child.type == "array_type":
                return_type = _get_text(child)

        sig = f"{return_type} {name}{params}" if return_type else f"{name}{params}"

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

        # Extract param type refs
        self._extract_param_types(node, result)

        # Return type ref
        if return_type and return_type not in ("void", "int", "long", "float", "double", "boolean", "byte", "short", "char"):
            result.type_refs.append(
                TypeRef(name=return_type, kind="return_type", line=start_line)
            )

        # Recurse into method body
        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _handle_constructor_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract constructor declaration."""
        name = _get_name(node)
        if not name:
            return

        start_line = node.start_point.row + 1
        end_line = node.end_point.row + 1

        params = ""
        for child in node.children:
            if child.type == "formal_parameters":
                params = _get_text(child)

        result.symbols.append(
            SymbolInfo(
                name=name,
                kind="method",
                start_line=start_line,
                end_line=end_line,
                signature=f"{name}{params}",
                class_name=enclosing_class,
            )
        )

        # Extract param type refs
        self._extract_param_types(node, result)

        # Recurse into constructor body
        func_name = f"{enclosing_class}.{name}" if enclosing_class else name
        for child in node.children:
            if child.type == "block" or child.type == "constructor_body":
                for stmt in child.children:
                    self._walk(stmt, result, enclosing_class, func_name)

    def _handle_import_declaration(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract import declaration."""
        line = node.start_point.row + 1
        # Get the scoped identifier path
        module = ""
        for child in node.children:
            if child.type == "scoped_identifier":
                module = _get_text(child)
            elif child.type == "identifier":
                module = _get_text(child)

        if module:
            # Split into module path and imported name
            parts = module.rsplit(".", 1)
            if len(parts) == 2:
                result.imports.append(
                    ImportInfo(module=parts[0], names=[parts[1]], line=line)
                )
            else:
                result.imports.append(
                    ImportInfo(module=module, line=line)
                )

    def _handle_method_invocation(
        self,
        node: tree_sitter.Node,
        result: ParseResult,
        enclosing_class: str,
        enclosing_func: str,
    ) -> None:
        """Extract method invocation (call)."""
        # Method name is in the identifier child
        method_name = ""
        object_name = ""
        for child in node.children:
            if child.type == "identifier":
                method_name = _get_text(child)
            elif child.type in ("field_access", "method_invocation"):
                object_name = _get_text(child)

        # Check for object.method() pattern
        callee = method_name
        if object_name and method_name:
            callee = f"{object_name}.{method_name}"
        elif not method_name:
            # Try getting callee from first child
            if node.children:
                callee = _get_text(node.children[0])

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

    def _extract_interfaces(
        self,
        node: tree_sitter.Node,
        class_name: str,
        relation: str,
        result: ParseResult,
    ) -> None:
        """Extract interface/superclass references from a type_list."""
        for child in node.children:
            if child.type == "type_list":
                for sub in child.children:
                    if sub.type == "type_identifier":
                        iface = _get_text(sub)
                        result.heritage.append((class_name, iface, relation))
                        result.type_refs.append(
                            TypeRef(name=iface, kind="base_class", line=sub.start_point.row + 1)
                        )
                    elif sub.type == "generic_type":
                        # Generic interface like Comparable<Foo>
                        iface = _get_text(sub)
                        result.heritage.append((class_name, iface, relation))
                        result.type_refs.append(
                            TypeRef(name=iface, kind="base_class", line=sub.start_point.row + 1)
                        )
            elif child.type == "type_identifier":
                iface = _get_text(child)
                result.heritage.append((class_name, iface, relation))
                result.type_refs.append(
                    TypeRef(name=iface, kind="base_class", line=child.start_point.row + 1)
                )

    def _extract_param_types(
        self, func_node: tree_sitter.Node, result: ParseResult
    ) -> None:
        """Extract type references from method parameters."""
        for child in func_node.children:
            if child.type == "formal_parameters":
                for param in child.children:
                    if param.type == "formal_parameter" or param.type == "spread_parameter":
                        for sub in param.children:
                            if sub.type == "type_identifier" or sub.type == "generic_type":
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
        "class_declaration": _handle_class_declaration,
        "interface_declaration": _handle_interface_declaration,
        "enum_declaration": _handle_enum_declaration,
        "method_declaration": _handle_method_declaration,
        "constructor_declaration": _handle_constructor_declaration,
        "import_declaration": _handle_import_declaration,
        "method_invocation": _handle_method_invocation,
    }
