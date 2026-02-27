"""Tests for context graph data model."""

from __future__ import annotations

import pytest


def test_node_label_has_10_values():
    from scripts.context.model import NodeLabel
    expected = {
        "file", "folder", "function", "class", "method",
        "interface", "type_alias", "enum", "community", "process",
    }
    actual = {nl.value for nl in NodeLabel}
    assert actual == expected


def test_rel_type_has_11_values():
    from scripts.context.model import RelType
    expected = {
        "contains", "defines", "calls", "imports", "extends",
        "implements", "uses_type", "exports", "member_of",
        "step_in_process", "coupled_with",
    }
    actual = {rt.value for rt in RelType}
    assert actual == expected


def test_generate_id_format():
    from scripts.context.model import NodeLabel, generate_id
    nid = generate_id(NodeLabel.FUNCTION, "scripts/memory/__init__.py", "create")
    assert nid == "function:scripts/memory/__init__.py:create"


def test_generate_id_no_name():
    from scripts.context.model import NodeLabel, generate_id
    nid = generate_id(NodeLabel.FILE, "scripts/memory/__init__.py", "")
    assert nid == "file:scripts/memory/__init__.py:"


def test_graph_node_creation():
    from scripts.context.model import GraphNode, NodeLabel
    node = GraphNode(
        id="function:foo.py:bar",
        label=NodeLabel.FUNCTION,
        name="bar",
        file_path="foo.py",
        start_line=10,
        end_line=20,
    )
    assert node.id == "function:foo.py:bar"
    assert node.label == NodeLabel.FUNCTION
    assert node.name == "bar"
    assert node.file_path == "foo.py"
    assert node.start_line == 10
    assert node.end_line == 20
    assert node.content == ""
    assert node.signature == ""
    assert node.language == ""
    assert node.class_name == ""
    assert node.is_dead is False
    assert node.is_entry_point is False
    assert node.is_exported is False
    assert node.properties == {}


def test_graph_node_with_properties():
    from scripts.context.model import GraphNode, NodeLabel
    node = GraphNode(
        id="method:foo.py:Cls.run",
        label=NodeLabel.METHOD,
        name="run",
        file_path="foo.py",
        class_name="Cls",
        properties={"decorators": ["staticmethod"]},
    )
    assert node.class_name == "Cls"
    assert node.properties["decorators"] == ["staticmethod"]


def test_graph_relationship_creation():
    from scripts.context.model import GraphRelationship, RelType
    rel = GraphRelationship(
        id="calls:function:a.py:foo->function:b.py:bar",
        type=RelType.CALLS,
        source="function:a.py:foo",
        target="function:b.py:bar",
    )
    assert rel.type == RelType.CALLS
    assert rel.source == "function:a.py:foo"
    assert rel.target == "function:b.py:bar"
    assert rel.properties == {}


def test_graph_relationship_with_confidence():
    from scripts.context.model import GraphRelationship, RelType
    rel = GraphRelationship(
        id="calls:a->b",
        type=RelType.CALLS,
        source="function:a.py:foo",
        target="function:b.py:bar",
        properties={"confidence": 0.8},
    )
    assert rel.properties["confidence"] == 0.8


def test_graph_node_to_dict():
    from scripts.context.model import GraphNode, NodeLabel
    node = GraphNode(
        id="function:foo.py:bar",
        label=NodeLabel.FUNCTION,
        name="bar",
        file_path="foo.py",
    )
    d = node.to_dict()
    assert d["id"] == "function:foo.py:bar"
    assert d["label"] == "function"
    assert d["name"] == "bar"


def test_graph_relationship_to_dict():
    from scripts.context.model import GraphRelationship, RelType
    rel = GraphRelationship(
        id="calls:a->b",
        type=RelType.CALLS,
        source="a",
        target="b",
        properties={"confidence": 1.0},
    )
    d = rel.to_dict()
    assert d["type"] == "calls"
    assert d["properties"]["confidence"] == 1.0
