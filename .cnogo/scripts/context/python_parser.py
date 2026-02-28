"""Python AST parser for context graph ingestion.

Parses Python source files using the stdlib ast module to extract
symbols, imports, calls, heritage relationships, and type references.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SymbolInfo:
    """A symbol (function, class, method) extracted from source."""

    name: str
    kind: str  # "function", "class", "method"
    start_line: int
    end_line: int
    signature: str = ""
    class_name: str = ""
    decorators: list[str] = field(default_factory=list)
    docstring: str = ""


@dataclass
class ImportInfo:
    """An import statement extracted from source."""

    module: str
    names: list[str] = field(default_factory=list)
    is_relative: bool = False
    level: int = 0


@dataclass
class CallInfo:
    """A function/method call extracted from source."""

    name: str
    line: int
    receiver: str = ""


@dataclass
class TypeRef:
    """A type reference extracted from annotations."""

    name: str
    kind: str  # "param", "return"
    line: int


@dataclass
class ParseResult:
    """Complete parse result for a single file."""

    file_path: str
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)
    heritage: list[tuple[str, str, str]] = field(default_factory=list)
    type_refs: list[TypeRef] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)


def _build_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a human-readable signature from a function AST node."""
    args = node.args
    params: list[str] = []

    # Regular args
    for i, arg in enumerate(args.args):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        # Defaults are right-aligned to args
        default_offset = len(args.args) - len(args.defaults)
        if i >= default_offset:
            default = args.defaults[i - default_offset]
            param += f"={ast.unparse(default)}"
        params.append(param)

    # *args
    if args.vararg:
        p = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            p += f": {ast.unparse(args.vararg.annotation)}"
        params.append(p)

    # keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        param = arg.arg
        if arg.annotation:
            param += f": {ast.unparse(arg.annotation)}"
        if args.kw_defaults[i] is not None:
            param += f"={ast.unparse(args.kw_defaults[i])}"
        params.append(param)

    # **kwargs
    if args.kwarg:
        p = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            p += f": {ast.unparse(args.kwarg.annotation)}"
        params.append(p)

    sig = f"def {node.name}({', '.join(params)})"
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _get_decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> list[str]:
    """Extract decorator names from a node."""
    names = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name):
            names.append(dec.id)
        elif isinstance(dec, ast.Attribute):
            names.append(ast.unparse(dec))
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                names.append(dec.func.id)
            elif isinstance(dec.func, ast.Attribute):
                names.append(ast.unparse(dec.func))
    return names


def _extract_type_names(annotation: ast.expr, kind: str, line: int) -> list[TypeRef]:
    """Extract type reference names from an annotation node."""
    refs: list[TypeRef] = []
    if isinstance(annotation, ast.Name):
        refs.append(TypeRef(name=annotation.id, kind=kind, line=line))
    elif isinstance(annotation, ast.Attribute):
        refs.append(TypeRef(name=ast.unparse(annotation), kind=kind, line=line))
    elif isinstance(annotation, ast.Subscript):
        # e.g. list[str] — extract the outer type
        if isinstance(annotation.value, ast.Name):
            refs.append(TypeRef(name=annotation.value.id, kind=kind, line=line))
        # Recurse into slice
        if isinstance(annotation.slice, ast.Name):
            refs.append(TypeRef(name=annotation.slice.id, kind=kind, line=line))
    elif isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        # Forward reference string
        refs.append(TypeRef(name=annotation.value, kind=kind, line=line))
    return refs


class PythonParser:
    """Parses Python source to extract symbols, imports, calls, heritage, types."""

    @staticmethod
    def parse(source: str, file_path: str) -> ParseResult:
        """Parse Python source code and extract all information.

        Args:
            source: Python source code string.
            file_path: Path to the source file (for metadata).

        Returns:
            ParseResult with extracted symbols, imports, calls, etc.
        """
        result = ParseResult(file_path=file_path)

        if not source.strip():
            return result

        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError:
            return result

        _extract_symbols(tree, result)
        _extract_imports(tree, result)
        _extract_calls(tree, result)
        _extract_heritage(tree, result)
        _extract_types(tree, result)
        _extract_exports(tree, result)

        return result


def _extract_symbols(tree: ast.Module, result: ParseResult) -> None:
    """Extract function, class, and method symbols."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Determine if it's a method (inside a class)
            kind = "function"
            class_name = ""
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    if node in ast.iter_child_nodes(parent):
                        kind = "method"
                        class_name = parent.name
                        break

            result.symbols.append(SymbolInfo(
                name=node.name,
                kind=kind,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=_build_signature(node),
                class_name=class_name,
                decorators=_get_decorator_names(node),
                docstring=ast.get_docstring(node) or "",
            ))

        elif isinstance(node, ast.ClassDef):
            result.symbols.append(SymbolInfo(
                name=node.name,
                kind="class",
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                decorators=_get_decorator_names(node),
                docstring=ast.get_docstring(node) or "",
            ))


def _extract_imports(tree: ast.Module, result: ParseResult) -> None:
    """Extract import statements."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.imports.append(ImportInfo(
                    module=alias.name,
                    names=[],
                    is_relative=False,
                    level=0,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            level = node.level or 0
            result.imports.append(ImportInfo(
                module=module,
                names=names,
                is_relative=level > 0,
                level=level,
            ))


def _extract_calls(tree: ast.Module, result: ParseResult) -> None:
    """Extract function and method calls."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                result.calls.append(CallInfo(
                    name=func.id,
                    line=node.lineno,
                ))
            elif isinstance(func, ast.Attribute):
                receiver = ""
                if isinstance(func.value, ast.Name):
                    receiver = func.value.id
                result.calls.append(CallInfo(
                    name=func.attr,
                    line=node.lineno,
                    receiver=receiver,
                ))


def _extract_heritage(tree: ast.Module, result: ParseResult) -> None:
    """Extract class inheritance relationships."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name):
                    result.heritage.append((node.name, "extends", base.id))
                elif isinstance(base, ast.Attribute):
                    result.heritage.append((node.name, "extends", ast.unparse(base)))


def _extract_types(tree: ast.Module, result: ParseResult) -> None:
    """Extract type annotations from function parameters and return types."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Parameter annotations
            for arg in node.args.args:
                if arg.annotation:
                    result.type_refs.extend(
                        _extract_type_names(arg.annotation, "param", arg.annotation.lineno)
                    )
            # Return annotation
            if node.returns:
                result.type_refs.extend(
                    _extract_type_names(node.returns, "return", node.returns.lineno)
                )


def _extract_exports(tree: ast.Module, result: ParseResult) -> None:
    """Extract __all__ exports list."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                result.exports.append(elt.value)
