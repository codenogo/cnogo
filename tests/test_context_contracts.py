"""Tests for contract detection: signature comparison and break detection."""

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
def graph(tmp_path):
    from scripts.context import ContextGraph

    g = ContextGraph(repo_path=tmp_path)
    yield g
    g.close()


# --- helpers ---


def _add_function_node(storage, file_path, name, label=None, signature=""):
    if label is None:
        label = NodeLabel.FUNCTION
    node_id = generate_id(label, file_path, name)
    node = GraphNode(
        id=node_id,
        label=label,
        name=name,
        file_path=file_path,
        start_line=1,
        signature=signature,
    )
    storage.add_nodes([node])
    return node_id


def _add_method_node(storage, file_path, class_name, method_name, signature=""):
    node_id = generate_id(NodeLabel.METHOD, file_path, method_name)
    node = GraphNode(
        id=node_id,
        label=NodeLabel.METHOD,
        name=method_name,
        file_path=file_path,
        start_line=1,
        class_name=class_name,
        signature=signature,
    )
    storage.add_nodes([node])
    return node_id


def _add_call_edge(storage, caller_id, callee_id, confidence=1.0):
    storage.add_relationships(
        [
            GraphRelationship(
                id=f"calls:{caller_id}->{callee_id}",
                type=RelType.CALLS,
                source=caller_id,
                target=callee_id,
                properties={"confidence": confidence},
            )
        ]
    )


# =============================================================================
# TASK 1: extract_current_signatures and compare_signatures
# =============================================================================


class TestExtractCurrentSignatures:
    def test_signature_extract_simple_function(self, tmp_path):
        """extract_current_signatures parses a Python file and returns sigs."""
        from scripts.context.phases.contracts import extract_current_signatures

        py_file = tmp_path / "foo.py"
        py_file.write_text(
            "def hello(name: str) -> str:\n"
            "    return name\n"
        )
        sigs = extract_current_signatures(str(py_file))
        assert "hello" in sigs
        assert "name" in sigs["hello"]

    def test_signature_extract_method(self, tmp_path):
        """Qualified names for methods use 'ClassName.method_name' format."""
        from scripts.context.phases.contracts import extract_current_signatures

        py_file = tmp_path / "foo.py"
        py_file.write_text(
            "class Foo:\n"
            "    def bar(self, x: int) -> None:\n"
            "        pass\n"
        )
        sigs = extract_current_signatures(str(py_file))
        assert "Foo.bar" in sigs

    def test_signature_extract_multiple_symbols(self, tmp_path):
        """Multiple functions in a file are all captured."""
        from scripts.context.phases.contracts import extract_current_signatures

        py_file = tmp_path / "multi.py"
        py_file.write_text(
            "def alpha(a: int) -> int:\n"
            "    return a\n"
            "\n"
            "def beta(b: str, c: float = 1.0) -> None:\n"
            "    pass\n"
        )
        sigs = extract_current_signatures(str(py_file))
        assert "alpha" in sigs
        assert "beta" in sigs

    def test_signature_extract_missing_file(self, tmp_path):
        """Returns empty dict if file does not exist."""
        from scripts.context.phases.contracts import extract_current_signatures

        sigs = extract_current_signatures(str(tmp_path / "nonexistent.py"))
        assert sigs == {}

    def test_signature_extract_syntax_error(self, tmp_path):
        """Returns empty dict if file has syntax errors."""
        from scripts.context.phases.contracts import extract_current_signatures

        py_file = tmp_path / "bad.py"
        py_file.write_text("def (:\n")
        sigs = extract_current_signatures(str(py_file))
        assert sigs == {}


