"""Tests for KuzuDB context graph storage backend."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / ".cnogo"))

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.storage import GraphStorage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_graph.kuzu"


@pytest.fixture
def storage(db_path):
    s = GraphStorage(db_path)
    s.initialize()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _node(
    nid: str = "function:foo.py:bar",
    label: NodeLabel = NodeLabel.FUNCTION,
    name: str = "bar",
    file_path: str = "foo.py",
    **kwargs,
) -> GraphNode:
    return GraphNode(id=nid, label=label, name=name, file_path=file_path, **kwargs)


def _rel(
    rid: str = "calls:a->b",
    rtype: RelType = RelType.CALLS,
    source: str = "function:a.py:foo",
    target: str = "function:b.py:bar",
    **kwargs,
) -> GraphRelationship:
    return GraphRelationship(id=rid, type=rtype, source=source, target=target, **kwargs)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_initialize(db_path):
    """initialize() creates schema; DB directory exists."""
    s = GraphStorage(db_path)
    s.initialize()
    assert db_path.exists()
    s.close()


# ---------------------------------------------------------------------------
# Node CRUD
# ---------------------------------------------------------------------------


def test_add_nodes(storage):
    """add_nodes() inserts GraphNode objects that can be retrieved."""
    nodes = [
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ]
    storage.add_nodes(nodes)
    assert storage.get_node("function:a.py:foo") is not None
    assert storage.get_node("function:b.py:bar") is not None


def test_get_node(storage):
    """get_node() returns correct node by ID with all fields."""
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
        embedding=[0.1, 0.2, 0.3],
    )
    storage.add_nodes([node])
    result = storage.get_node("method:a.py:Cls.run")
    assert result is not None
    assert result.id == "method:a.py:Cls.run"
    assert result.label == NodeLabel.METHOD
    assert result.name == "run"
    assert result.file_path == "a.py"
    assert result.start_line == 10
    assert result.end_line == 25
    assert result.content == "def run(self): pass"
    assert result.signature == "def run(self)"
    assert result.language == "python"
    assert result.class_name == "Cls"
    assert result.is_entry_point is True
    assert result.is_exported is True
    assert result.properties["decorators"] == ["staticmethod"]
    assert result.embedding == pytest.approx([0.1, 0.2, 0.3])


def test_get_node_not_found(storage):
    """get_node() returns None for unknown ID."""
    assert storage.get_node("nonexistent:id") is None


def test_get_nodes_by_file(storage):
    """get_nodes_by_file() returns all nodes with matching file_path."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:a.py:bar", name="bar", file_path="a.py"),
        _node("function:b.py:baz", name="baz", file_path="b.py"),
    ])
    result = storage.get_nodes_by_file("a.py")
    assert len(result) == 2
    ids = {n.id for n in result}
    assert ids == {"function:a.py:foo", "function:a.py:bar"}


def test_add_nodes_upsert(storage):
    """add_nodes() upserts: second add with same ID updates the record."""
    storage.add_nodes([_node(name="original")])
    storage.add_nodes([_node(name="updated")])
    result = storage.get_node("function:foo.py:bar")
    assert result is not None
    assert result.name == "updated"


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_add_relationships(storage):
    """add_relationships() inserts GraphRelationship objects."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_rel()])
    callers = storage.get_callers_with_confidence("function:b.py:bar")
    assert len(callers) == 1
    node, confidence = callers[0]
    assert node.id == "function:a.py:foo"


def test_get_related_nodes(storage):
    """get_related_nodes() returns nodes connected by rel_type and direction."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_rel(rtype=RelType.CALLS)])

    # Outgoing: foo calls bar
    outgoing = storage.get_related_nodes("function:a.py:foo", RelType.CALLS, "outgoing")
    assert len(outgoing) == 1
    assert outgoing[0].id == "function:b.py:bar"

    # Incoming: bar is called by foo
    incoming = storage.get_related_nodes("function:b.py:bar", RelType.CALLS, "incoming")
    assert len(incoming) == 1
    assert incoming[0].id == "function:a.py:foo"


def test_get_callers_with_confidence(storage):
    """get_callers_with_confidence() returns (node, confidence) tuples."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_rel(properties={"confidence": 0.75})])
    callers = storage.get_callers_with_confidence("function:b.py:bar")
    assert len(callers) == 1
    node, conf = callers[0]
    assert node.id == "function:a.py:foo"
    assert conf == pytest.approx(0.75)


def test_get_callees(storage):
    """get_callees() returns outgoing CALLS targets."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_rel()])
    callees = storage.get_callees("function:a.py:foo")
    assert len(callees) == 1
    assert callees[0].id == "function:b.py:bar"


# ---------------------------------------------------------------------------
# Count / Stats
# ---------------------------------------------------------------------------


