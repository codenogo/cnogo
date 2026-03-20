"""Tests for Rust parser."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, ".cnogo")

pytest.importorskip("tree_sitter")
pytest.importorskip("tree_sitter_rust")

from scripts.context.parser_base import LanguageParser, ParseResult
from scripts.context.parsers.rust_parser import RustParser


# --- Rust: functions ---


def test_rust_parse_function():
    parser = RustParser()
    source = 'fn greet(name: &str) -> String {\n    format!("Hello {}", name)\n}\n'
    result = parser.parse(source, "greet.rs")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "greet"
    assert "greet" in funcs[0].signature


def test_rust_parse_function_no_return():
    parser = RustParser()
    source = "fn do_nothing() {\n    // nothing\n}\n"
    result = parser.parse(source, "noop.rs")
    funcs = [s for s in result.symbols if s.kind == "function"]
    assert len(funcs) == 1
    assert funcs[0].name == "do_nothing"


# --- Rust: methods (impl block) ---


def test_rust_parse_method():
    parser = RustParser()
    source = "struct Dog {\n    name: String,\n}\n\nimpl Dog {\n    fn bark(&self) -> String {\n        self.name.clone()\n    }\n}\n"
    result = parser.parse(source, "dog.rs")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "bark"
    assert methods[0].class_name == "Dog"


def test_rust_parse_impl_multiple_methods():
    parser = RustParser()
    source = "struct Calc;\n\nimpl Calc {\n    fn add(&self, a: i32, b: i32) -> i32 { a + b }\n    fn sub(&self, a: i32, b: i32) -> i32 { a - b }\n}\n"
    result = parser.parse(source, "calc.rs")
    methods = [s for s in result.symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert names == {"add", "sub"}


# --- Rust: structs ---


def test_rust_parse_struct():
    parser = RustParser()
    source = "struct Config {\n    host: String,\n    port: u16,\n}\n"
    result = parser.parse(source, "config.rs")
    structs = [s for s in result.symbols if s.kind == "class"]
    assert len(structs) == 1
    assert structs[0].name == "Config"


# --- Rust: enums ---


def test_rust_parse_enum():
    parser = RustParser()
    source = "enum Status {\n    Active,\n    Inactive,\n    Pending,\n}\n"
    result = parser.parse(source, "status.rs")
    enums = [s for s in result.symbols if s.kind == "enum"]
    assert len(enums) == 1
    assert enums[0].name == "Status"


# --- Rust: traits ---


def test_rust_parse_trait():
    parser = RustParser()
    source = "trait Readable {\n    fn read(&self) -> Vec<u8>;\n}\n"
    result = parser.parse(source, "readable.rs")
    traits = [s for s in result.symbols if s.kind == "interface"]
    assert len(traits) == 1
    assert traits[0].name == "Readable"


# --- Rust: type alias ---


def test_rust_parse_type_alias():
    parser = RustParser()
    source = "type Result<T> = std::result::Result<T, MyError>;\n"
    result = parser.parse(source, "types.rs")
    aliases = [s for s in result.symbols if s.kind == "type_alias"]
    assert len(aliases) == 1
    assert aliases[0].name == "Result"


# --- Rust: use imports ---


def test_rust_parse_use_simple():
    parser = RustParser()
    source = "use std::io::Read;\n"
    result = parser.parse(source, "lib.rs")
    assert len(result.imports) == 1
    assert result.imports[0].module == "std::io"
    assert "Read" in result.imports[0].names


def test_rust_parse_use_grouped():
    parser = RustParser()
    source = "use std::collections::{HashMap, HashSet};\n"
    result = parser.parse(source, "lib.rs")
    assert len(result.imports) == 1
    assert result.imports[0].module == "std::collections"
    assert "HashMap" in result.imports[0].names
    assert "HashSet" in result.imports[0].names


# --- Rust: calls ---


def test_rust_parse_call():
    parser = RustParser()
    source = 'fn main() {\n    println!("hello");\n    greet("world");\n    String::from("test");\n}\n'
    result = parser.parse(source, "main.rs")
    callees = {c.callee for c in result.calls}
    assert "greet" in callees


# --- Rust: empty ---


def test_rust_parse_empty():
    parser = RustParser()
    result = parser.parse("", "empty.rs")
    assert result.symbols == []
    assert result.imports == []
    assert result.calls == []


# --- Rust: heritage (impl Trait for Struct) ---


def test_rust_parse_impl_trait():
    parser = RustParser()
    source = "trait Animal {\n    fn speak(&self) -> String;\n}\n\nstruct Dog;\n\nimpl Animal for Dog {\n    fn speak(&self) -> String {\n        String::from(\"Woof\")\n    }\n}\n"
    result = parser.parse(source, "animals.rs")
    implements = [h for h in result.heritage if h[0] == "Dog" and h[2] == "implements"]
    assert len(implements) == 1
    assert implements[0][1] == "Animal"


# --- Rust: is LanguageParser ---


def test_rust_parser_is_language_parser():
    parser = RustParser()
    assert isinstance(parser, LanguageParser)
