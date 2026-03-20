"""Tests for scripts.memory.bridge — TaskDesc V2 generation and rendering."""

import json
import re
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory.bridge import (
    TASK_DESC_SCHEMA_VERSION,
    _is_already_closed,
    _make_skipped_desc,
    detect_file_conflicts,
    generate_implement_prompt,
    generate_run_id,
    plan_to_task_descriptions,
)


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------


def test_schema_version_is_2():
    assert TASK_DESC_SCHEMA_VERSION == 2


# ---------------------------------------------------------------------------
# generate_run_id
# ---------------------------------------------------------------------------


def test_run_id_format():
    rid = generate_run_id("my-feature")
    assert rid.startswith("my-feature-")
    # Timestamp portion is digits
    ts = rid.split("-", 2)[-1]
    assert ts.isdigit()


# ---------------------------------------------------------------------------
# generate_implement_prompt — pure renderer
# ---------------------------------------------------------------------------


def _make_desc(**overrides):
    """Build a minimal TaskDesc V2 dict with optional overrides."""
    base = {
        "task_id": "",
        "plan_task_index": 0,
        "title": "Test task",
        "action": "Do the thing",
        "file_scope": {"paths": [], "forbidden": []},
        "commands": {"verify": []},
        "completion_footer": "",
        "blockedBy": [],
        "micro_steps": [],
        "tdd": {},
        "skipped": False,
    }
    base.update(overrides)
    return base


class TestGenerateImplementPrompt:
    def test_basic_render(self):
        prompt = generate_implement_prompt(_make_desc())
        assert "# Implement: Test task" in prompt
        assert "Do the thing" in prompt

    def test_files_section(self):
        desc = _make_desc(file_scope={"paths": ["a.py", "b.py"], "forbidden": []})
        prompt = generate_implement_prompt(desc)
        assert "`a.py`" in prompt
        assert "`b.py`" in prompt
        assert "**Files (ONLY touch these):**" in prompt

    def test_forbidden_section(self):
        desc = _make_desc(file_scope={"paths": [], "forbidden": ["core.py"]})
        prompt = generate_implement_prompt(desc)
        assert "**Forbidden (NEVER touch these):**" in prompt
        assert "`core.py`" in prompt

    def test_verify_section(self):
        desc = _make_desc(commands={"verify": ["pytest", "mypy"]})
        prompt = generate_implement_prompt(desc)
        assert "- `pytest`" in prompt
        assert "- `mypy`" in prompt

    def test_micro_steps_section(self):
        desc = _make_desc(micro_steps=["Write failing test", "Implement minimal code"])
        prompt = generate_implement_prompt(desc)
        assert "**Micro-steps (execute in order):**" in prompt
        assert "- Write failing test" in prompt
        assert "- Implement minimal code" in prompt

    def test_tdd_contract_section(self):
        desc = _make_desc(
            tdd={
                "required": True,
                "failingVerify": ["pytest tests/test_x.py -k failing_case"],
                "passingVerify": ["pytest tests/test_x.py -k failing_case"],
            }
        )
        prompt = generate_implement_prompt(desc)
        assert "**TDD contract (must provide evidence):**" in prompt
        assert "- required: `true`" in prompt
        assert "failingVerify" in prompt
        assert "passingVerify" in prompt

    def test_no_memory_section_without_task_id(self):
        prompt = generate_implement_prompt(_make_desc(task_id=""))
        assert "**Memory:**" not in prompt
        assert "Claim:" not in prompt

    def test_memory_commands_derived_from_task_id(self):
        desc = _make_desc(
            task_id="cn-abc123",
            completion_footer="TASK_DONE: [cn-abc123]",
        )
        prompt = generate_implement_prompt(desc)
        assert "**Memory:** `cn-abc123`" in prompt
        assert "claim cn-abc123 --actor implementer" in prompt
        assert "report-done cn-abc123 --actor implementer" in prompt
        assert "show cn-abc123" in prompt
        assert "history cn-abc123" in prompt

    def test_memory_commands_use_custom_actor_name(self):
        desc = _make_desc(
            task_id="cn-abc123",
            completion_footer="TASK_DONE: [cn-abc123]",
        )
        prompt = generate_implement_prompt(desc, actor_name="impl-run-t0-a1")
        assert "claim cn-abc123 --actor impl-run-t0-a1" in prompt
        assert "report-done cn-abc123 --actor impl-run-t0-a1" in prompt

    def test_no_persisted_claim_in_commands(self):
        """Derived commands must NOT come from the commands dict."""
        desc = _make_desc(task_id="cn-abc123", completion_footer="TASK_DONE: [cn-abc123]")
        # commands dict should only have verify
        assert "claim" not in desc["commands"]
        assert "report_done" not in desc["commands"]
        assert "context" not in desc["commands"]
        # But prompt still renders them
        prompt = generate_implement_prompt(desc)
        assert "claim cn-abc123" in prompt

    def test_completion_footer_rendered(self):
        desc = _make_desc(
            task_id="cn-abc123",
            completion_footer="TASK_DONE: [cn-abc123]",
        )
        prompt = generate_implement_prompt(desc)
        assert "`TASK_DONE: [cn-abc123]`" in prompt
        assert "TASK_EVIDENCE:" in prompt

    def test_invalid_task_id_rejected(self):
        desc = _make_desc(task_id="bad-id-format")
        with pytest.raises(ValueError, match="Invalid task_id format"):
            generate_implement_prompt(desc)

    def test_hierarchical_task_id_accepted(self):
        desc = _make_desc(
            task_id="cn-a3f8.1.2",
            completion_footer="TASK_DONE: [cn-a3f8.1.2]",
        )
        prompt = generate_implement_prompt(desc)
        assert "cn-a3f8.1.2" in prompt

    def test_never_close_warning_present(self):
        desc = _make_desc(
            task_id="cn-abc123",
            completion_footer="TASK_DONE: [cn-abc123]",
        )
        prompt = generate_implement_prompt(desc)
        assert "NEVER close issues" in prompt


