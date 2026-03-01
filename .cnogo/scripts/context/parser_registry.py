"""Parser registry for language-specific parsers.

Maps language identifiers to parser instances with lazy initialization
and instance caching.
"""

from __future__ import annotations

from .parser_base import LanguageParser

# Cache for parser instances — reuse across calls
_PARSER_CACHE: dict[str, LanguageParser] = {}


def _create_parser(language: str) -> LanguageParser | None:
    """Create a parser instance for the given language."""
    if language == "python":
        from .parsers.python_parser import PythonParser
        return PythonParser()
    elif language == "typescript":
        from .parsers.typescript_parser import TypeScriptParser
        return TypeScriptParser(tsx=False)
    elif language == "javascript":
        from .parsers.javascript_parser import JavaScriptParser
        return JavaScriptParser()
    return None


def get_parser(language: str) -> LanguageParser | None:
    """Get a parser for the given language identifier.

    Returns a cached parser instance, or None if the language is not supported.
    Language identifiers match walker.SUPPORTED_EXTENSIONS values.
    """
    if language not in _PARSER_CACHE:
        parser = _create_parser(language)
        if parser is None:
            return None
        _PARSER_CACHE[language] = parser
    return _PARSER_CACHE[language]


def supported_languages() -> list[str]:
    """Return list of languages with parser support."""
    return ["python", "typescript", "javascript"]


def clear_cache() -> None:
    """Clear the parser cache (useful for testing)."""
    _PARSER_CACHE.clear()
