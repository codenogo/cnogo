"""Tests for context graph SQLite storage backend."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_graph.db"


@pytest.fixture
def storage(db_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(db_path)
    s.initialize()
    yield s
    s.close()


# --- Initialization ---


def test_initialize_creates_db(db_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(db_path)
    s.initialize()
    assert db_path.exists()
    s.close()


def test_is_initialized_true_after_init(storage):
    assert storage.is_initialized()


def test_is_initialized_false_before_init(db_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(db_path)
    assert not s.is_initialized()


# --- Node CRUD ---


def _make_node(nid="function:foo.py:bar", label=NodeLabel.FUNCTION,
               name="bar", file_path="foo.py", **kwargs):
    return GraphNode(id=nid, label=label, name=name, file_path=file_path, **kwargs)


def test_add_and_get_node(storage):
    node = _make_node()
    storage.add_nodes([node])
    result = storage.get_node("function:foo.py:bar")
    assert result is not None
    assert result.id == "function:foo.py:bar"
    assert result.label == NodeLabel.FUNCTION
    assert result.name == "bar"
    assert result.file_path == "foo.py"


def test_get_node_not_found(storage):
    assert storage.get_node("nonexistent") is None


def test_add_node_with_all_fields(storage):
    node = GraphNode(
        id="method:a.py:Cls.run",
        label=NodeLabel.METHOD,
        name="run",
        file_path="a.py",
        start_line=10,
        end_line=25,
        content="def run(self): pass",
        signature="def run(self)",
        language="python",
        class_name="Cls",
        is_dead=False,
        is_entry_point=True,
        is_exported=True,
        properties={"decorators": ["staticmethod"]},
    )
    storage.add_nodes([node])
    result = storage.get_node("method:a.py:Cls.run")
    assert result.start_line == 10
    assert result.end_line == 25
    assert result.content == "def run(self): pass"
    assert result.signature == "def run(self)"
    assert result.language == "python"
    assert result.class_name == "Cls"
    assert result.is_entry_point is True
    assert result.is_exported is True
    assert result.properties["decorators"] == ["staticmethod"]


def test_add_nodes_upsert(storage):
    node1 = _make_node(name="bar")
    storage.add_nodes([node1])
    node2 = _make_node(name="bar_updated")
    storage.add_nodes([node2])
    result = storage.get_node("function:foo.py:bar")
    assert result.name == "bar_updated"


def test_add_multiple_nodes(storage):
    nodes = [
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ]
    storage.add_nodes(nodes)
    assert storage.get_node("function:a.py:foo") is not None
    assert storage.get_node("function:b.py:bar") is not None


# --- Relationship CRUD ---


def _make_rel(rid="calls:a->b", rtype=RelType.CALLS,
              source="function:a.py:foo", target="function:b.py:bar",
              **kwargs):
    return GraphRelationship(id=rid, type=rtype, source=source, target=target,
                             **kwargs)


def test_add_and_get_relationship(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    rel = _make_rel()
    storage.add_relationships([rel])

    callers = storage.get_callers_with_confidence("function:b.py:bar")
    assert len(callers) == 1
    assert callers[0][0].id == "function:a.py:foo"


def test_get_callees(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_make_rel()])

    callees = storage.get_callees("function:a.py:foo")
    assert len(callees) == 1
    assert callees[0].id == "function:b.py:bar"


def test_relationship_with_properties(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    rel = _make_rel(properties={"confidence": 0.8})
    storage.add_relationships([rel])

    callers = storage.get_callers_with_confidence("function:b.py:bar")
    assert len(callers) == 1
    node, confidence = callers[0]
    assert node.id == "function:a.py:foo"
    assert confidence == 0.8


def test_get_callers_empty(storage):
    storage.add_nodes([_make_node()])
    assert storage.get_callers_with_confidence("function:foo.py:bar") == []


# --- File hash tracking ---


def test_get_indexed_files_empty(storage):
    assert storage.get_indexed_files() == {}


def test_update_and_get_file_hash(storage):
    storage.update_file_hash("foo.py", "abc123")
    files = storage.get_indexed_files()
    assert files == {"foo.py": "abc123"}


def test_update_file_hash_upsert(storage):
    storage.update_file_hash("foo.py", "abc123")
    storage.update_file_hash("foo.py", "def456")
    files = storage.get_indexed_files()
    assert files["foo.py"] == "def456"


# --- Remove by file ---


def test_remove_nodes_by_file(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:a.py:bar", name="bar", file_path="a.py"),
        _make_node("function:b.py:baz", name="baz", file_path="b.py"),
    ])
    storage.remove_nodes_by_file("a.py")
    assert storage.get_node("function:a.py:foo") is None
    assert storage.get_node("function:a.py:bar") is None
    assert storage.get_node("function:b.py:baz") is not None


def test_remove_nodes_also_removes_relationships(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_make_rel(
        source="function:a.py:foo", target="function:b.py:bar"
    )])
    storage.remove_nodes_by_file("a.py")
    # Relationship should be gone since source node was removed
    assert storage.get_callers_with_confidence("function:b.py:bar") == []


def test_remove_file_hash(storage):
    storage.update_file_hash("a.py", "abc")
    storage.remove_file_hash("a.py")
    assert storage.get_indexed_files() == {}


# --- Node count ---


def test_node_count_empty(storage):
    assert storage.node_count() == 0


def test_node_count_after_add(storage):
    storage.add_nodes([_make_node(), _make_node("class:a.py:Cls",
                       label=NodeLabel.CLASS, name="Cls", file_path="a.py")])
    assert storage.node_count() == 2


def test_relationship_count_empty(storage):
    assert storage.relationship_count() == 0


def test_relationship_count_after_add(storage):
    storage.add_nodes([
        _make_node("fn:a.py:foo", name="foo"),
        _make_node("fn:a.py:bar", name="bar"),
    ])
    storage.add_relationships([
        GraphRelationship(id="r1", type=RelType.CALLS, source="fn:a.py:foo", target="fn:a.py:bar"),
    ])
    assert storage.relationship_count() == 1


def test_file_count_empty(storage):
    assert storage.file_count() == 0


def test_file_count_after_update(storage):
    # file_count() counts FILE-label GraphNode entries, not FileHash rows
    storage.add_nodes([
        _make_node("file:a.py:", label=NodeLabel.FILE, name="a.py", file_path="a.py"),
        _make_node("file:b.py:", label=NodeLabel.FILE, name="b.py", file_path="b.py"),
    ])
    assert storage.file_count() == 2


# --- get_all_relationships_by_types ---


def test_get_all_relationships_by_types_empty(storage):
    result = storage.get_all_relationships_by_types([RelType.CALLS.value])
    assert result == []


def test_get_all_relationships_by_types_single_type(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([
        GraphRelationship(id="r1", type=RelType.CALLS, source="function:a.py:foo", target="function:b.py:bar"),
    ])
    result = storage.get_all_relationships_by_types([RelType.CALLS.value])
    assert len(result) == 1
    assert result[0] == ("function:a.py:foo", "function:b.py:bar", RelType.CALLS.value)


def test_get_all_relationships_by_types_multiple_types(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
        _make_node("function:c.py:baz", name="baz", file_path="c.py"),
    ])
    storage.add_relationships([
        GraphRelationship(id="r1", type=RelType.CALLS, source="function:a.py:foo", target="function:b.py:bar"),
        GraphRelationship(id="r2", type=RelType.IMPORTS, source="function:b.py:bar", target="function:c.py:baz"),
    ])
    result = storage.get_all_relationships_by_types([RelType.CALLS.value, RelType.IMPORTS.value])
    assert len(result) == 2
    sources = {r[0] for r in result}
    assert "function:a.py:foo" in sources
    assert "function:b.py:bar" in sources


def test_get_all_relationships_by_types_filters_other_types(storage):
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py"),
        _make_node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([
        GraphRelationship(id="r1", type=RelType.CALLS, source="function:a.py:foo", target="function:b.py:bar"),
        GraphRelationship(id="r2", type=RelType.EXTENDS, source="function:a.py:foo", target="function:b.py:bar"),
    ])
    result = storage.get_all_relationships_by_types([RelType.CALLS.value])
    assert len(result) == 1
    assert result[0][2] == RelType.CALLS.value


# --- FTS5 Search ---


def test_search_returns_empty_for_no_match(storage):
    """search() returns empty list when nothing matches."""
    storage.add_nodes([_make_node(content="hello world")])
    storage.rebuild_fts()
    results = storage.search("zzzznotfound")
    assert results == []


def test_search_finds_by_name(storage):
    """search() finds nodes by name."""
    storage.add_nodes([
        _make_node("function:a.py:calculate_sum", name="calculate_sum", file_path="a.py"),
        _make_node("function:b.py:send_email", name="send_email", file_path="b.py"),
    ])
    storage.rebuild_fts()
    results = storage.search("calculate")
    assert len(results) >= 1
    assert any(n.name == "calculate_sum" for n, _ in results)


def test_search_finds_by_signature(storage):
    """search() finds nodes by signature text."""
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py",
                    signature="def foo(x: int, y: int) -> int"),
    ])
    storage.rebuild_fts()
    results = storage.search("int")
    assert len(results) >= 1
    assert results[0][0].name == "foo"


def test_search_finds_by_content(storage):
    """search() finds nodes by content/docstring text."""
    storage.add_nodes([
        _make_node("function:a.py:parse", name="parse", file_path="a.py",
                    content="Parse a configuration file and return settings"),
    ])
    storage.rebuild_fts()
    results = storage.search("configuration")
    assert len(results) >= 1
    assert results[0][0].name == "parse"


def test_search_substring_match(storage):
    """CONTAINS-based search matches substrings."""
    storage.add_nodes([
        _make_node("function:a.py:parse", name="parse", file_path="a.py",
                    content="Parse a document"),
    ])
    storage.rebuild_fts()
    results = storage.search("parse")
    assert len(results) >= 1
    assert results[0][0].name == "parse"


def test_search_returns_ranked_results(storage):
    """Results are ranked by BM25 relevance."""
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py",
                    content="unrelated stuff"),
        _make_node("function:b.py:search_engine", name="search_engine", file_path="b.py",
                    content="Search through the search index for search results"),
    ])
    storage.rebuild_fts()
    results = storage.search("search")
    assert len(results) >= 1
    # search_engine should rank higher (more occurrences of 'search')
    assert results[0][0].name == "search_engine"


def test_search_respects_limit(storage):
    """search() limit parameter caps results."""
    nodes = [
        _make_node(f"function:a.py:func{i}", name=f"func{i}", file_path="a.py",
                    content="common keyword stuff")
        for i in range(10)
    ]
    storage.add_nodes(nodes)
    storage.rebuild_fts()
    results = storage.search("common", limit=3)
    assert len(results) == 3


def test_search_fts_cleaned_on_node_removal(storage):
    """FTS entries are removed when nodes are removed by file."""
    storage.add_nodes([
        _make_node("function:a.py:target", name="target", file_path="a.py",
                    content="unique_keyword_xyz"),
        _make_node("function:b.py:other", name="other", file_path="b.py",
                    content="something else"),
    ])
    storage.rebuild_fts()
    # Should find it before removal
    assert len(storage.search("unique_keyword_xyz")) == 1
    # Remove the file
    storage.remove_nodes_by_file("a.py")
    storage.rebuild_fts()
    # Should not find it after removal
    assert len(storage.search("unique_keyword_xyz")) == 0


def test_search_handles_special_characters(storage):
    """search() handles special FTS characters gracefully."""
    storage.add_nodes([
        _make_node("function:a.py:foo", name="foo", file_path="a.py",
                    content="handles (parentheses) and [brackets]"),
    ])
    storage.rebuild_fts()
    # Should not crash on special characters
    results = storage.search("parentheses")
    assert len(results) >= 1
