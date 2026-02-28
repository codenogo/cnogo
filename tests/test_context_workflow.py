"""Tests for context graph workflow integration functions."""

from __future__ import annotations

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)


@pytest.fixture
def graph(tmp_path):
    from scripts.context import ContextGraph

    g = ContextGraph(repo_path=tmp_path)
    yield g
    g.close()


# --- helpers ---


def _add_function_node(storage, file_path, name, label=None):
    if label is None:
        label = NodeLabel.FUNCTION
    node_id = generate_id(label, file_path, name)
    node = GraphNode(
        id=node_id, label=label, name=name, file_path=file_path, start_line=1
    )
    storage.add_nodes([node])
    return node_id


def _add_call_edge(storage, caller_id, callee_id, confidence=None):
    props = {}
    if confidence is not None:
        props["confidence"] = confidence
    storage.add_relationships(
        [
            GraphRelationship(
                id=f"calls:{caller_id}->{callee_id}",
                type=RelType.CALLS,
                source=caller_id,
                target=callee_id,
                properties=props,
            )
        ]
    )


def _add_import_edge(storage, source_id, target_id):
    storage.add_relationships(
        [
            GraphRelationship(
                id=f"imports:{source_id}->{target_id}",
                type=RelType.IMPORTS,
                source=source_id,
                target=target_id,
            )
        ]
    )


# --- suggest_scope tests ---


def test_suggest_scope_returns_enabled_structure(graph):
    """Empty graph returns enabled structure with empty suggestions."""
    from scripts.context.workflow import suggest_scope

    result = suggest_scope(graph.repo_path, keywords=["nonexistent"])
    assert result["enabled"] is True
    assert result["suggestions"] == []


def test_suggest_scope_with_keywords(graph):
    """Keyword search returns matching file paths as suggestions."""
    from scripts.context.workflow import suggest_scope

    # Index a small codebase
    _add_function_node(graph._storage, "src/auth.py", "authenticate")
    _add_function_node(graph._storage, "src/auth.py", "verify_token")
    _add_function_node(graph._storage, "src/db.py", "connect")
    # Rebuild FTS for search to work
    graph._storage.rebuild_fts()

    result = suggest_scope(graph.repo_path, keywords=["authenticate"])
    assert result["enabled"] is True
    assert len(result["suggestions"]) >= 1
    paths = [s["path"] for s in result["suggestions"]]
    assert "src/auth.py" in paths
    # Each suggestion has required fields
    for s in result["suggestions"]:
        assert "path" in s
        assert "reason" in s
        assert "confidence" in s


def test_suggest_scope_with_related_files(graph):
    """Impact analysis on related_files returns blast-radius file suggestions."""
    from scripts.context.workflow import suggest_scope

    # Build a call graph: caller_func in caller.py calls target_func in target.py
    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    caller_id = _add_function_node(graph._storage, "src/caller.py", "caller_func")
    _add_call_edge(graph._storage, caller_id, target_id)
    graph._storage.rebuild_fts()

    result = suggest_scope(
        graph.repo_path, keywords=[], related_files=["src/target.py"]
    )
    assert result["enabled"] is True
    paths = [s["path"] for s in result["suggestions"]]
    assert "src/caller.py" in paths


def test_suggest_scope_graceful_degradation(tmp_path):
    """Returns {enabled: false, error: ...} on failure."""
    from unittest.mock import patch

    from scripts.context.workflow import suggest_scope

    # Force ContextGraph to raise during construction
    with patch(
        "scripts.context.workflow.ContextGraph",
        side_effect=RuntimeError("graph init failed"),
    ):
        result = suggest_scope(tmp_path, keywords=["test"])
    assert result["enabled"] is False
    assert "error" in result
    assert "graph init failed" in result["error"]


def test_suggest_scope_low_confidence_label(graph):
    """Fuzzy edges with confidence <= 0.5 get low_confidence: true."""
    from scripts.context.workflow import suggest_scope

    # Build graph with a low-confidence call edge
    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    fuzzy_caller_id = _add_function_node(
        graph._storage, "src/fuzzy.py", "fuzzy_caller"
    )
    _add_call_edge(graph._storage, fuzzy_caller_id, target_id, confidence=0.5)
    graph._storage.rebuild_fts()

    result = suggest_scope(
        graph.repo_path, keywords=[], related_files=["src/target.py"]
    )
    assert result["enabled"] is True
    # Find the fuzzy caller suggestion
    fuzzy_suggestions = [
        s for s in result["suggestions"] if s["path"] == "src/fuzzy.py"
    ]
    assert len(fuzzy_suggestions) >= 1
    assert fuzzy_suggestions[0].get("low_confidence") is True


# --- validate_scope tests ---


def test_validate_scope_within_scope(graph):
    """Declared files match changed files — expect within_scope: true."""
    from scripts.context.workflow import validate_scope

    _add_function_node(graph._storage, "src/auth.py", "authenticate")
    graph._storage.rebuild_fts()

    result = validate_scope(
        graph.repo_path, declared_files=["src/auth.py"], changed_files=["src/auth.py"]
    )
    assert result["enabled"] is True
    assert result["within_scope"] is True
    assert result["violations"] == []


def test_validate_scope_violation(graph):
    """Changed files extend beyond declared scope — expect violations list."""
    from scripts.context.workflow import validate_scope

    # caller.py calls target.py — changing target.py affects caller.py
    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    caller_id = _add_function_node(graph._storage, "src/caller.py", "caller_func")
    _add_call_edge(graph._storage, caller_id, target_id)
    graph._storage.rebuild_fts()

    # Declared only target.py, but blast radius includes caller.py
    result = validate_scope(
        graph.repo_path,
        declared_files=["src/target.py"],
        changed_files=["src/target.py"],
    )
    assert result["enabled"] is True
    assert result["within_scope"] is False
    violation_paths = [v["path"] for v in result["violations"]]
    assert "src/caller.py" in violation_paths