# ---------------------------------------------------------------------------
# detect_file_conflicts — pure logic
# ---------------------------------------------------------------------------


class TestDetectFileConflicts:
    def test_no_conflicts(self):
        tasks = [
            _make_desc(file_scope={"paths": ["a.py"], "forbidden": []}),
            _make_desc(file_scope={"paths": ["b.py"], "forbidden": []}),
        ]
        assert detect_file_conflicts(tasks) == []

    def test_advisory_overlap(self):
        tasks = [
            _make_desc(file_scope={"paths": ["shared.py"], "forbidden": []}),
            _make_desc(file_scope={"paths": ["shared.py"], "forbidden": []}),
        ]
        conflicts = detect_file_conflicts(tasks)
        assert len(conflicts) == 1
        assert conflicts[0]["file"] == "shared.py"
        assert conflicts[0]["severity"] == "advisory"
        assert conflicts[0]["tasks"] == [0, 1]

    def test_forbidden_overlap(self):
        tasks = [
            _make_desc(file_scope={"paths": ["core.py"], "forbidden": []}),
            _make_desc(file_scope={"paths": [], "forbidden": ["core.py"]}),
        ]
        conflicts = detect_file_conflicts(tasks)
        forbidden_conflicts = [c for c in conflicts if c["severity"] == "forbidden_overlap"]
        assert len(forbidden_conflicts) == 1
        assert forbidden_conflicts[0]["file"] == "core.py"
        assert forbidden_conflicts[0]["tasks"] == [0]
        assert forbidden_conflicts[0]["forbidden_by"] == [1]

    def test_skipped_tasks_ignored(self):
        tasks = [
            _make_desc(file_scope={"paths": ["shared.py"], "forbidden": []}, skipped=True),
            _make_desc(file_scope={"paths": ["shared.py"], "forbidden": []}),
        ]
        assert detect_file_conflicts(tasks) == []

    def test_three_way_overlap(self):
        tasks = [
            _make_desc(file_scope={"paths": ["x.py"], "forbidden": []}),
            _make_desc(file_scope={"paths": ["x.py"], "forbidden": []}),
            _make_desc(file_scope={"paths": ["x.py"], "forbidden": []}),
        ]
        conflicts = detect_file_conflicts(tasks)
        assert len(conflicts) == 1
        assert conflicts[0]["tasks"] == [0, 1, 2]


# ---------------------------------------------------------------------------
# _make_skipped_desc — shape check
# ---------------------------------------------------------------------------


class TestMakeSkippedDesc:
    def test_shape(self):
        task = {"name": "Do X", "files": ["f.py"], "verify": ["check"], "blockedBy": [0]}
        desc = _make_skipped_desc(1, "Do X", "cn-abc", task)
        assert desc["skipped"] is True
        assert desc["task_id"] == "cn-abc"
        assert desc["plan_task_index"] == 1
        assert desc["title"] == "Do X"
        assert desc["action"] == ""
        assert desc["file_scope"]["paths"] == ["f.py"]
        assert desc["commands"]["verify"] == ["check"]
        assert desc["completion_footer"] == ""
        assert desc["blockedBy"] == [0]

    def test_no_derived_commands_on_skipped(self):
        desc = _make_skipped_desc(0, "T", "cn-abc", {})
        assert "claim" not in desc["commands"]
        assert "report_done" not in desc["commands"]


