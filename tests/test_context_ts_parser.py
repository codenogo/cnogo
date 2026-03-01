"""Tests for TypeScript parser, JavaScript parser, and parser registry."""

from __future__ import annotations

import sys

sys.path.insert(0, ".cnogo")

from scripts.context.parser_base import LanguageParser, ParseResult
from scripts.context.parsers.typescript_parser import TypeScriptParser
from scripts.context.parsers.javascript_parser import JavaScriptParser
from scripts.context.parser_registry import get_parser, supported_languages, clear_cache


# --- TypeScript: functions ---


def test_ts_parse_function():
    parser = TypeScriptParser()
    source = 'function greet(name: string): string {\n    return "Hello " + name;\n}\n'
    result = parser.parse(source, "greet.ts")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"
    assert "name: string" in funcs[0].signature
    assert "string" in funcs[0].signature


def test_ts_parse_arrow_function():
    parser = TypeScriptParser()
    source = "const double = (x: number): number => {\n    return x * 2;\n};\n"
    result = parser.parse(source, "arrow.ts")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) >= 1
    assert any(f.name == "double" for f in funcs)


# --- TypeScript: classes ---


def test_ts_parse_class():
    parser = TypeScriptParser()
    source = "class Animal {\n    name: string;\n    speak(): void {}\n}\n"
    result = parser.parse(source, "animal.ts")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "Animal"


def test_ts_parse_class_methods():
    parser = TypeScriptParser()
    source = "class Calc {\n    add(a: number, b: number): number { return a + b; }\n    sub(a: number, b: number): number { return a - b; }\n}\n"
    result = parser.parse(source, "calc.ts")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert names == {"add", "sub"}
    assert all(m.class_name == "Calc" for m in methods)


def test_ts_parse_class_extends():
    parser = TypeScriptParser()
    source = "class Dog extends Animal {\n    bark(): void {}\n}\n"
    result = parser.parse(source, "dog.ts")
    assert len(result.heritage) >= 1
    extends = [h for h in result.heritage if h[0] == "Dog" and h[2] == "extends"]
    assert len(extends) == 1
    assert extends[0][1] == "Animal"


def test_ts_parse_class_implements():
    parser = TypeScriptParser()
    source = "class Server implements Config {\n    host: string = '';\n    port: number = 0;\n}\n"
    result = parser.parse(source, "server.ts")
    implements = [h for h in result.heritage if h[0] == "Server" and h[2] == "implements"]
    assert len(implements) == 1
    assert implements[0][1] == "Config"


def test_ts_parse_class_extends_and_implements():
    parser = TypeScriptParser()
    source = "class Server extends BaseServer implements Config {\n    start(): void {}\n}\n"
    result = parser.parse(source, "server.ts")
    extends = [h for h in result.heritage if h[2] == "extends"]
    implements = [h for h in result.heritage if h[2] == "implements"]
    assert len(extends) >= 1
    assert len(implements) >= 1


# --- TypeScript: interfaces ---


def test_ts_parse_interface():
    parser = TypeScriptParser()
    source = "interface Config {\n    host: string;\n    port: number;\n}\n"
    result = parser.parse(source, "config.ts")
    ifaces = [s for s in result.symbols if s.kind == "interface"]
    assert len(ifaces) == 1
    assert ifaces[0].name == "Config"


# --- TypeScript: type aliases ---


def test_ts_parse_type_alias():
    parser = TypeScriptParser()
    source = "type ID = string | number;\n"
    result = parser.parse(source, "types.ts")
    aliases = [s for s in result.symbols if s.kind == "type_alias"]
    assert len(aliases) == 1
    assert aliases[0].name == "ID"


# --- TypeScript: enums ---


def test_ts_parse_enum():
    parser = TypeScriptParser()
    source = 'enum Status {\n    Active = "active",\n    Inactive = "inactive"\n}\n'
    result = parser.parse(source, "status.ts")
    enums = [s for s in result.symbols if s.kind == "enum"]
    assert len(enums) == 1
    assert enums[0].name == "Status"


# --- TypeScript: imports ---


def test_ts_parse_named_import():
    parser = TypeScriptParser()
    source = 'import { Component, useState } from "react";\n'
    result = parser.parse(source, "app.ts")
    assert len(result.imports) == 1
    imp = result.imports[0]
    assert imp.module == "react"
    assert "Component" in imp.names
    assert "useState" in imp.names


def test_ts_parse_default_import():
    parser = TypeScriptParser()
    source = 'import React from "react";\n'
    result = parser.parse(source, "app.ts")
    assert len(result.imports) == 1
    assert result.imports[0].module == "react"
    assert "React" in result.imports[0].names


