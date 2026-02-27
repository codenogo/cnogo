"""Tests for Python AST parser."""

from __future__ import annotations

import pytest


# --- Function parsing ---


def test_parse_function():
    from scripts.context.python_parser import PythonParser
    source = "def greet(name: str) -> str:\n    return f'Hello {name}'\n"
    result = PythonParser.parse(source, "hello.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"
    assert funcs[0].start_line == 1
    assert funcs[0].end_line == 2
    assert "name: str" in funcs[0].signature
    assert "-> str" in funcs[0].signature


def test_parse_async_function():
    from scripts.context.python_parser import PythonParser
    source = "async def fetch(url: str) -> bytes:\n    pass\n"
    result = PythonParser.parse(source, "async.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "fetch"


def test_parse_function_no_annotations():
    from scripts.context.python_parser import PythonParser
    source = "def add(a, b):\n    return a + b\n"
    result = PythonParser.parse(source, "math.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert "a, b" in funcs[0].signature


def test_parse_function_with_defaults():
    from scripts.context.python_parser import PythonParser
    source = "def connect(host='localhost', port=8080):\n    pass\n"
    result = PythonParser.parse(source, "net.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert "host" in funcs[0].signature
    assert "port" in funcs[0].signature


def test_parse_function_decorators():
    from scripts.context.python_parser import PythonParser
    source = "@staticmethod\ndef run():\n    pass\n"
    result = PythonParser.parse(source, "deco.py")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert "staticmethod" in funcs[0].decorators


# --- Class and method parsing ---


def test_parse_class():
    from scripts.context.python_parser import PythonParser
    source = "class Animal:\n    pass\n"
    result = PythonParser.parse(source, "models.py")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "Animal"
    assert classes[0].start_line == 1
    assert classes[0].end_line == 2


def test_parse_method_linked_to_class():
    from scripts.context.python_parser import PythonParser
    source = "class Dog:\n    def bark(self):\n        print('Woof')\n"
    result = PythonParser.parse(source, "dog.py")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "bark"
    assert methods[0].class_name == "Dog"


def test_parse_multiple_methods():
    from scripts.context.python_parser import PythonParser
    source = (
        "class Calc:\n"
        "    def add(self, a, b):\n"
        "        return a + b\n"
        "    def sub(self, a, b):\n"
        "        return a - b\n"
    )
    result = PythonParser.parse(source, "calc.py")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert names == {"add", "sub"}
    assert all(m.class_name == "Calc" for m in methods)


# --- Import extraction ---


def test_parse_import():
    from scripts.context.python_parser import PythonParser
    source = "import os\nimport sys\n"
    result = PythonParser.parse(source, "imports.py")
    assert len(result.imports) == 2
    modules = {i.module for i in result.imports}
    assert modules == {"os", "sys"}


def test_parse_from_import():
    from scripts.context.python_parser import PythonParser
    source = "from pathlib import Path\n"
    result = PythonParser.parse(source, "imports.py")
    assert len(result.imports) == 1
    imp = result.imports[0]
    assert imp.module == "pathlib"
    assert imp.names == ["Path"]
    assert imp.is_relative is False


def test_parse_from_import_multiple():
    from scripts.context.python_parser import PythonParser
    source = "from os.path import join, exists\n"
    result = PythonParser.parse(source, "imports.py")
    assert len(result.imports) == 1
    assert set(result.imports[0].names) == {"join", "exists"}


def test_parse_relative_import():
    from scripts.context.python_parser import PythonParser
    source = "from . import sibling\n"
    result = PythonParser.parse(source, "pkg/child.py")
    assert len(result.imports) == 1
    imp = result.imports[0]
    assert imp.is_relative is True
    assert imp.level == 1
    assert imp.names == ["sibling"]


def test_parse_relative_import_from():
    from scripts.context.python_parser import PythonParser
    source = "from ..utils import helper\n"
    result = PythonParser.parse(source, "pkg/sub/mod.py")
    assert len(result.imports) == 1
    imp = result.imports[0]
    assert imp.is_relative is True
    assert imp.level == 2
    assert imp.module == "utils"
    assert imp.names == ["helper"]


# --- Call extraction ---


def test_parse_simple_call():
    from scripts.context.python_parser import PythonParser
    source = "def main():\n    foo()\n"
    result = PythonParser.parse(source, "main.py")
    calls = result.calls
    call_names = {c.name for c in calls}
    assert "foo" in call_names


def test_parse_method_call():
    from scripts.context.python_parser import PythonParser
    source = "def run():\n    obj.method()\n"
    result = PythonParser.parse(source, "run.py")
    calls = result.calls
    method_calls = [c for c in calls if c.receiver == "obj"]
    assert len(method_calls) == 1
    assert method_calls[0].name == "method"


def test_parse_self_method_call():
    from scripts.context.python_parser import PythonParser
    source = "class Foo:\n    def run(self):\n        self.helper()\n"
    result = PythonParser.parse(source, "foo.py")
    calls = result.calls
    self_calls = [c for c in calls if c.receiver == "self"]
    assert len(self_calls) == 1
    assert self_calls[0].name == "helper"


def test_parse_call_line_number():
    from scripts.context.python_parser import PythonParser
    source = "x = 1\ny = foo()\n"
    result = PythonParser.parse(source, "lines.py")
    calls = [c for c in result.calls if c.name == "foo"]
    assert len(calls) == 1
    assert calls[0].line == 2


# --- Heritage extraction ---


def test_parse_extends():
    from scripts.context.python_parser import PythonParser
    source = "class Dog(Animal):\n    pass\n"
    result = PythonParser.parse(source, "dog.py")
    assert len(result.heritage) >= 1
    ext = [h for h in result.heritage if h[0] == "Dog" and h[2] == "Animal"]
    assert len(ext) == 1
    assert ext[0][1] == "extends"


def test_parse_multiple_inheritance():
    from scripts.context.python_parser import PythonParser
    source = "class C(A, B):\n    pass\n"
    result = PythonParser.parse(source, "multi.py")
    parents = {h[2] for h in result.heritage if h[0] == "C"}
    assert parents == {"A", "B"}


def test_parse_no_heritage():
    from scripts.context.python_parser import PythonParser
    source = "class Plain:\n    pass\n"
    result = PythonParser.parse(source, "plain.py")
    assert result.heritage == []


# --- Type annotation extraction ---


def test_parse_param_type():
    from scripts.context.python_parser import PythonParser
    source = "def greet(name: str) -> None:\n    pass\n"
    result = PythonParser.parse(source, "typed.py")
    type_names = {t.name for t in result.type_refs}
    assert "str" in type_names


def test_parse_return_type():
    from scripts.context.python_parser import PythonParser
    source = "def count() -> int:\n    return 0\n"
    result = PythonParser.parse(source, "typed.py")
    type_names = {t.name for t in result.type_refs}
    assert "int" in type_names


def test_parse_complex_type():
    from scripts.context.python_parser import PythonParser
    source = "def items() -> list[str]:\n    return []\n"
    result = PythonParser.parse(source, "typed.py")
    type_names = {t.name for t in result.type_refs}
    assert "list" in type_names


# --- __all__ exports ---


def test_parse_all_exports():
    from scripts.context.python_parser import PythonParser
    source = '__all__ = ["foo", "bar"]\ndef foo(): pass\ndef bar(): pass\n'
    result = PythonParser.parse(source, "exports.py")
    assert set(result.exports) == {"foo", "bar"}


def test_parse_no_all_exports():
    from scripts.context.python_parser import PythonParser
    source = "def foo(): pass\n"
    result = PythonParser.parse(source, "noexport.py")
    assert result.exports == []


# --- Empty and error handling ---


def test_parse_empty_source():
    from scripts.context.python_parser import PythonParser
    result = PythonParser.parse("", "empty.py")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []
    assert result.heritage == []
    assert result.type_refs == []


def test_parse_syntax_error_returns_empty():
    from scripts.context.python_parser import PythonParser
    result = PythonParser.parse("def broken(:", "bad.py")
    assert result.symbols == []
