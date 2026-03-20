"""Tests for Go parser."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".cnogo")

pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_go")

from scripts.context.parser_base import LanguageParser, ParseResult
from scripts.context.parsers.go_parser import GoParser


# --- Go: functions ---


def test_go_parse_function():
    parser = GoParser()
    source = 'package main\n\nfunc greet(name string) string {\n    return "Hello " + name\n}\n'
    result = parser.parse(source, "greet.go")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"
    assert "greet" in funcs[0].signature


def test_go_parse_function_multiple_returns():
    parser = GoParser()
    source = 'package main\n\nfunc divide(a, b int) (int, error) {\n    return a / b, nil\n}\n'
    result = parser.parse(source, "math.go")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "divide"


# --- Go: methods ---


def test_go_parse_method():
    parser = GoParser()
    source = 'package main\n\ntype Dog struct {\n    Name string\n}\n\nfunc (d Dog) Bark() string {\n    return "Woof"\n}\n'
    result = parser.parse(source, "dog.go")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "Bark"
    assert methods[0].class_name == "Dog"


def test_go_parse_pointer_receiver_method():
    parser = GoParser()
    source = 'package main\n\ntype Server struct{}\n\nfunc (s *Server) Start() error {\n    return nil\n}\n'
    result = parser.parse(source, "server.go")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "Start"
    assert methods[0].class_name == "Server"


# --- Go: structs ---


def test_go_parse_struct():
    parser = GoParser()
    source = 'package main\n\ntype Config struct {\n    Host string\n    Port int\n}\n'
    result = parser.parse(source, "config.go")
    structs = [s for s in result.symbols if s.kind == "class"]
    assert len(structs) == 1
    assert structs[0].name == "Config"
    assert "struct" in structs[0].signature


# --- Go: interfaces ---


def test_go_parse_interface():
    parser = GoParser()
    source = 'package main\n\ntype Reader interface {\n    Read(p []byte) (n int, err error)\n}\n'
    result = parser.parse(source, "reader.go")
    ifaces = [s for s in result.symbols if s.kind == "interface"]
    assert len(ifaces) == 1
    assert ifaces[0].name == "Reader"
    assert "interface" in ifaces[0].signature


# --- Go: imports ---


def test_go_parse_single_import():
    parser = GoParser()
    source = 'package main\n\nimport "fmt"\n'
    result = parser.parse(source, "main.go")
    assert len(result.imports) == 1
    assert result.imports[0].module == "fmt"


def test_go_parse_grouped_imports():
    parser = GoParser()
    source = 'package main\n\nimport (\n    "fmt"\n    "os"\n    "strings"\n)\n'
    result = parser.parse(source, "main.go")
    assert len(result.imports) == 3
    modules = {i.module for i in result.imports}
    assert "fmt" in modules
    assert "os" in modules
    assert "strings" in modules


def test_go_parse_aliased_import():
    parser = GoParser()
    source = 'package main\n\nimport f "fmt"\n'
    result = parser.parse(source, "main.go")
    assert len(result.imports) == 1
    assert result.imports[0].module == "fmt"
    assert result.imports[0].alias == "f"


# --- Go: calls ---


def test_go_parse_call():
    parser = GoParser()
    source = 'package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("hello")\n    greet("world")\n}\n'
    result = parser.parse(source, "main.go")
    callees = {c.callee for c in result.calls}
    assert "fmt.Println" in callees
    assert "greet" in callees


# --- Go: empty ---


def test_go_parse_empty():
    parser = GoParser()
    result = parser.parse("package main\n", "empty.go")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []


# --- Go: heritage (embedded structs) ---


def test_go_parse_struct_embedding():
    parser = GoParser()
    source = 'package main\n\ntype Base struct {\n    ID int\n}\n\ntype Derived struct {\n    Base\n    Name string\n}\n'
    result = parser.parse(source, "embed.go")
    extends = [h for h in result.heritage if h[0] == "Derived" and h[2] == "extends"]
    assert len(extends) == 1
    assert extends[0][1] == "Base"


# --- Go: is LanguageParser ---


def test_go_parser_is_language_parser():
    parser = GoParser()
    assert isinstance(parser, LanguageParser)