def test_ts_parse_namespace_import():
    parser = TypeScriptParser()
    source = 'import * as path from "path";\n'
    result = parser.parse(source, "util.ts")
    assert len(result.imports) == 1
    assert result.imports[0].module == "path"
    assert any("path" in n for n in result.imports[0].names)


# --- TypeScript: calls ---


def test_ts_parse_call():
    parser = TypeScriptParser()
    source = 'function main() {\n    console.log("hello");\n    greet("world");\n}\n'
    result = parser.parse(source, "main.ts")
    callees = {c.callee for c in result.calls}
    assert "console.log" in callees
    assert "greet" in callees


# --- TypeScript: type refs ---


def test_ts_parse_type_refs():
    parser = TypeScriptParser()
    source = "function process(input: Config): Result {\n    return {} as Result;\n}\n"
    result = parser.parse(source, "process.ts")
    type_names = {t.name for t in result.type_refs}
    assert "Config" in type_names
    assert "Result" in type_names


# --- TypeScript: empty ---


def test_ts_parse_empty():
    parser = TypeScriptParser()
    result = parser.parse("", "empty.ts")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []


# --- TypeScript: exported declarations ---


def test_ts_parse_exported_function():
    parser = TypeScriptParser()
    source = "export function greet(name: string): string {\n    return name;\n}\n"
    result = parser.parse(source, "lib.ts")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"


def test_ts_parse_exported_class():
    parser = TypeScriptParser()
    source = "export class App {\n    render(): void {}\n}\n"
    result = parser.parse(source, "app.ts")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "App"


# --- JavaScript: functions ---


def test_js_parse_function():
    parser = JavaScriptParser()
    source = 'function greet(name) {\n    return "Hello " + name;\n}\n'
    result = parser.parse(source, "greet.js")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"


def test_js_parse_arrow_function():
    parser = JavaScriptParser()
    source = "const double = (x) => {\n    return x * 2;\n};\n"
    result = parser.parse(source, "arrow.js")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) >= 1
    assert any(f.name == "double" for f in funcs)


# --- JavaScript: classes ---


def test_js_parse_class():
    parser = JavaScriptParser()
    source = "class Animal {\n    speak() {}\n}\n"
    result = parser.parse(source, "animal.js")
    classes = [s for s in result.symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "Animal"


def test_js_parse_class_extends():
    parser = JavaScriptParser()
    source = "class Dog extends Animal {\n    bark() {}\n}\n"
    result = parser.parse(source, "dog.js")
    extends = [h for h in result.heritage if h[0] == "Dog" and h[2] == "extends"]
    assert len(extends) == 1
    assert extends[0][1] == "Animal"


# --- JavaScript: imports ---


def test_js_parse_esm_import():
    parser = JavaScriptParser()
    source = 'import React from "react";\nimport { useState } from "react";\n'
    result = parser.parse(source, "app.js")
    assert len(result.imports) == 2
    modules = {i.module for i in result.imports}
    assert "react" in modules


# --- JavaScript: calls ---


def test_js_parse_call():
    parser = JavaScriptParser()
    source = 'function main() {\n    console.log("hi");\n    fetch("/api");\n}\n'
    result = parser.parse(source, "main.js")
    callees = {c.callee for c in result.calls}
    assert "console.log" in callees
    assert "fetch" in callees


# --- JavaScript: empty ---


def test_js_parse_empty():
    parser = JavaScriptParser()
    result = parser.parse("", "empty.js")
    assert result.symbols == []
    assert result.imports == []


# --- JavaScript: is LanguageParser ---


def test_js_parser_is_language_parser():
    parser = JavaScriptParser()
    assert isinstance(parser, LanguageParser)


# --- Parser registry ---


def test_registry_get_python():
    clear_cache()
    parser = get_parser("python")
    assert parser is not None
    assert isinstance(parser, LanguageParser)


def test_registry_get_typescript():
    clear_cache()
    parser = get_parser("typescript")
    assert parser is not None
    assert isinstance(parser, LanguageParser)


def test_registry_get_javascript():
    clear_cache()
    parser = get_parser("javascript")
    assert parser is not None
    assert isinstance(parser, LanguageParser)


def test_registry_unsupported_returns_none():
    clear_cache()
    parser = get_parser("cobol")
    assert parser is None


def test_registry_caches_instances():
    clear_cache()
    p1 = get_parser("python")
    p2 = get_parser("python")
    assert p1 is p2


def test_registry_supported_languages():
    langs = supported_languages()
    assert "python" in langs
    assert "typescript" in langs
    assert "javascript" in langs


def test_registry_parsers_produce_parse_result():
    """All registered parsers should return ParseResult."""
    clear_cache()
    for lang in supported_languages():
        parser = get_parser(lang)
        assert parser is not None
        result = parser.parse("", "test.x")
        assert isinstance(result, ParseResult)