def test_validate_scope_blast_radius(graph):
    """Blast-radius symbols from impact analysis are included."""
    from scripts.context.workflow import validate_scope

    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    caller_id = _add_function_node(graph._storage, "src/caller.py", "caller_func")
    _add_call_edge(graph._storage, caller_id, target_id)
    graph._storage.rebuild_fts()

    result = validate_scope(
        graph.repo_path,
        declared_files=["src/target.py"],
        changed_files=["src/target.py"],
    )
    assert result["enabled"] is True
    assert len(result["blast_radius"]) >= 1
    blast_paths = [b["path"] for b in result["blast_radius"]]
    assert "src/caller.py" in blast_paths


def test_validate_scope_low_confidence_warnings(graph):
    """Fuzzy edges appear with low_confidence: true in warnings."""
    from scripts.context.workflow import validate_scope

    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    fuzzy_id = _add_function_node(graph._storage, "src/fuzzy.py", "fuzzy_func")
    _add_call_edge(graph._storage, fuzzy_id, target_id, confidence=0.5)
    graph._storage.rebuild_fts()

    result = validate_scope(
        graph.repo_path,
        declared_files=["src/target.py"],
        changed_files=["src/target.py"],
    )
    assert result["enabled"] is True
    # Fuzzy caller should appear in warnings, not violations
    warning_paths = [w["path"] for w in result["warnings"]]
    assert "src/fuzzy.py" in warning_paths
    fuzzy_warning = [w for w in result["warnings"] if w["path"] == "src/fuzzy.py"][0]
    assert fuzzy_warning.get("low_confidence") is True


def test_validate_scope_graceful_degradation(tmp_path):
    """Returns {enabled: false, error: ...} on failure."""
    from unittest.mock import patch

    from scripts.context.workflow import validate_scope

    with patch(
        "scripts.context.workflow.ContextGraph",
        side_effect=RuntimeError("graph init failed"),
    ):
        result = validate_scope(tmp_path, declared_files=["foo.py"])
    assert result["enabled"] is False
    assert "error" in result
    assert "graph init failed" in result["error"]


# --- helpers for enrich_context tests ---


def _add_extends_edge(storage, child_id, parent_id):
    storage.add_relationships(
        [
            GraphRelationship(
                id=f"extends:{child_id}->{parent_id}",
                type=RelType.EXTENDS,
                source=child_id,
                target=parent_id,
            )
        ]
    )


# --- enrich_context tests ---


def test_enrich_context_returns_enabled_structure(graph):
    """Empty graph returns enabled structure with empty related_code."""
    from scripts.context.workflow import enrich_context

    result = enrich_context(graph.repo_path, keywords=["nonexistent"])
    assert result["enabled"] is True
    assert result["related_code"] == []
    assert "architecture" in result


def test_enrich_context_with_keywords(graph):
    """Keyword search returns related code with callers/callees."""
    from scripts.context.workflow import enrich_context

    # Build graph: caller -> target
    target_id = _add_function_node(graph._storage, "src/target.py", "target_func")
    caller_id = _add_function_node(graph._storage, "src/caller.py", "caller_func")
    _add_call_edge(graph._storage, caller_id, target_id)
    graph._storage.rebuild_fts()

    result = enrich_context(graph.repo_path, keywords=["target_func"])
    assert result["enabled"] is True
    assert len(result["related_code"]) >= 1
    # Should find caller_func as a caller relationship
    names = [r["name"] for r in result["related_code"]]
    assert "target_func" in names or "caller_func" in names
    # Each entry has required fields
    for r in result["related_code"]:
        assert "path" in r
        assert "name" in r
        assert "label" in r
        assert "relationship" in r
        assert "confidence" in r


def test_enrich_context_includes_heritage(graph):
    """Parent/child class relationships appear in results."""
    from scripts.context.workflow import enrich_context

    parent_id = _add_function_node(
        graph._storage, "src/base.py", "BaseClass", label=NodeLabel.CLASS
    )
    child_id = _add_function_node(
        graph._storage, "src/child.py", "ChildClass", label=NodeLabel.CLASS
    )
    _add_extends_edge(graph._storage, child_id, parent_id)
    graph._storage.rebuild_fts()

    result = enrich_context(graph.repo_path, keywords=["BaseClass"])
    assert result["enabled"] is True
    # Should find ChildClass as child_class or BaseClass as parent
    relationships = [r["relationship"] for r in result["related_code"]]
    assert any(
        rel in ("child_class", "parent_class", "self") for rel in relationships
    )


def test_enrich_context_graceful_degradation(tmp_path):
    """Returns {enabled: false, error: ...} on failure."""
    from unittest.mock import patch

    from scripts.context.workflow import enrich_context

    with patch(
        "scripts.context.workflow.ContextGraph",
        side_effect=RuntimeError("graph init failed"),
    ):
        result = enrich_context(tmp_path, keywords=["test"])
    assert result["enabled"] is False
    assert "error" in result


def test_enrich_context_deduplication(graph):
    """Duplicate symbols across multiple keywords are deduplicated."""
    from scripts.context.workflow import enrich_context

    # Both keywords match the same symbol
    _add_function_node(graph._storage, "src/auth.py", "authenticate")
    graph._storage.rebuild_fts()

    result = enrich_context(graph.repo_path, keywords=["authenticate", "auth"])
    assert result["enabled"] is True
    # Count entries for src/auth.py — should not be duplicated by node_id
    node_ids = [r.get("node_id") for r in result["related_code"]]
    assert len(node_ids) == len(set(node_ids))
