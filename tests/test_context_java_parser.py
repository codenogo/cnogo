"""Tests for Java parser."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".cnogo")

pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_java")

from scripts.context.parser_base import LanguageParser, ParseResult
from scripts.context.parsers.java_parser import JavaParser


# --- Java: classes ---


def test_java_parse_class():
    parser = JavaParser()
    source = "public class Animal {\n    private String name;\n}\n"
    result = parser.parse(source, "Animal.java")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "Animal"


def test_java_parse_class_with_methods():
    parser = JavaParser()
    source = "public class Calc {\n    public int add(int a, int b) {\n        return a + b;\n    }\n    public int sub(int a, int b) {\n        return a - b;\n    }\n}\n"
    result = parser.parse(source, "Calc.java")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert names == {"add", "sub"}
    assert all(m.class_name == "Calc" for m in methods)


# --- Java: interfaces ---


def test_java_parse_interface():
    parser = JavaParser()
    source = "public interface Readable {\n    byte[] read();\n}\n"
    result = parser.parse(source, "Readable.java")
    ifaces = [s for s in result.symbols if s.kind == "interface"]
    assert len(ifaces) == 1
    assert ifaces[0].name == "Readable"


# --- Java: enums ---


def test_java_parse_enum():
    parser = JavaParser()
    source = "public enum Status {\n    ACTIVE,\n    INACTIVE,\n    PENDING\n}\n"
    result = parser.parse(source, "Status.java")
    enums = [s for s in result.symbols if s.kind == "enum"]
    assert len(enums) == 1
    assert enums[0].name == "Status"


# --- Java: methods ---


def test_java_parse_method():
    parser = JavaParser()
    source = "public class Greeter {\n    public String greet(String name) {\n        return \"Hello \" + name;\n    }\n}\n"
    result = parser.parse(source, "Greeter.java")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "greet"
    assert methods[0].class_name == "Greeter"


# --- Java: constructors ---


def test_java_parse_constructor():
    parser = JavaParser()
    source = "public class Person {\n    private String name;\n    public Person(String name) {\n        this.name = name;\n    }\n}\n"
    result = parser.parse(source, "Person.java")
    constructors = [s for s in result.symbols if s.kind == "method" and s.name == "Person"]
    assert len(constructors) == 1
    assert constructors[0].class_name == "Person"


# --- Java: imports ---


def test_java_parse_import():
    parser = JavaParser()
    source = "import java.util.List;\nimport java.util.Map;\n\npublic class App {}\n"
    result = parser.parse(source, "App.java")
    assert len(result.imports) == 2
    modules = {i.module for i in result.imports}
    assert "java.util" in modules


def test_java_parse_import_names():
    parser = JavaParser()
    source = "import java.util.ArrayList;\n"
    result = parser.parse(source, "App.java")
    assert len(result.imports) == 1
    assert result.imports[0].module == "java.util"
    assert "ArrayList" in result.imports[0].names


# --- Java: calls ---


def test_java_parse_call():
    parser = JavaParser()
    source = 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("hello");\n        greet("world");\n    }\n}\n'
    result = parser.parse(source, "Main.java")
    callees = {c.callee for c in result.calls}
    assert "greet" in callees


# --- Java: empty ---


def test_java_parse_empty():
    parser = JavaParser()
    result = parser.parse("", "Empty.java")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []


# --- Java: extends ---


def test_java_parse_extends():
    parser = JavaParser()
    source = "public class Dog extends Animal {\n    public void bark() {}\n}\n"
    result = parser.parse(source, "Dog.java")
    extends = [h for h in result.heritage if h[0] == "Dog" and h[2] == "extends"]
    assert len(extends) == 1
    assert extends[0][1] == "Animal"


# --- Java: implements ---


def test_java_parse_implements():
    parser = JavaParser()
    source = "public class Server implements Runnable {\n    public void run() {}\n}\n"
    result = parser.parse(source, "Server.java")
    implements = [h for h in result.heritage if h[0] == "Server" and h[2] == "implements"]
    assert len(implements) == 1
    assert implements[0][1] == "Runnable"


def test_java_parse_extends_and_implements():
    parser = JavaParser()
    source = "public class Server extends BaseServer implements Runnable {\n    public void run() {}\n}\n"
    result = parser.parse(source, "Server.java")
    extends = [h for h in result.heritage if h[2] == "extends"]
    implements = [h for h in result.heritage if h[2] == "implements"]
    assert len(extends) >= 1
    assert len(implements) >= 1


# --- Java: is LanguageParser ---


def test_java_parser_is_language_parser():
    parser = JavaParser()
    assert isinstance(parser, LanguageParser)
