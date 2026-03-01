# Plan 02: Multi-language file walker and tree-sitter parser framework with Python, TypeScript, and JavaScript support

## Goal
Multi-language file walker and tree-sitter parser framework with Python, TypeScript, and JavaScript support

## Tasks

### Task 1: Multi-language file walker
**Files:** `.cnogo/scripts/context/walker.py`, `tests/test_context_walker.py`
**Action:**
Rebuild walker.py to discover files for all supported languages, not just Python. Define SUPPORTED_EXTENSIONS dict mapping file extensions to language identifiers. Use pathlib to walk the repo once, matching against all supported extensions. Return FileEntry objects with correct language field. Keep the same public API: walk(repo_path) -> list[FileEntry].

**Micro-steps:**
- Write failing test: test_context_walker.py — discover .py, .ts, .tsx, .js, .jsx files; skip .git/node_modules/etc; respect .gitignore; FileEntry has correct language field
- Run failing tests to verify RED
- Implement walker.py with SUPPORTED_EXTENSIONS dict mapping extensions to language names (python, typescript, javascript, go, java, rust, etc.)
- Walk repo using pathlib.rglob for each supported extension pattern
- Preserve existing skip logic (_DEFAULT_SKIP, _load_gitignore, _is_ignored) but expand to all languages
- Run passing tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_walker.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_walker.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_walker.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Abstract LanguageParser base and PythonParser
**Files:** `.cnogo/scripts/context/parser_base.py`, `.cnogo/scripts/context/parsers/__init__.py`, `.cnogo/scripts/context/parsers/python_parser.py`, `tests/test_context_python_parser.py`
**Action:**
Create the parser framework. parser_base.py defines abstract LanguageParser with parse() method and IR dataclasses (SymbolInfo, ImportInfo, CallInfo, TypeRef, ParseResult). PythonParser uses tree-sitter-python grammar to extract symbols, imports, calls, heritage, and type references from Python source. Follow Axon pattern: tree-sitter query strings for each construct type.

**Micro-steps:**
- Create parser_base.py with abstract LanguageParser class defining parse(content, file_path) -> ParseResult
- Create IR dataclasses: SymbolInfo (name, kind, start_line, end_line, signature, docstring), ImportInfo (module, names, alias), CallInfo (caller, callee, line, confidence), TypeRef (name, kind), ParseResult (symbols, imports, calls, type_refs, heritage)
- Write failing test for PythonParser using tree-sitter-python
- Implement PythonParser in parsers/python_parser.py using py-tree-sitter with tree-sitter-python grammar
- Extract functions, classes, methods, imports, calls from Python AST via tree-sitter queries
- Run passing tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_python_parser.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_python_parser.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_python_parser.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: TypeScript/JavaScript parsers and parser registry
**Files:** `.cnogo/scripts/context/parsers/typescript_parser.py`, `.cnogo/scripts/context/parsers/javascript_parser.py`, `.cnogo/scripts/context/parser_registry.py`, `tests/test_context_ts_parser.py`
**Action:**
Create TypeScript and JavaScript parsers using tree-sitter grammars. TypeScriptParser extracts interfaces, type aliases, enums in addition to standard symbols. JavaScriptParser handles JSX and CommonJS/ESM imports. Create parser_registry.py with get_parser(language) function and _PARSER_CACHE dict for parser instance reuse (Axon pattern). Registry maps language string to parser class.

**Micro-steps:**
- Write failing test for TypeScriptParser: extract classes, interfaces, functions, imports, exports, type aliases from TS code
- Implement TypeScriptParser using tree-sitter-typescript grammar
- Implement JavaScriptParser (can extend TypeScriptParser with JS-specific adjustments or be a thin wrapper)
- Create parser_registry.py: get_parser(language) -> LanguageParser with _PARSER_CACHE dict for instance reuse
- Register python, typescript, javascript parsers in registry
- Run passing tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_ts_parser.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_ts_parser.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_ts_parser.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_walker.py tests/test_context_python_parser.py tests/test_context_ts_parser.py -v 2>&1 | tail -10
```

## Commit Message
```
feat(context-graph): multi-language walker + tree-sitter parser framework
```