def test_node_count(storage):
    """node_count() returns total number of nodes."""
    assert storage.node_count() == 0
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("class:a.py:MyClass", label=NodeLabel.CLASS, name="MyClass", file_path="a.py"),
    ])
    assert storage.node_count() == 2


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search(storage):
    """search() returns nodes matching text in name, signature, or content."""
    storage.add_nodes([
        _node("function:a.py:calculate_sum", name="calculate_sum", file_path="a.py",
              signature="def calculate_sum(x, y)", content="Returns sum of x and y"),
        _node("function:b.py:send_email", name="send_email", file_path="b.py"),
    ])
    storage.rebuild_fts()
    results = storage.search("calculate")
    assert len(results) >= 1
    assert any(n.name == "calculate_sum" for n, _ in results)


def test_search_no_match(storage):
    """search() returns empty list when nothing matches."""
    storage.add_nodes([_node(content="hello world")])
    storage.rebuild_fts()
    results = storage.search("zzzznotfound")
    assert results == []


def test_search_respects_limit(storage):
    """search() limit parameter caps results."""
    nodes = [
        _node(f"function:a.py:func{i}", name=f"func{i}", file_path="a.py",
              content="common keyword stuff")
        for i in range(10)
    ]
    storage.add_nodes(nodes)
    storage.rebuild_fts()
    results = storage.search("common", limit=3)
    assert len(results) == 3


# ---------------------------------------------------------------------------
# File hash tracking
# ---------------------------------------------------------------------------


def test_get_indexed_files(storage):
    """get_indexed_files() returns empty dict when no files indexed."""
    assert storage.get_indexed_files() == {}


def test_update_file_hash(storage):
    """update_file_hash() sets and updates hash for a file."""
    storage.update_file_hash("foo.py", "abc123")
    assert storage.get_indexed_files() == {"foo.py": "abc123"}
    # Upsert
    storage.update_file_hash("foo.py", "def456")
    assert storage.get_indexed_files()["foo.py"] == "def456"


# ---------------------------------------------------------------------------
# Remove by file
# ---------------------------------------------------------------------------


def test_remove_nodes_by_file(storage):
    """remove_nodes_by_file() deletes all nodes for a given file_path."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:a.py:bar", name="bar", file_path="a.py"),
        _node("function:b.py:baz", name="baz", file_path="b.py"),
    ])
    storage.remove_nodes_by_file("a.py")
    assert storage.get_node("function:a.py:foo") is None
    assert storage.get_node("function:a.py:bar") is None
    assert storage.get_node("function:b.py:baz") is not None


def test_remove_nodes_also_removes_relationships(storage):
    """remove_nodes_by_file() also removes relationships involving those nodes."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.add_relationships([_rel(source="function:a.py:foo", target="function:b.py:bar")])
    storage.remove_nodes_by_file("a.py")
    # Relationship should be gone since source node was removed
    assert storage.get_callees("function:a.py:foo") == []
    callers = storage.get_callers_with_confidence("function:b.py:bar")
    assert callers == []


def test_remove_file_hash(storage):
    """remove_file_hash() removes file hash entry."""
    storage.update_file_hash("a.py", "abc")
    storage.remove_file_hash("a.py")
    assert storage.get_indexed_files() == {}


# ---------------------------------------------------------------------------
# Close / shutdown
# ---------------------------------------------------------------------------


def test_close(db_path):
    """close() shuts down cleanly; double-close does not raise."""
    s = GraphStorage(db_path)
    s.initialize()
    s.close()
    # Should not raise on second close
    s.close()


# ---------------------------------------------------------------------------
# FTS rebuild
# ---------------------------------------------------------------------------


def test_rebuild_fts(storage):
    """rebuild_fts() runs without error and updates search index."""
    storage.add_nodes([
        _node("function:a.py:parse", name="parse", file_path="a.py",
              content="Parse a configuration file"),
    ])
    storage.rebuild_fts()
    results = storage.search("configuration")
    assert len(results) >= 1
    assert results[0][0].name == "parse"


# ---------------------------------------------------------------------------
# Dead node marking
# ---------------------------------------------------------------------------


def test_mark_dead_nodes(storage):
    """mark_dead_nodes() sets is_dead=True for specified node IDs."""
    storage.add_nodes([
        _node("function:a.py:foo", name="foo", file_path="a.py"),
        _node("function:b.py:bar", name="bar", file_path="b.py"),
    ])
    storage.mark_dead_nodes(["function:a.py:foo"])
    foo = storage.get_node("function:a.py:foo")
    bar = storage.get_node("function:b.py:bar")
    assert foo is not None and foo.is_dead is True
    assert bar is not None and bar.is_dead is False