class TestCompareSignatures:
    def _make_node(self, file_path, name, signature, label=NodeLabel.FUNCTION, class_name=""):
        node_id = generate_id(label, file_path, name)
        return GraphNode(
            id=node_id,
            label=label,
            name=name,
            file_path=file_path,
            start_line=1,
            signature=signature,
            class_name=class_name,
        )

    def test_no_changes(self):
        """Returns empty list when signatures match."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "hello", "def hello(name: str) -> str")
        current = {"hello": "def hello(name: str) -> str"}
        changes = compare_signatures([node], current)
        assert changes == []

    def test_param_added(self):
        """Detects param_added when new parameter appears in current signature."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "hello", "def hello(name: str) -> str")
        current = {"hello": "def hello(name: str, age: int) -> str"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["symbol"] == "hello"
        assert changes[0]["change_type"] == "param_added"
        assert "old_signature" in changes[0]
        assert "new_signature" in changes[0]

    def test_param_removed(self):
        """Detects param_removed when a parameter is dropped from signature."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "hello", "def hello(name: str, age: int) -> str")
        current = {"hello": "def hello(name: str) -> str"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "param_removed"

    def test_default_changed(self):
        """Detects default_changed when default value changes."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "greet", "def greet(name: str='Alice') -> str")
        current = {"greet": "def greet(name: str='Bob') -> str"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "default_changed"

    def test_return_type_changed(self):
        """Detects return_type_changed when return annotation changes."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "compute", "def compute(x: int) -> int")
        current = {"compute": "def compute(x: int) -> str"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "return_type_changed"

    def test_signature_changed_catchall(self):
        """Unclassified changes use signature_changed catch-all type."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "func", "def func(x)")
        current = {"func": "def func(*args, **kwargs)"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["change_type"] in (
            "signature_changed", "param_added", "param_removed"
        )

    def test_method_qualified_name_lookup(self):
        """Methods in stored nodes are matched via 'ClassName.method_name' key."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node(
            "foo.py", "bar", "def bar(self, x: int) -> None",
            label=NodeLabel.METHOD, class_name="Foo"
        )
        # current sigs use 'Foo.bar' as key
        current = {"Foo.bar": "def bar(self, x: int, y: int) -> None"}
        changes = compare_signatures([node], current)
        assert len(changes) == 1
        assert changes[0]["symbol"] in ("Foo.bar", "bar")

    def test_symbol_not_in_current(self):
        """Symbols removed from current file are not reported as changes."""
        from scripts.context.phases.contracts import compare_signatures

        node = self._make_node("foo.py", "deleted_func", "def deleted_func()")
        current = {}
        changes = compare_signatures([node], current)
        assert changes == []


# =============================================================================
# TASK 2: ContextGraph.contract_check
# =============================================================================


class TestContractCheck:
    def test_contract_check_no_breaks(self, graph, tmp_path):
        """Returns empty breaks list when signatures haven't changed."""
        from scripts.context.phases.contracts import extract_current_signatures

        py_file = tmp_path / "stable.py"
        py_file.write_text("def stable_func(x: int) -> int:\n    return x\n")

        stored_sig = "def stable_func(x: int) -> int"
        _add_function_node(
            graph._storage, str(py_file), "stable_func",
            signature=stored_sig,
        )

        result = graph.contract_check([str(py_file)])
        assert result["breaks"] == []
        assert result["summary"]["total_breaks"] == 0
        assert result["summary"]["total_affected_callers"] == 0

    def test_contract_check_detects_break(self, graph, tmp_path):
        """Detects signature break and includes callers in result."""
        py_file = tmp_path / "changed.py"
        py_file.write_text("def changed_func(x: int, y: int) -> int:\n    return x + y\n")

        old_sig = "def changed_func(x: int) -> int"
        callee_id = _add_function_node(
            graph._storage, str(py_file), "changed_func",
            signature=old_sig,
        )

        # Add a caller
        caller_id = _add_function_node(
            graph._storage, "src/caller.py", "caller_func",
        )
        _add_call_edge(graph._storage, caller_id, callee_id, confidence=1.0)

        result = graph.contract_check([str(py_file)])
        assert len(result["breaks"]) >= 1
        brk = result["breaks"][0]
        assert brk["symbol"] == "changed_func"
        assert "old_signature" in brk
        assert "new_signature" in brk
        assert "callers" in brk
        assert len(brk["callers"]) >= 1
        caller_entry = brk["callers"][0]
        assert "name" in caller_entry
        assert "file" in caller_entry
        assert "confidence" in caller_entry

    def test_contract_check_summary(self, graph, tmp_path):
        """Summary counts total_breaks and total_affected_callers."""
        py_file = tmp_path / "api.py"
        py_file.write_text(
            "def func_a(x: int, y: int) -> int:\n    return x\n"
            "def func_b(name: str, age: int) -> str:\n    return name\n"
        )

        _add_function_node(
            graph._storage, str(py_file), "func_a",
            signature="def func_a(x: int) -> int",
        )
        _add_function_node(
            graph._storage, str(py_file), "func_b",
            signature="def func_b(name: str) -> str",
        )

        result = graph.contract_check([str(py_file)])
        assert result["summary"]["total_breaks"] == 2

    def test_contract_check_empty_files(self, graph):
        """Returns empty result when no files provided."""
        result = graph.contract_check([])
        assert result["breaks"] == []
        assert result["summary"]["total_breaks"] == 0

    def test_contract_check_nonexistent_file(self, graph):
        """Handles nonexistent file gracefully (no crash, empty breaks)."""
        result = graph.contract_check(["/nonexistent/path.py"])
        assert "breaks" in result
        assert "summary" in result


# =============================================================================
# TASK 3: contract_warnings workflow function and suggest_scope auto_populate
# =============================================================================


class TestContractWarnings:
    def test_contract_warnings_not_indexed(self, tmp_path):
        """Returns enabled:false with error when graph not indexed."""
        from scripts.context.workflow import contract_warnings

        result = contract_warnings(tmp_path, changed_files=[])
        assert result["enabled"] is False
        assert "error" in result

    def test_contract_warnings_no_breaks(self, graph, tmp_path):
        """Returns enabled:true with empty breaks when no contract changes."""
        from scripts.context.workflow import contract_warnings

        py_file = tmp_path / "stable.py"
        py_file.write_text("def stable(x: int) -> int:\n    return x\n")

        _add_function_node(
            graph._storage, str(py_file), "stable",
            signature="def stable(x: int) -> int",
        )

        result = contract_warnings(tmp_path, changed_files=[str(py_file)])
        assert result["enabled"] is True
        assert result["breaks"] == []
        assert result["summary"]["total_breaks"] == 0

    def test_contract_warnings_detects_break(self, graph, tmp_path):
        """Detects and returns break when signature changes."""
        from scripts.context.workflow import contract_warnings

        py_file = tmp_path / "api.py"
        py_file.write_text("def compute(x: int, y: int) -> int:\n    return x + y\n")

        _add_function_node(
            graph._storage, str(py_file), "compute",
            signature="def compute(x: int) -> int",
        )

        result = contract_warnings(tmp_path, changed_files=[str(py_file)])
        assert result["enabled"] is True
        assert len(result["breaks"]) >= 1

    def test_contract_warnings_graceful_degradation(self, tmp_path):
        """Returns enabled:false when ContextGraph raises."""
        from unittest.mock import patch

        from scripts.context.workflow import contract_warnings

        with patch(
            "scripts.context.workflow.ContextGraph",
            side_effect=RuntimeError("graph init failed"),
        ):
            result = contract_warnings(tmp_path, changed_files=["foo.py"])
        assert result["enabled"] is False
        assert "graph init failed" in result["error"]


class TestSuggestScopeAutoPopulate:
    def test_suggest_scope_has_auto_populate(self, graph):
        """suggest_scope result includes auto_populate key."""
        from scripts.context.workflow import suggest_scope

        _add_function_node(graph._storage, "src/auth.py", "authenticate")
        graph._storage.rebuild_fts()

        result = suggest_scope(graph.repo_path, keywords=["authenticate"])
        assert result["enabled"] is True
        assert "auto_populate" in result

    def test_suggest_scope_auto_populate_sorted_by_confidence(self, graph):
        """auto_populate contains files sorted by confidence descending."""
        from scripts.context.workflow import suggest_scope

        _add_function_node(graph._storage, "src/auth.py", "authenticate")
        _add_function_node(graph._storage, "src/db.py", "connect")
        graph._storage.rebuild_fts()

        result = suggest_scope(graph.repo_path, keywords=["authenticate", "connect"])
        assert result["enabled"] is True
        auto_pop = result["auto_populate"]
        # If we have items, they should be sorted by confidence (highest first)
        if len(auto_pop) >= 2:
            confidences = [item["confidence"] for item in auto_pop]
            assert confidences == sorted(confidences, reverse=True)

    def test_suggest_scope_auto_populate_is_list(self, graph):
        """auto_populate is always a list (even if empty)."""
        from scripts.context.workflow import suggest_scope

        result = suggest_scope(graph.repo_path, keywords=["nonexistent"])
        assert result["enabled"] is True
        assert isinstance(result["auto_populate"], list)
