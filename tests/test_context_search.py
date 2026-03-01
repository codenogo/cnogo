"""Tests for BM25 and fuzzy search engines."""
from __future__ import annotations

import sys
sys.path.insert(0, ".cnogo")

from pathlib import Path
import pytest

from scripts.context.model import GraphNode, NodeLabel, generate_id
from scripts.context.storage import GraphStorage
from scripts.context.search import SearchResult, BM25Search, FuzzySearch


@pytest.fixture
def storage(tmp_path):
    """Create an initialized GraphStorage for testing."""
    s = GraphStorage(tmp_path / "testdb")
    s.initialize()
    yield s
    s.close()


def _add_symbol(storage, name, label=NodeLabel.FUNCTION, file_path="main.py",
                signature="", content="", start_line=1):
    """Helper to add a symbol node."""
    node = GraphNode(
        id=generate_id(label, file_path, name),
        label=label,
        name=name,
        file_path=file_path,
        signature=signature,
        content=content,
        start_line=start_line,
    )
    storage.add_nodes([node])
    return node


# ---------------------------------------------------------------------------
# SearchResult dataclass tests
# ---------------------------------------------------------------------------

def test_search_result_fields():
    """Verify SearchResult has node_id, name, score, source fields."""
    result = SearchResult(node_id="fn:main.py:helper", name="helper", score=1.5, source="bm25")
    assert result.node_id == "fn:main.py:helper"
    assert result.name == "helper"
    assert result.score == 1.5
    assert result.source == "bm25"


# ---------------------------------------------------------------------------
# BM25Search tests
# ---------------------------------------------------------------------------

def test_bm25_empty_index_returns_empty(storage):
    """Search on empty storage returns []."""
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("helper")
    assert results == []


def test_bm25_finds_exact_name_match(storage):
    """Searching 'helper' finds a function named 'helper'."""
    # Need at least 3 docs for BM25 IDF to be non-zero
    _add_symbol(storage, "helper")
    _add_symbol(storage, "unrelated_func")
    _add_symbol(storage, "another_method")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("helper")
    names = [r.name for r in results]
    assert "helper" in names


def test_bm25_finds_by_signature(storage):
    """Searching signature text finds matching node."""
    _add_symbol(storage, "compute", signature="def compute(x: int, y: int) -> int")
    _add_symbol(storage, "other_func", signature="def other_func() -> None")
    _add_symbol(storage, "another_method", signature="def another_method() -> None")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("compute")
    names = [r.name for r in results]
    assert "compute" in names


def test_bm25_finds_by_content(storage):
    """Searching content snippet finds matching node."""
    _add_symbol(storage, "process_data", content="This function processes data using algorithms")
    _add_symbol(storage, "other_func", content="This is a completely different function")
    _add_symbol(storage, "another_method", content="Another unrelated method for testing")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("algorithms")
    names = [r.name for r in results]
    assert "process_data" in names


def test_bm25_results_sorted_by_score(storage):
    """Results are sorted descending by score."""
    _add_symbol(storage, "helper", signature="helper helper helper")
    _add_symbol(storage, "helper_lite", signature="helper")
    _add_symbol(storage, "unrelated_thing", signature="unrelated thing here")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("helper")
    assert len(results) >= 2
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_bm25_respects_limit(storage):
    """limit=1 returns at most 1 result."""
    _add_symbol(storage, "helper_a")
    _add_symbol(storage, "helper_b")
    _add_symbol(storage, "helper_c")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("helper", limit=1)
    assert len(results) <= 1


def test_bm25_source_is_bm25(storage):
    """All results have source='bm25'."""
    _add_symbol(storage, "helper")
    _add_symbol(storage, "other_func")
    _add_symbol(storage, "another_method")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("helper")
    assert len(results) > 0
    for r in results:
        assert r.source == "bm25"


def test_bm25_no_results_for_nonsense(storage):
    """Gibberish query returns empty."""
    _add_symbol(storage, "helper")
    _add_symbol(storage, "compute")
    _add_symbol(storage, "another_method")
    bm25 = BM25Search()
    bm25.build_index(storage)
    results = bm25.search("xyzzy_nonsense_qqqqq")
    assert results == []


# ---------------------------------------------------------------------------
# FuzzySearch tests
# ---------------------------------------------------------------------------

def test_fuzzy_empty_index_returns_empty(storage):
    """Search on empty storage returns []."""
    fuzzy = FuzzySearch()
    fuzzy.build_index(storage)
    results = fuzzy.search("helper")
    assert results == []


def test_fuzzy_finds_approximate_match(storage):
    """'helpr' matches 'helper' (typo handling)."""
    _add_symbol(storage, "helper")
    fuzzy = FuzzySearch(threshold=0.4)
    fuzzy.build_index(storage)
    results = fuzzy.search("helpr")
    names = [r.name for r in results]
    assert "helper" in names


def test_fuzzy_finds_partial_match(storage):
    """'help' matches 'helper' (partial name)."""
    _add_symbol(storage, "helper")
    fuzzy = FuzzySearch(threshold=0.4)
    fuzzy.build_index(storage)
    results = fuzzy.search("help")
    names = [r.name for r in results]
    assert "helper" in names


def test_fuzzy_threshold_filters(storage):
    """Very dissimilar strings are excluded."""
    _add_symbol(storage, "totally_different_function_xyz")
    fuzzy = FuzzySearch(threshold=0.8)
    fuzzy.build_index(storage)
    results = fuzzy.search("abc")
    assert results == []


def test_fuzzy_results_sorted_by_score(storage):
    """Results sorted descending by score."""
    _add_symbol(storage, "helper")
    _add_symbol(storage, "help")
    fuzzy = FuzzySearch(threshold=0.4)
    fuzzy.build_index(storage)
    results = fuzzy.search("helper")
    assert len(results) >= 2
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_fuzzy_source_is_fuzzy(storage):
    """All results have source='fuzzy'."""
    _add_symbol(storage, "helper")
    fuzzy = FuzzySearch(threshold=0.4)
    fuzzy.build_index(storage)
    results = fuzzy.search("helper")
    assert len(results) > 0
    for r in results:
        assert r.source == "fuzzy"


def test_fuzzy_case_insensitive(storage):
    """'HELPER' matches 'helper'."""
    _add_symbol(storage, "helper")
    fuzzy = FuzzySearch(threshold=0.4)
    fuzzy.build_index(storage)
    results = fuzzy.search("HELPER")
    names = [r.name for r in results]
    assert "helper" in names
