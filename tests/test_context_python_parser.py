"""Tests for PythonParser using tree-sitter."""

from __future__ import annotations

import sys

sys.path.insert(0, ".cnogo")

from scripts.context.parser_base import (
    CallInfo,
    ImportInfo,
    LanguageParser,
    ParseResult,
    SymbolInfo,
    TypeRef,
)
from scripts.context.parsers.python_parser import PythonParser


# --- parser_base IR ---


def test_parser_base_imports():
    """Verify all IR classes are importable."""
    assert SymbolInfo is not None
    assert ImportInfo is not None
    assert CallInfo is not None
    assert TypeRef is not None
    assert ParseResult is not None
    assert LanguageParser is not None


def test_python_parser_is_language_parser():
    """PythonParser must be a subclass of LanguageParser."""
    parser = PythonParser()
    assert isinstance(parser, LanguageParser)


# --- Function parsing ---


def test_parse_function():
    parser = PythonParser()
    source = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
    result = parser.parse(source, "hello.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"
    assert funcs[0].start_line == 1
    assert funcs[0].end_line == 2
    assert "name: str" in funcs[0].signature
    assert "-> str" in funcs[0].signature


def test_parse_function_no_annotations():
    parser = PythonParser()
    source = "def add(a, b):\n    return a + b\n"
    result = parser.parse(source, "math.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert "a, b" in funcs[0].signature


def test_parse_function_with_defaults():
    parser = PythonParser()
    source = "def connect(host='localhost', port=8080):\n    pass\n"
    result = parser.parse(source, "net.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert "host" in funcs[0].signature
    assert "port" in funcs[0].signature


# --- Class and method parsing ---


def test_parse_class():
    parser = PythonParser()
    source = "class Animal:\n    pass\n"
    result = parser.parse(source, "models.py")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "Animal"
    assert classes[0].start_line == 1
    assert classes[0].end_line == 2


def test_parse_method_linked_to_class():
    parser = PythonParser()
    source = "class Dog:\n    def bark(self):\n        print('Woof')\n"
    result = parser.parse(source, "dog.py")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "bark"
    assert methods[0].class_name == "Dog"


def test_parse_multiple_methods():
    parser = PythonParser()
    source = (
        "class Calc:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n"
        "    def sub(self, a, b):\n"
        "        return a - b\n"
    )
    result = parser.parse(source, "calc.py")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert names == {"add", "sub"}
    assert all(m.class_name == "Calc" for m in methods)


def test_parse_docstring():
    parser = PythonParser()
    source = 'def greet():\n    """Say hello."""\n    pass\n'
    result = parser.parse(source, "doc.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].docstring == "Say hello."


def test_parse_class_docstring():
    parser = PythonParser()
    source = 'class Foo:\n    """A foo class."""\n    pass\n'
    result = parser.parse(source, "doc.py")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].docstring == "A foo class."


# --- Import extraction ---


def test_parse_import():
    parser = PythonParser()
    source = "import os\nimport sys\n"
    result = parser.parse(source, "imports.py")
    assert len(result.imports) == 2
    modules = {i.module for i in result.imports}
    assert modules == {"os", "sys"}


def test_parse_from_import():
    parser = PythonParser()
    source = "from pathlib import Path\n"
    result = parser.parse(source, "imports.py")
    assert len(result.imports) == 1
    imp = result.imports[0]
    assert imp.module == "pathlib"
    assert imp.names == ["Path"]


def test_parse_from_import_multiple():
    parser = PythonParser()
    source = "from os.path import join, exists\n"
    result = parser.parse(source, "imports.py")
    assert len(result.imports) == 1
    assert set(result.imports[0].names) == {"join", "exists"}


def test_parse_import_line_numbers():
    parser = PythonParser()
    source = "import os\nimport sys\n"
    result = parser.parse(source, "imports.py")
    lines = sorted(i.line for i in result.imports)
    assert lines == [1, 2]


# --- Call extraction ---


def test_parse_simple_call():
    parser = PythonParser()
    source = "def main():\n    foo()\n"
    result = parser.parse(source, "main.py")
    callees = {c.callee for c in result.calls}
    assert "foo" in callees


def test_parse_call_with_caller():
    parser = PythonParser()
    source = "def main():\n    foo()\n"
    result = parser.parse(source, "main.py")
    foo_calls = [c for c in result.calls if c.callee == "foo"]
    assert len(foo_calls) == 1
    assert foo_calls[0].caller == "main"


def test_parse_method_call():
    parser = PythonParser()
    source = "def run():\n    obj.method()\n"
    result = parser.parse(source, "run.py")
    callees = {c.callee for c in result.calls}
    assert "obj.method" in callees


def test_parse_call_line_number():
    parser = PythonParser()
    source = "x = 1\ndef main():\n    foo()\n"
    result = parser.parse(source, "lines.py")
    foo_calls = [c for c in result.calls if c.callee == "foo"]
    assert len(foo_calls) == 1
    assert foo_calls[0].line == 3


def test_parse_nested_calls():
    parser = PythonParser()
    source = "def outer():\n    foo(bar())\n"
    result = parser.parse(source, "nested.py")
    callees = {c.callee for c in result.calls}
    assert "foo" in callees
    assert "bar" in callees


# --- Heritage extraction ---


def test_parse_extends():
    parser = PythonParser()
    source = "class Dog(Animal):\n    pass\n"
    result = parser.parse(source, "dog.py")
    assert len(result.heritage) == 1
    child, parent, rel = result.heritage[0]
    assert child == "Dog"
    assert parent == "Animal"
    assert rel == "extends"


def test_parse_multiple_inheritance():
    parser = PythonParser()
    source = "class C(A, B):\n    pass\n"
    result = parser.parse(source, "multi.py")
    parents = {h[1] for h in result.heritage if h[0] == "C"}
    assert parents == {"A", "B"}


def test_parse_no_heritage():
    parser = PythonParser()
    source = "class Plain:\n    pass\n"
    result = parser.parse(source, "plain.py")
    assert result.heritage == []


# --- Type annotation extraction ---


def test_parse_param_type():
    parser = PythonParser()
    source = "def greet(name: str) -> None:\n    pass\n"
    result = parser.parse(source, "typed.py")
    type_names = {t.name for t in result.type_refs}
    assert "str" in type_names


def test_parse_return_type():
    parser = PythonParser()
    source = "def count() -> int:\n    return 0\n"
    result = parser.parse(source, "typed.py")
    ret_types = [t for t in result.type_refs if t.kind == "return_type"]
    assert any(t.name == "int" for t in ret_types)


def test_parse_base_class_type_ref():
    parser = PythonParser()
    source = "class Dog(Animal):\n    pass\n"
    result = parser.parse(source, "dog.py")
    base_refs = [t for t in result.type_refs if t.kind == "base_class"]
    assert any(t.name == "Animal" for t in base_refs)


# --- Empty and edge cases ---


def test_parse_empty_source():
    parser = PythonParser()
    result = parser.parse("", "empty.py")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []
    assert result.heritage == []
    assert result.type_refs == []


def test_parse_syntax_error_partial():
    """tree-sitter is error-tolerant; it should still extract what it can."""
    parser = PythonParser()
    source = "def good():\n    pass\n\ndef broken(:\n"
    result = parser.parse(source, "partial.py")
    # Should at least find the good function
    funcs = [s for s in result.symbols if s.name == "good"]
    assert len(funcs) == 1


def test_parse_multiple_classes_and_functions():
    parser = PythonParser()
    source = (
        "def standalone():\n    pass\n\n"
        "class A:\n    def method_a(self):\n        pass\n\n"
        "class B:\n    def method_b(self):\n        pass\n"
    )
    result = parser.parse(source, "multi.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    classes = [s for s in result.symbols if s.kind == "class"]
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(funcs) == 1
    assert len(classes) == 2
    assert len(methods) == 2
    assert {m.class_name for m in methods} == {"A", "B"}
