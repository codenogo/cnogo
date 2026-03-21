"""Tests for query, phase, and dependency helpers in scripts.memory."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory import (  # noqa: E402
    blockers,
    blocks,
    create,
    dep_add,
    dep_remove,
    get_cost_summary,
    get_phase,
    init,
    record_cost_event,
    ready,
    set_phase,
    show,
    update,
)


def test_phase_roundtrip_uses_public_wrappers(tmp_path):
    root = tmp_path
    init(root)
    create("phase task", issue_type="task", feature_slug="feat-x", root=root)

    assert get_phase("feat-x", root=root) == "discuss"
    assert set_phase("feat-x", "plan", root=root) == 1
    assert get_phase("feat-x", root=root) == "plan"


def test_dependency_wrappers_update_ready_and_relationships(tmp_path):
    root = tmp_path
    init(root)
    blocker = create("blocker", issue_type="task", root=root)
    blocked = create("blocked", issue_type="task", root=root)

    dep_add(blocked.id, blocker.id, root=root)

    ready_ids = [issue.id for issue in ready(root=root, limit=10)]
    assert blocker.id in ready_ids
    assert blocked.id not in ready_ids
    assert [issue.id for issue in blockers(blocked.id, root=root)] == [blocker.id]
    assert [issue.id for issue in blocks(blocker.id, root=root)] == [blocked.id]

    dep_remove(blocked.id, blocker.id, root=root)

    ready_ids_after = [issue.id for issue in ready(root=root, limit=10)]
    assert blocker.id in ready_ids_after
    assert blocked.id in ready_ids_after


def test_dependency_wrappers_reject_cycles(tmp_path):
    root = tmp_path
    init(root)
    issue_a = create("a", issue_type="task", root=root)
    issue_b = create("b", issue_type="task", root=root)

    dep_add(issue_a.id, issue_b.id, root=root)

    with pytest.raises(ValueError, match="would create a cycle"):
        dep_add(issue_b.id, issue_a.id, root=root)


def test_show_and_update_wrappers_roundtrip_issue_state(tmp_path):
    root = tmp_path
    init(root)
    issue = create("needs update", issue_type="task", root=root)

    updated = update(
        issue.id,
        title="updated title",
        metadata={"scope": "narrow"},
        comment="refined during refactor",
        root=root,
    )

    assert updated.title == "updated title"
    assert updated.metadata["scope"] == "narrow"

    shown = show(issue.id, root=root)
    assert shown is not None
    assert shown.title == "updated title"
    assert any(event.event_type == "updated" for event in shown.recent_events)


def test_create_wrapper_supports_parent_child_issue_creation(tmp_path):
    root = tmp_path
    init(root)
    parent = create("parent epic", issue_type="epic", root=root)
    child = create("child task", issue_type="task", parent=parent.id, labels=["scoped"], root=root)

    assert child.id.startswith(f"{parent.id}.")
    shown = show(child.id, root=root)
    assert shown is not None
    assert shown.labels == ["scoped"]
    assert any(dep.depends_on_id == parent.id for dep in shown.deps)


def test_cost_tracking_wrappers_roundtrip_feature_aggregation(tmp_path):
    root = tmp_path
    init(root)
    issue = create("costed task", issue_type="task", feature_slug="feat-x", root=root)

    record_cost_event(
        issue.id,
        input_tokens=120,
        output_tokens=30,
        cost_usd=1.5,
        root=root,
    )

    summary = get_cost_summary("feat-x", root=root)
    assert summary["feature_slug"] == "feat-x"
    assert summary["total_tokens"] == 150
    assert summary["total_cost_usd"] == 1.5
    assert summary["event_count"] == 1
