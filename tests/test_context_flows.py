"""Tests for execution flow tracing phase."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        s = GraphStorage(Path(tmp) / "test.db")
        s.initialize()
        yield s
        s.close()


def _add_function(storage, name, file_path="a.py", is_entry_point=False):
    nid = f"function:{file_path}:{name}"
    storage.add_nodes([GraphNode(
        id=nid, label=NodeLabel.FUNCTION, name=name, file_path=file_path,
        is_entry_point=is_entry_point,
    )])
    return nid


def _add_class(storage, name, file_path="a.py"):
    nid = f"class:{file_path}:{name}"
    storage.add_nodes([GraphNode(
        id=nid, label=NodeLabel.CLASS, name=name, file_path=file_path,
    )])
    return nid


def _add_method(storage, name, file_path="a.py", class_name=""):
    nid = f"method:{file_path}:{name}"
    storage.add_nodes([GraphNode(
        id=nid, label=NodeLabel.METHOD, name=name, file_path=file_path,
        class_name=class_name,
    )])
    return nid


def _add_call_edge(storage, source_id, target_id):
    rid = f"calls:{source_id}->{target_id}"
    storage.add_relationships([GraphRelationship(
        id=rid, type=RelType.CALLS, source=source_id, target=target_id,
    )])


# --- FlowStep / FlowResult dataclass ---


def test_flow_step_fields():
    from scripts.context.phases.flows import FlowStep
    node = GraphNode(id="function:a.py:foo", label=NodeLabel.FUNCTION, name="foo")
    step = FlowStep(node=node, depth=1)
    assert step.node.name == "foo"
    assert step.depth == 1


def test_flow_result_fields():
    from scripts.context.phases.flows import FlowResult
    entry = GraphNode(id="function:a.py:main", label=NodeLabel.FUNCTION, name="main")
    result = FlowResult(process_id="process:a.py:main", entry_point=entry, steps=[])
    assert result.process_id == "process:a.py:main"
    assert result.entry_point.name == "main"
    assert result.steps == []


# --- trace_flows ---


def test_empty_graph_returns_empty(storage):
    """Empty graph should produce no flows."""
    from scripts.context.phases.flows import trace_flows
    result = trace_flows(storage)
    assert result == []


def test_single_entry_point_traces_forward_calls(storage):
    """main() calling helper() should produce one flow with one step."""
    from scripts.context.phases.flows import trace_flows

    main_id = _add_function(storage, "main", "app.py")
    helper_id = _add_function(storage, "helper", "app.py")
    _add_call_edge(storage, main_id, helper_id)

    flows = trace_flows(storage)
    assert len(flows) == 1
    assert flows[0].entry_point.name == "main"
    assert len(flows[0].steps) >= 1
    step_names = [s.node.name for s in flows[0].steps]
    assert "helper" in step_names


def test_multi_hop_bfs_respects_max_depth(storage):
    """BFS should stop at max_depth."""
    from scripts.context.phases.flows import trace_flows

    main_id = _add_function(storage, "main", "app.py")
    a_id = _add_function(storage, "func_a", "app.py")
    b_id = _add_function(storage, "func_b", "app.py")
    c_id = _add_function(storage, "func_c", "app.py")
    _add_call_edge(storage, main_id, a_id)
    _add_call_edge(storage, a_id, b_id)
    _add_call_edge(storage, b_id, c_id)

    flows = trace_flows(storage, max_depth=2)
    assert len(flows) == 1
    # depth 1: func_a, depth 2: func_b — func_c should be excluded
    step_names = [s.node.name for s in flows[0].steps]
    assert "func_a" in step_names
    assert "func_b" in step_names
    assert "func_c" not in step_names


def test_multiple_entry_points_produce_distinct_flows(storage):
    """Two entry points should produce two separate flows."""
    from scripts.context.phases.flows import trace_flows

    main_id = _add_function(storage, "main", "app.py")
    test_id = _add_function(storage, "test_foo", "test_app.py")
    helper_id = _add_function(storage, "helper", "lib.py")

    _add_call_edge(storage, main_id, helper_id)
    _add_call_edge(storage, test_id, helper_id)

    flows = trace_flows(storage)
    assert len(flows) == 2
    entry_names = sorted(f.entry_point.name for f in flows)
    assert entry_names == ["main", "test_foo"]


def test_step_in_process_edges_persisted(storage):
    """trace_flows should persist Process nodes and STEP_IN_PROCESS edges."""
    from scripts.context.phases.flows import trace_flows

    main_id = _add_function(storage, "main", "app.py")
    helper_id = _add_function(storage, "helper", "app.py")
    _add_call_edge(storage, main_id, helper_id)

    trace_flows(storage)

    # Check Process node was persisted
    process_node = storage.get_node(f"process:app.py:main")
    assert process_node is not None
    assert process_node.label == NodeLabel.PROCESS

    # Check STEP_IN_PROCESS edges
    step_edges = storage.get_all_relationships_by_types([RelType.STEP_IN_PROCESS.value])
    assert len(step_edges) >= 1
    targets = [t for _, t, _ in step_edges]
    assert helper_id in targets


def test_cycles_do_not_cause_infinite_loop(storage):
    """Cyclic call graph should terminate without infinite loop."""
    from scripts.context.phases.flows import trace_flows

    main_id = _add_function(storage, "main", "app.py")
    a_id = _add_function(storage, "func_a", "app.py")
    b_id = _add_function(storage, "func_b", "app.py")
    _add_call_edge(storage, main_id, a_id)
    _add_call_edge(storage, a_id, b_id)
    _add_call_edge(storage, b_id, a_id)  # cycle: a -> b -> a

    flows = trace_flows(storage, max_depth=10)
    assert len(flows) == 1
    # Should terminate — just check it doesn't hang
    assert len(flows[0].steps) == 2  # func_a and func_b (each visited once)


def test_entry_point_flag_detected(storage):
    """Nodes with is_entry_point=True should be treated as entry points."""
    from scripts.context.phases.flows import trace_flows

    ep_id = _add_function(storage, "custom_entry", "run.py", is_entry_point=True)
    helper_id = _add_function(storage, "helper", "run.py")
    _add_call_edge(storage, ep_id, helper_id)

    flows = trace_flows(storage)
    assert len(flows) == 1
    assert flows[0].entry_point.name == "custom_entry"


def test_init_py_symbols_as_entry_points(storage):
    """Symbols in __init__.py should be treated as entry points."""
    from scripts.context.phases.flows import trace_flows

    init_id = _add_function(storage, "setup", "__init__.py")
    helper_id = _add_function(storage, "helper", "lib.py")
    _add_call_edge(storage, init_id, helper_id)

    flows = trace_flows(storage)
    assert len(flows) == 1
    assert flows[0].entry_point.name == "setup"


def test_test_class_as_entry_point(storage):
    """Test classes (Test* prefix) should be treated as entry points."""
    from scripts.context.phases.flows import trace_flows

    cls_id = _add_class(storage, "TestFoo", "test_foo.py")
    helper_id = _add_function(storage, "helper", "lib.py")
    _add_call_edge(storage, cls_id, helper_id)

    flows = trace_flows(storage)
    entry_names = [f.entry_point.name for f in flows]
    assert "TestFoo" in entry_names