# ---------------------------------------------------------------------------
# plan_to_task_descriptions — needs plan file + mocked DB
# ---------------------------------------------------------------------------


class TestPlanToTaskDescriptions:
    def _write_plan(self, tmp_path, tasks, **extra):
        plan = {
            "schemaVersion": 1,
            "feature": "test-feat",
            "planNumber": "01",
            "tasks": tasks,
            **extra,
        }
        p = tmp_path / "01-PLAN.json"
        p.write_text(json.dumps(plan))
        return p

    def test_basic_task_without_memory(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "Task A", "files": ["a.py"], "verify": ["pytest"], "action": "do A"},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False), \
             mock.patch("scripts.memory.bridge._ensure_memory_issue", return_value=""):
            results = plan_to_task_descriptions(plan_path, tmp_path)

        assert len(results) == 1
        desc = results[0]
        assert desc["title"] == "Task A"
        assert desc["action"] == "do A"
        assert desc["file_scope"]["paths"] == ["a.py"]
        assert desc["commands"]["verify"] == ["pytest"]
        assert desc["task_id"] == ""
        assert desc["skipped"] is False
        # No derived commands persisted
        assert "claim" not in desc["commands"]

    def test_task_with_memory_id(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "Task B", "memoryId": "cn-xyz", "files": ["b.py"], "verify": [], "action": "do B"},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False):
            results = plan_to_task_descriptions(plan_path, tmp_path)

        desc = results[0]
        assert desc["task_id"] == "cn-xyz"
        assert desc["completion_footer"] == "TASK_DONE: [cn-xyz]"
        # Still no derived commands in dict
        assert "claim" not in desc["commands"]

    def test_closed_task_is_skipped(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "Task C", "memoryId": "cn-closed", "files": ["c.py"], "verify": [], "action": "do C"},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=True):
            results = plan_to_task_descriptions(plan_path, tmp_path)

        assert results[0]["skipped"] is True

    def test_blocked_by_validation_out_of_range(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "Task D", "files": ["d.py"], "verify": [], "action": "do D", "blockedBy": [5]},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False), \
             mock.patch("scripts.memory.bridge._ensure_memory_issue", return_value=""):
            with pytest.raises(ValueError, match="invalid blockedBy index 5"):
                plan_to_task_descriptions(plan_path, tmp_path)

    def test_blocked_by_self_reference(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "Task E", "files": ["e.py"], "verify": [], "action": "do E", "blockedBy": [0]},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False), \
             mock.patch("scripts.memory.bridge._ensure_memory_issue", return_value=""):
            with pytest.raises(ValueError, match="self-referencing blockedBy"):
                plan_to_task_descriptions(plan_path, tmp_path)

    def test_multiple_tasks_indexed(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {"name": "T1", "files": ["a.py"], "verify": [], "action": "do T1"},
            {"name": "T2", "files": ["b.py"], "verify": [], "action": "do T2", "blockedBy": [0]},
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False), \
             mock.patch("scripts.memory.bridge._ensure_memory_issue", return_value=""):
            results = plan_to_task_descriptions(plan_path, tmp_path)

        assert len(results) == 2
        assert results[0]["plan_task_index"] == 0
        assert results[1]["plan_task_index"] == 1
        assert results[1]["blockedBy"] == [0]

    def test_microsteps_and_tdd_copied(self, tmp_path):
        plan_path = self._write_plan(tmp_path, [
            {
                "name": "TDD task",
                "files": ["a.py"],
                "verify": ["pytest -q"],
                "action": "do it",
                "microSteps": ["write failing test", "run tests", "implement", "run tests"],
                "tdd": {
                    "required": True,
                    "failingVerify": ["pytest tests/test_a.py -k fail_case"],
                    "passingVerify": ["pytest tests/test_a.py -k fail_case"],
                },
            },
        ])
        with mock.patch("scripts.memory.bridge._is_already_closed", return_value=False), \
             mock.patch("scripts.memory.bridge._ensure_memory_issue", return_value=""):
            results = plan_to_task_descriptions(plan_path, tmp_path)

        desc = results[0]
        assert desc["micro_steps"] == ["write failing test", "run tests", "implement", "run tests"]
        assert desc["tdd"]["required"] is True


@pytest.mark.parametrize(
    ("status", "state"),
    [
        ("open", "done_by_worker"),
        ("open", "verified"),
        ("closed", "closed"),
    ],
)
def test_is_already_closed_treats_completed_states_as_complete(tmp_path, status, state):
    issue = mock.Mock(status=status, state=state)
    with mock.patch("scripts.memory.is_initialized", return_value=True), \
         mock.patch("scripts.memory.show", return_value=issue):
        assert _is_already_closed(tmp_path, "cn-finished") is True
