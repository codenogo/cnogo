"""Lifecycle transition helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage as _st
from .graph import rebuild_blocked_cache as _rebuild_blocked_cache
from .issues import show_issue as _show_issue
from .models import ACTOR_ROLES
from .policy import completion_evidence_findings as _completion_evidence_findings
from .policy import load_agent_team_settings as _load_agent_team_settings
from .policy import load_enforcement_levels as _load_enforcement_levels
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .runtime import emit as _emit
from .storage import with_retry as _with_retry


def validate_transition(issue: Any, from_state: str, to_state: str, actor_role: str) -> None:
    valid = issue.valid_states()
    if to_state not in valid:
        raise ValueError(f"Invalid target state {to_state!r} for {issue.issue_type}. Valid: {valid}")
    if from_state != issue.state:
        raise ValueError(f"State mismatch: expected {from_state!r}, got {issue.state!r}")
    if actor_role not in ACTOR_ROLES:
        raise ValueError(f"Invalid actor_role {actor_role!r}. Valid: {sorted(ACTOR_ROLES)}")


def report_done_issue(
    root: Path,
    issue_id: str,
    *,
    outputs: dict | None = None,
    actor: str,
    actor_role: str = "worker",
) -> Any:
    if actor_role not in ("worker", "hook"):
        raise ValueError(f"Only worker or hook can report_done, got {actor_role!r}")

    enforcement = _load_enforcement_levels(root)
    ownership_level = enforcement.get("taskOwnership", "error")

    def _do_report() -> Any:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if existing.issue_type != "task":
                raise ValueError(f"report_done only works on tasks, got {existing.issue_type!r}")

            policy_warnings: list[str] = []
            if not existing.assignee:
                message = "Cannot report_done without an assignee (unclaimed task)."
                if ownership_level == "error":
                    raise ValueError(message)
                if ownership_level == "warn":
                    policy_warnings.append(message)
            elif existing.assignee != actor:
                message = (
                    "report_done actor must match assignee under taskOwnership policy "
                    f"(assignee={existing.assignee!r}, actor={actor!r})."
                )
                if ownership_level == "error":
                    raise ValueError(message)
                if ownership_level == "warn":
                    policy_warnings.append(message)
            if existing.state not in {"in_progress", "done_by_worker"}:
                raise ValueError(
                    "report_done requires task state in_progress|done_by_worker, "
                    f"got {existing.state!r}"
                )
            if actor_role == "hook" and (not existing.owner_actor or existing.owner_actor != actor):
                raise ValueError("Hook can only report_done for owned tasks")

            validate_transition(existing, existing.state, "done_by_worker", actor_role)
            _st.update_issue_fields(conn, issue_id, state="done_by_worker")

            if outputs:
                merged_meta = {**existing.metadata, "outputs": outputs}
                _st.update_issue_fields(conn, issue_id, metadata=merged_meta)

            _emit(
                conn,
                issue_id,
                "report_done",
                actor,
                {
                    "actor_role": actor_role,
                    "outputs": outputs or {},
                    "policy_warnings": policy_warnings,
                },
            )
            conn.commit()
            return _st.get_issue(conn, issue_id)
        finally:
            conn.close()

    result = _with_retry(_do_report)
    _auto_export(root)
    return result


def verify_and_close_issue(
    root: Path,
    issue_id: str,
    *,
    reason: str = "completed",
    comment: str | None = None,
    actor: str = "claude",
) -> Any:
    enforcement = _load_enforcement_levels(root)
    verification_level = enforcement.get("verificationBeforeCompletion", "error")
    tdd_level = enforcement.get("tddMode", "error")

    def _do_verify() -> Any:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if existing.issue_type != "task":
                raise ValueError(f"verify_and_close only works on tasks, got {existing.issue_type!r}")

            evidence_findings = _completion_evidence_findings(
                existing,
                verification_level=verification_level,
                tdd_level=tdd_level,
            )
            blocking = [msg for level, msg in evidence_findings if level == "error"]
            if blocking:
                raise ValueError("Completion evidence policy violation: " + "; ".join(blocking))

            if existing.state == "done_by_worker":
                _st.update_issue_fields(conn, issue_id, state="verified")
                _emit(conn, issue_id, "verified", actor)
                _st.update_issue_fields(conn, issue_id, state="closed")
                _st.close_issue(conn, issue_id, reason)
                _emit(conn, issue_id, "closed", actor, {"reason": reason, "comment": comment or ""})
            elif existing.state == "verified":
                _st.update_issue_fields(conn, issue_id, state="closed")
                _st.close_issue(conn, issue_id, reason)
                _emit(conn, issue_id, "closed", actor, {"reason": reason, "comment": comment or ""})
            else:
                raise ValueError(f"Cannot verify task in state {existing.state!r}")

            _rebuild_blocked_cache(conn)
            conn.commit()
            return _st.get_issue(conn, issue_id)
        finally:
            conn.close()

    result = _with_retry(_do_verify)
    _auto_export(root)
    return result


def close_issue(
    root: Path,
    issue_id: str,
    *,
    reason: str = "completed",
    comment: str | None = None,
    actor: str = "claude",
    actor_role: str = "leader",
) -> Any:
    existing_issue = _show_issue(root, issue_id)
    if existing_issue and actor_role == "leader" and existing_issue.issue_type == "task":
        return verify_and_close_issue(root, issue_id, reason=reason, comment=comment, actor=actor)

    def _do_close() -> Any:
        conn = _conn(root)
        try:
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if actor_role != "leader" and existing.issue_type in ("plan", "epic"):
                raise ValueError(f"Only leader can close {existing.issue_type} issues")
            if actor_role != "leader" and existing.issue_type == "task":
                raise ValueError("Use report_done() for worker task completion")

            ok = _st.close_issue(conn, issue_id, reason)
            if not ok:
                raise ValueError(f"Issue {issue_id} is already closed")

            _st.update_issue_fields(conn, issue_id, state="closed")
            _emit(conn, issue_id, "closed", actor, {"reason": reason, "comment": comment or ""})
            _rebuild_blocked_cache(conn)
            conn.commit()
            return _st.get_issue(conn, issue_id)
        finally:
            conn.close()

    result = _with_retry(_do_close)
    _auto_export(root)
    return result


def reopen_issue(root: Path, issue_id: str, *, actor: str = "claude") -> Any:
    conn = _conn(root)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")

        ok = _st.reopen_issue(conn, issue_id)
        if not ok:
            raise ValueError(f"Issue {issue_id} is not closed")

        _emit(conn, issue_id, "reopened", actor)
        _rebuild_blocked_cache(conn)
        conn.commit()
        result = _st.get_issue(conn, issue_id)
    finally:
        conn.close()
    _auto_export(root)
    return result


def release_issue(
    root: Path,
    issue_id: str,
    *,
    actor: str = "claude",
    actor_role: str = "leader",
) -> Any:
    if actor_role != "leader":
        raise ValueError("Only leader can release in-progress issues")

    conn = _conn(root)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")
        if existing.issue_type != "task":
            raise ValueError(f"release only works on tasks, got {existing.issue_type!r}")
        if existing.state != "in_progress":
            raise ValueError(
                "release requires task in active execution state "
                f"(state='in_progress'), got state={existing.state!r}"
            )

        ok = _st.release_issue(conn, issue_id)
        if not ok:
            raise ValueError(f"Issue {issue_id} is not in_progress (status={existing.status!r})")

        _emit(conn, issue_id, "released", actor, {"previous_assignee": existing.assignee})
        _rebuild_blocked_cache(conn)
        conn.commit()
        result = _st.get_issue(conn, issue_id)
    finally:
        conn.close()
    _auto_export(root)
    return result


def takeover_issue(
    root: Path,
    issue_id: str,
    *,
    to_actor: str,
    reason: str,
    actor: str = "leader",
    actor_role: str = "leader",
) -> dict[str, Any]:
    if actor_role != "leader":
        raise ValueError("Only leader can run takeover_task")
    to_actor_clean = (to_actor or "").strip()
    if not to_actor_clean:
        raise ValueError("takeover target actor cannot be empty")
    reason_clean = (reason or "").strip()
    if not reason_clean:
        raise ValueError("takeover reason cannot be empty")

    max_takeovers = _load_agent_team_settings(root).get("maxTakeoversPerTask", 2)

    def _do_takeover() -> dict[str, Any]:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if existing.issue_type != "task":
                raise ValueError(f"takeover_task only works on tasks, got {existing.issue_type!r}")
            if existing.status == "closed" or existing.state == "closed":
                raise ValueError(f"Issue {issue_id} is closed")
            if existing.status != "in_progress" or existing.state != "in_progress":
                raise ValueError(
                    "takeover_task requires task in active execution state "
                    f"(status='in_progress', state='in_progress'), got "
                    f"(status={existing.status!r}, state={existing.state!r})"
                )

            row = conn.execute(
                "SELECT COUNT(1) AS c FROM events WHERE issue_id = ? AND event_type = 'taken_over'",
                (issue_id,),
            ).fetchone()
            attempts_so_far = int(row["c"] or 0) if row else 0
            if attempts_so_far >= max_takeovers:
                raise ValueError(f"Takeover limit reached for {issue_id}: {attempts_so_far}/{max_takeovers}")

            from_actor = existing.assignee or ""
            if from_actor == to_actor_clean and existing.state == "in_progress":
                return {
                    "id": issue_id,
                    "from_actor": from_actor,
                    "to_actor": to_actor_clean,
                    "attempt": attempts_so_far,
                    "max_attempts": max_takeovers,
                    "state": existing.state,
                    "status": existing.status,
                    "idempotent": True,
                }

            _st.update_issue_fields(
                conn,
                issue_id,
                assignee=to_actor_clean,
                status="in_progress",
                state="in_progress",
            )
            attempt = attempts_so_far + 1
            _emit(
                conn,
                issue_id,
                "taken_over",
                actor,
                {
                    "from_actor": from_actor,
                    "to_actor": to_actor_clean,
                    "reason": reason_clean,
                    "attempt": attempt,
                    "max_attempts": max_takeovers,
                },
            )
            _rebuild_blocked_cache(conn)
            conn.commit()

            fresh = _st.get_issue(conn, issue_id)
            return {
                "id": issue_id,
                "from_actor": from_actor,
                "to_actor": to_actor_clean,
                "attempt": attempt,
                "max_attempts": max_takeovers,
                "state": fresh.state if fresh else "in_progress",
                "status": fresh.status if fresh else "in_progress",
                "idempotent": False,
            }
        finally:
            conn.close()

    result = _with_retry(_do_takeover)
    _auto_export(root)
    return result
