"""Ready-feature dispatch and shape feedback synchronization."""

from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import dispatcher_settings_cfg, load_workflow_config
from scripts.workflow.shared.runtime_root import runtime_path

from .lane import (
    ensure_feature_lane,
    feature_lane_payload,
    heartbeat_feature_lane,
    list_feature_lanes,
    load_feature_lane,
    reclaim_stale_feature_lanes,
)
from .delivery_run import latest_delivery_run, save_delivery_run
from .plan_factory import auto_plan_feature, resolve_feature_plan_policy
from .review import (
    set_review_stage,
    set_review_verdict,
    start_review,
    sync_review_state,
)
from .dispatch_ledger import (
    check_dispatch_hold,
    clear_dispatch_hold_on_success,
    record_dispatch_failure,
)
from .ship import complete_ship, start_ship, sync_ship_state
from .watch_artifacts import load_attention_queue
from .work_order import WorkOrder, sync_all_work_orders, sync_work_order


class _DispatchLock:
    """Advisory flock-based lock for dispatch_ready_work().

    Non-blocking: if the lock is already held, acquire() returns False.
    The OS releases the flock automatically on fd close or process exit.
    """

    def __init__(self, root: Path) -> None:
        self._lock_path = runtime_path(root, "dispatch.lock")
        self._fd: int | None = None

    def acquire(self) -> bool:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_path), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        content = json.dumps(
            {"pid": os.getpid(), "acquiredAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            sort_keys=True,
        )
        os.write(fd, content.encode("utf-8"))
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None

    def holder_info(self) -> dict[str, Any] | None:
        if not self._lock_path.exists():
            return None
        try:
            return json.loads(self._lock_path.read_text(encoding="utf-8").strip())
        except Exception:
            return None


def _is_systemic_error(exc: Exception) -> bool:
    """Classify an exception as systemic (non-retryable) vs transient.

    Systemic: corrupt state, missing schemas, permission denied, bad config.
    Transient: network errors, timeouts, temporary file locks, git conflicts.

    Inspired by Erlang/OTP :permanent vs :transient restart types.
    """
    systemic_types = (
        TypeError,        # wrong function signature, bad schema
        ValueError,       # invalid data, corrupt state
        KeyError,         # missing required field
        AttributeError,   # missing attribute on object
        PermissionError,  # file permission denied
        json.JSONDecodeError,  # corrupt JSON file
    )
    if isinstance(exc, systemic_types):
        return True
    # Check error message for systemic patterns.
    msg = str(exc).lower()
    systemic_patterns = ("schema", "corrupt", "permission denied", "invalid", "missing required")
    return any(pat in msg for pat in systemic_patterns)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _feature_context(root: Path, feature: str) -> dict[str, Any]:
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    payload = _read_json(feature_dir / "CONTEXT.json")
    return payload if isinstance(payload, dict) else {}


def _feature_stub(root: Path, feature: str) -> dict[str, Any]:
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    payload = _read_json(feature_dir / "FEATURE.json")
    return payload if isinstance(payload, dict) else {}


def _priority(root: Path, feature: str) -> int:
    stub = _feature_stub(root, feature)
    priority = stub.get("priority", 2)
    return priority if isinstance(priority, int) and not isinstance(priority, bool) else 2


def _dependencies(root: Path, feature: str) -> list[str]:
    stub = _feature_stub(root, feature)
    deps = stub.get("dependencies", [])
    if not isinstance(deps, list):
        return []
    return [str(dep).strip() for dep in deps if isinstance(dep, str) and str(dep).strip()]


def _sequence_index(root: Path, feature: str) -> int:
    stub = _feature_stub(root, feature)
    parent_shape = stub.get("parentShape")
    if not isinstance(parent_shape, dict):
        return 10_000
    raw_path = parent_shape.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return 10_000
    shape_path = Path(raw_path.strip())
    if not shape_path.is_absolute():
        shape_path = root / shape_path
    shape = _read_json(shape_path)
    if not isinstance(shape, dict):
        return 10_000
    sequence = shape.get("recommendedSequence", [])
    if not isinstance(sequence, list):
        return 10_000
    try:
        return [str(value).strip() for value in sequence].index(feature)
    except ValueError:
        return 10_000


def _dependencies_satisfied(root: Path, feature: str, orders_by_feature: dict[str, WorkOrder]) -> tuple[bool, list[str]]:
    unresolved: list[str] = []
    for dependency in _dependencies(root, feature):
        order = orders_by_feature.get(dependency)
        if order is None or order.status != "completed":
            unresolved.append(dependency)
    return not unresolved, unresolved


def _context_overlap(root: Path, feature: str, other_feature: str) -> bool:
    current = _feature_context(root, feature).get("relatedCode", [])
    other = _feature_context(root, other_feature).get("relatedCode", [])
    if not isinstance(current, list) or not isinstance(other, list):
        return False
    current_set = {str(value).strip() for value in current if isinstance(value, str) and str(value).strip()}
    other_set = {str(value).strip() for value in other if isinstance(value, str) and str(value).strip()}
    return bool(current_set.intersection(other_set))


def _planning_root_for_lane(root: Path, feature: str) -> Path:
    lane = load_feature_lane(root, feature)
    if lane is None:
        return root
    worktree_path = str(getattr(lane, "worktree_path", "")).strip()
    if not worktree_path:
        return root
    candidate = Path(worktree_path)
    return candidate if candidate.exists() else root


def _autoplan_candidates(root: Path, *, feature_filter: str | None = None) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for lane in list_feature_lanes(root, feature_filter=feature_filter):
        if lane.feature in seen:
            continue
        if lane.status not in {"leased", "planning"}:
            continue
        if getattr(lane, "current_run_id", ""):
            continue
        seen.add(lane.feature)
        candidates.append(lane.feature)
    return candidates


def _attempt_auto_plan(
    root: Path,
    *,
    feature: str,
    lease_owner: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    planning_root = _planning_root_for_lane(root, feature)
    lane = load_feature_lane(root, feature)
    lane_id = str(getattr(lane, "lane_id", "") or "")
    try:
        policy = resolve_feature_plan_policy(planning_root, feature=feature)
    except Exception as exc:
        if lane is not None:
            heartbeat_feature_lane(root, feature, status="blocked", lease_owner=lease_owner)
        record_dispatch_failure(root, feature, phase="plan", error=f"{type(exc).__name__}: {exc}", systemic=_is_systemic_error(exc), lane_id=lane_id)
        sync_work_order(root, feature)
        return (
            None,
            None,
            {
                "feature": feature,
                "laneId": lane_id,
                "planningRoot": str(planning_root),
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
    profile = policy.get("profile", {}) if isinstance(policy.get("profile"), dict) else {}
    profile_name = str(profile.get("name", "")).strip()
    if not bool(policy.get("autoPlanAllowed")):
        sync_work_order(root, feature)
        return (
            None,
            {
                "feature": feature,
                "laneId": lane_id,
                "planningRoot": str(planning_root),
                "profile": profile_name,
                "reason": "profile_auto_plan_disabled",
            },
            None,
        )
    try:
        payload = auto_plan_feature(
            planning_root,
            feature=feature,
            start_run=bool(policy.get("autoAdvanceAllowed")),
        )
        clear_dispatch_hold_on_success(root, feature)
        sync_work_order(root, feature)
        lane = load_feature_lane(root, feature)
        if lane is not None:
            payload["lane"] = feature_lane_payload(root, lane)
        payload["laneId"] = lane_id
        payload["planningRoot"] = str(planning_root)
        payload["feature"] = feature
        return payload, None, None
    except Exception as exc:
        if lane is not None:
            heartbeat_feature_lane(root, feature, status="blocked", lease_owner=lease_owner)
        record_dispatch_failure(root, feature, phase="plan", error=f"{type(exc).__name__}: {exc}", systemic=_is_systemic_error(exc), lane_id=lane_id)
        sync_work_order(root, feature)
        return (
            None,
            None,
            {
                "feature": feature,
                "laneId": lane_id,
                "planningRoot": str(planning_root),
                "profile": profile_name,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )


def _autoreview_candidates(root: Path, *, feature_filter: str | None = None) -> list[str]:
    """Find lanes whose latest run is ready for review but has no verdict yet."""
    candidates: list[str] = []
    seen: set[str] = set()
    for lane in list_feature_lanes(root, feature_filter=feature_filter):
        if lane.feature in seen:
            continue
        if lane.status not in {"implementing", "reviewing"}:
            continue
        run = latest_delivery_run(root, lane.feature)
        if run is None:
            continue
        review_readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
        review = run.review if isinstance(getattr(run, "review", None), dict) else {}
        if str(review_readiness.get("status", "")).strip() != "ready":
            continue
        if str(review.get("finalVerdict", "pending")).strip() != "pending":
            continue
        seen.add(lane.feature)
        candidates.append(lane.feature)
    return candidates


def _run_verify_command(command: str, cwd: Path, timeout: int = 120) -> dict[str, Any]:
    """Run a single verification command and capture result."""
    import subprocess as _sp
    try:
        result = _sp.run(
            command, shell=True, cwd=str(cwd),
            capture_output=True, text=True, check=False, timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return {
            "command": command,
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "output": output[:2000],
            "timedOut": False,
        }
    except _sp.TimeoutExpired:
        return {"command": command, "returncode": -1, "passed": False, "output": f"Timed out after {timeout}s", "timedOut": True}
    except Exception as exc:
        return {"command": command, "returncode": -1, "passed": False, "output": str(exc)[:500], "timedOut": False}


def _load_plan_verify_commands(run: Any, wt_root: Path) -> list[str]:
    """Load planVerify[] commands from the delivery run's plan contract."""
    plan_path_str = str(getattr(run, "plan_path", "")).strip()
    if not plan_path_str:
        return []
    plan_path = Path(plan_path_str)
    if not plan_path.is_absolute():
        plan_path = wt_root / plan_path_str
    if not plan_path.exists():
        return []
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        raw = plan.get("planVerify", [])
        return [str(cmd).strip() for cmd in raw if isinstance(cmd, str) and cmd.strip()]
    except Exception:
        return []


def _attempt_auto_review(
    root: Path,
    *,
    feature: str,
    lease_owner: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Auto-review: run planVerify commands, set verdict based on results."""
    from scripts.workflow.shared.profiles import profile_auto_review, resolve_profile  # noqa: lazy

    run = latest_delivery_run(root, feature)
    if run is None:
        return None, None, {"feature": feature, "error": "no delivery run found"}
    run_profile = run.profile if isinstance(getattr(run, "profile", None), dict) else {}
    if not run_profile:
        try:
            run_profile = resolve_profile(root, requested_name=None) or {}
        except Exception:
            run_profile = {}
    if not profile_auto_review(run_profile):
        return (
            None,
            {"feature": feature, "reason": "profile_auto_review_disabled"},
            None,
        )
    try:
        # Resolve feature worktree — verify commands must run there.
        lane = load_feature_lane(root, feature)
        wt_root = root
        if lane is not None and str(getattr(lane, "worktree_path", "")).strip():
            candidate = Path(str(lane.worktree_path).strip())
            if candidate.exists() and candidate.is_dir():
                wt_root = candidate

        # Load verify commands from the plan.
        plan_cmds = _load_plan_verify_commands(run, wt_root)

        # Run commands and collect results.
        spec_results: list[dict[str, Any]] = []
        for cmd in plan_cmds:
            spec_results.append(_run_verify_command(cmd, wt_root))

        # Determine verdict.
        all_passed = all(r["passed"] for r in spec_results) if spec_results else True
        automated_verdict = "pass" if all_passed else "fail"

        # Build evidence.
        spec_evidence = [
            f"{r['command']}: {'PASS' if r['passed'] else 'FAIL'} (rc={r['returncode']})"
            for r in spec_results
        ] if spec_results else ["No planVerify commands found — plan-verify gate was the only check"]

        spec_findings = [
            f"FAIL: {r['command']} (rc={r['returncode']}): {r['output'][:200]}"
            for r in spec_results if not r["passed"]
        ]

        # Start review and set stages.
        start_review(run, automated_verdict=automated_verdict, note="Auto-review by dispatcher")
        set_review_stage(
            run, stage="spec-compliance",
            status="pass" if all_passed else "fail",
            findings=spec_findings,
            evidence=spec_evidence,
            notes=[f"Auto-review ran {len(spec_results)} command(s) from feature worktree"],
        )
        set_review_stage(
            run, stage="code-quality",
            status="pass" if all_passed else "fail",
            findings=[],
            evidence=["Covered by planVerify commands in spec-compliance stage"],
            notes=["Auto-completed by dispatcher"],
        )
        # Set final verdict.
        set_review_verdict(run, verdict=automated_verdict, note=f"Auto-verdict: {len(spec_results)} commands, {sum(1 for r in spec_results if r['passed'])} passed")

        # Advance lane status.
        if lane is not None:
            new_status = "shipping" if all_passed else "blocked"
            heartbeat_feature_lane(root, feature, status=new_status, lease_owner=lease_owner)
        save_delivery_run(run, root)
        if all_passed:
            clear_dispatch_hold_on_success(root, feature)
            # Trigger immediate dispatch for auto-ship on next tick.
            try:
                from .dispatch_trigger import touch_dispatch_trigger
                touch_dispatch_trigger(root, feature, reason="review_passed")
            except Exception:
                pass
        else:
            record_dispatch_failure(root, feature, phase="review", error=f"Auto-review failed: {len(spec_findings)} command(s) failed")
        sync_work_order(root, feature)
        return (
            {
                "feature": feature,
                "automatedVerdict": automated_verdict,
                "finalVerdict": automated_verdict,
                "runId": str(getattr(run, "run_id", "")),
                "commandsRun": len(spec_results),
                "commandsPassed": sum(1 for r in spec_results if r["passed"]),
                "commandsFailed": sum(1 for r in spec_results if not r["passed"]),
            },
            None,
            None,
        )
    except Exception as exc:
        lane = load_feature_lane(root, feature)
        if lane is not None:
            heartbeat_feature_lane(root, feature, status="blocked", lease_owner=lease_owner)
        record_dispatch_failure(root, feature, phase="review", error=f"{type(exc).__name__}: {exc}", systemic=_is_systemic_error(exc))
        sync_work_order(root, feature)
        return (
            None,
            None,
            {"feature": feature, "error": f"{type(exc).__name__}: {exc}"},
        )


def _autoship_candidates(root: Path, *, feature_filter: str | None = None) -> list[str]:
    """Find lanes whose latest run has ship.status in {ready, in_progress}.

    Including in_progress allows retry of failed git push/PR creation on the
    next dispatcher tick, preventing permanent stall.
    """
    candidates: list[str] = []
    seen: set[str] = set()
    for lane in list_feature_lanes(root, feature_filter=feature_filter):
        if lane.feature in seen:
            continue
        if lane.status not in {"reviewing", "shipping"}:
            continue
        run = latest_delivery_run(root, lane.feature)
        if run is None:
            continue
        ship = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
        ship_status = str(ship.get("status", "")).strip()
        if ship_status not in {"ready", "in_progress"}:
            continue
        seen.add(lane.feature)
        candidates.append(lane.feature)
    return candidates


def _attempt_auto_ship(
    root: Path,
    *,
    feature: str,
    lease_owner: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Auto-ship a feature: push feature branch + create PR. Returns (success, skipped, error)."""
    import subprocess as _sp
    from scripts.workflow.shared.profiles import profile_auto_ship, resolve_profile  # noqa: lazy

    run = latest_delivery_run(root, feature)
    if run is None:
        return None, None, {"feature": feature, "error": "no delivery run found"}
    run_profile = run.profile if isinstance(getattr(run, "profile", None), dict) else {}
    if not run_profile:
        try:
            run_profile = resolve_profile(root, requested_name=None) or {}
        except Exception:
            run_profile = {}
    if not profile_auto_ship(run_profile):
        return (
            None,
            {"feature": feature, "reason": "profile_auto_ship_disabled"},
            None,
        )
    try:
        start_ship(run, note="Auto-ship started by dispatcher")
        # Advance lane status.
        lane = load_feature_lane(root, feature)
        if lane is not None:
            heartbeat_feature_lane(root, feature, status="shipping", lease_owner=lease_owner)
        save_delivery_run(run, root)

        # Resolve the feature worktree — git ops must run there, not the control plane.
        # NEVER fall back to root (main checkout) — pushing from main would ship wrong commits.
        wt_root: Path | None = None
        if lane is not None and str(getattr(lane, "worktree_path", "")).strip():
            candidate = Path(str(lane.worktree_path).strip())
            if candidate.exists() and candidate.is_dir():
                wt_root = candidate
        if wt_root is None:
            raise RuntimeError(f"Feature worktree not found for {feature} — cannot push")

        # Build ship draft from the feature worktree where feature/<slug> is HEAD.
        draft: dict[str, Any] | None = None
        try:
            from .ship_draft import build_ship_draft
            draft = build_ship_draft(wt_root, feature)
        except Exception:
            pass

        # Attempt git push + PR creation from the feature worktree.
        # These are best-effort — if there's no remote or gh is unavailable,
        # ship stays in_progress for manual /ship completion.
        # Use lane.branch when available; fall back to convention.
        branch = str(getattr(lane, "branch", "")).strip() or f"feature/{feature}"
        commit = ""
        pr_url = ""
        _SHIP_TIMEOUT = 60  # seconds — prevent hangs on unreachable remotes
        # Check prerequisites before attempting git ops.
        _has_gh = _sp.run(["gh", "--version"], capture_output=True, check=False).returncode == 0 if _sp else False
        try:
            push_result = _sp.run(
                ["git", "push", "-u", "origin", branch],
                cwd=str(wt_root), capture_output=True, text=True, check=False,
                timeout=_SHIP_TIMEOUT,
            )
            if push_result.returncode == 0:
                # Get the commit hash.
                commit_result = _sp.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(wt_root), capture_output=True, text=True, check=False,
                    timeout=10,
                )
                commit = commit_result.stdout.strip() if commit_result.returncode == 0 else ""

                # Create PR via gh (or find existing one).
                if not _has_gh:
                    # gh CLI not available — ship stays in_progress for manual /ship.
                    pass
                else:
                    pr_title = draft.get("prTitle", f"feat({feature}): implement {feature}") if draft else f"feat({feature}): implement {feature}"
                    pr_body = draft.get("prBody", f"## Summary\n- Implement {feature}") if draft else f"## Summary\n- Implement {feature}"
                    pr_result = _sp.run(
                        ["gh", "pr", "create", "--title", pr_title, "--body", pr_body, "--head", branch],
                        cwd=str(wt_root), capture_output=True, text=True, check=False,
                        timeout=_SHIP_TIMEOUT,
                    )
                    if pr_result.returncode == 0:
                        pr_url = pr_result.stdout.strip()
                    else:
                        # PR may already exist — try to get its URL.
                        view_result = _sp.run(
                            ["gh", "pr", "view", branch, "--json", "url", "-q", ".url"],
                            cwd=str(wt_root), capture_output=True, text=True, check=False,
                            timeout=_SHIP_TIMEOUT,
                        )
                        if view_result.returncode == 0 and view_result.stdout.strip():
                            pr_url = view_result.stdout.strip()

                # Record ship completion if we have enough for the profile.
                try:
                    complete_ship(run, commit=commit, branch=branch, pr_url=pr_url, note="Auto-ship completed by dispatcher")
                except ValueError:
                    pass  # Profile may require PR URL; ship stays in_progress for manual completion
        except Exception:
            pass  # git/gh not available — ship stays in_progress

        save_delivery_run(run, root)

        clear_dispatch_hold_on_success(root, feature)
        sync_work_order(root, feature)
        payload: dict[str, Any] = {
            "feature": feature,
            "runId": str(getattr(run, "run_id", "")),
            "shipStatus": "completed" if pr_url else "in_progress",
        }
        if draft is not None:
            payload["draft"] = draft
        if pr_url:
            payload["prUrl"] = pr_url
        if commit:
            payload["commit"] = commit
        return payload, None, None
    except Exception as exc:
        lane = load_feature_lane(root, feature)
        if lane is not None:
            heartbeat_feature_lane(root, feature, status="blocked", lease_owner=lease_owner)
        record_dispatch_failure(root, feature, phase="ship", error=f"{type(exc).__name__}: {exc}", systemic=_is_systemic_error(exc))
        sync_work_order(root, feature)
        return (
            None,
            None,
            {"feature": feature, "error": f"{type(exc).__name__}: {exc}"},
        )


def auto_queue_from_shape(root: Path) -> list[dict[str, Any]]:
    """Scan SHAPE.json files for ready candidates without Work Orders. Auto-create queued orders."""
    ideas_root = root / "docs" / "planning" / "work" / "ideas"
    if not ideas_root.is_dir():
        return []
    queued: list[dict[str, Any]] = []
    for shape_dir in sorted(ideas_root.iterdir()):
        if not shape_dir.is_dir():
            continue
        shape_path = shape_dir / "SHAPE.json"
        shape = _read_json(shape_path)
        if not isinstance(shape, dict):
            continue
        candidates = shape.get("candidateFeatures", [])
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if str(candidate.get("status", "")).strip() != "ready":
                continue
            slug = str(candidate.get("slug", "")).strip()
            if not slug:
                continue
            # Check if feature dossier exists.
            feature_dir = root / "docs" / "planning" / "work" / "features" / slug
            if not (feature_dir / "FEATURE.json").exists():
                continue
            if not (feature_dir / "CONTEXT.json").exists():
                continue
            # Check if Work Order already exists.
            wo_path = runtime_path(root, "work-orders", f"{slug}.json")
            if wo_path.exists():
                continue
            # Create the Work Order by syncing.
            try:
                sync_work_order(root, slug)
                queued.append({"feature": slug, "initiative": str(shape.get("slug", ""))})
            except Exception as exc:
                queued.append({"feature": slug, "error": f"{type(exc).__name__}: {exc}"})
    return queued


def release_completed_lanes(root: Path) -> list[dict[str, Any]]:
    """Release lanes where ship is completed. Clean up worktrees."""
    from .lane import release_feature_lane
    import shutil

    released: list[dict[str, Any]] = []
    for lane in list_feature_lanes(root, include_terminal=True):
        if lane.status == "released":
            continue
        run = latest_delivery_run(root, lane.feature)
        if run is None:
            continue
        ship = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
        if str(ship.get("status", "")).strip() != "completed":
            continue
        try:
            release_feature_lane(root, lane.feature, reason="ship_completed")
            worktree = str(getattr(lane, "worktree_path", "")).strip()
            actually_removed = False
            if worktree:
                wt = Path(worktree)
                if wt.exists() and wt.is_dir() and str(wt) != str(root.resolve()):
                    # Use git worktree remove first (handles lock files and branch cleanup),
                    # then fall back to shutil.rmtree if git worktree remove fails.
                    import subprocess as _sp_rm
                    rm_result = _sp_rm.run(
                        ["git", "worktree", "remove", "--force", str(wt)],
                        cwd=str(root), capture_output=True, text=True, check=False,
                    )
                    if rm_result.returncode != 0 and wt.exists():
                        shutil.rmtree(wt, ignore_errors=True)
                    actually_removed = not wt.exists()
            sync_work_order(root, lane.feature)
            released.append({"feature": lane.feature, "worktreeRemoved": actually_removed})
        except Exception as exc:
            released.append({"feature": lane.feature, "error": f"{type(exc).__name__}: {exc}"})
    # Clean up stale worktree-agent-* branches left by Claude Code isolation worktrees.
    try:
        import subprocess as _sp
        result = _sp.run(
            ["git", "branch", "--list", "worktree-agent-*"],
            cwd=str(root), capture_output=True, text=True, check=False,
        )
        for line in result.stdout.strip().splitlines():
            branch = line.strip().lstrip("* ")
            if branch.startswith("worktree-agent-"):
                _sp.run(
                    ["git", "branch", "-D", branch],
                    cwd=str(root), capture_output=True, text=True, check=False,
                )
    except Exception:
        pass  # Best-effort cleanup
    # Also prune stale worktree references.
    try:
        _sp.run(["git", "worktree", "prune"], cwd=str(root), capture_output=True, check=False)
    except Exception:
        pass
    return released


def dispatch_ready_work(
    root: Path,
    *,
    feature_filter: str | None = None,
    lease_owner: str = "dispatcher",
) -> dict[str, Any]:
    lock = _DispatchLock(root)
    if not lock.acquire():
        return {
            "enabled": True,
            "status": "dispatch_locked",
            "reason": "Another dispatch is in progress.",
            "holder": lock.holder_info() or {},
            "leased": [], "autoPlanned": [], "autoPlanSkipped": [], "planErrors": [],
            "autoReviewed": [], "autoReviewSkipped": [], "reviewErrors": [],
            "autoShipStarted": [], "autoShipSkipped": [], "shipErrors": [],
            "reclaimed": [], "skipped": [], "autoQueued": [], "autoReleased": [],
            "activeLaneCount": 0, "autonomy": "", "defaultWipLimit": 0, "leaseTimeoutMinutes": 0,
        }
    try:
        return _dispatch_ready_work_locked(root, feature_filter=feature_filter, lease_owner=lease_owner)
    finally:
        lock.release()


def _dispatch_ready_work_locked(
    root: Path,
    *,
    feature_filter: str | None = None,
    lease_owner: str = "dispatcher",
) -> dict[str, Any]:
    # Consume pending dispatch triggers (event-driven reactivity).
    try:
        from .dispatch_trigger import consume_dispatch_triggers
        _consumed_triggers = consume_dispatch_triggers(root)
    except Exception:
        _consumed_triggers = []

    # Auto-queue ready features from shape and release completed lanes.
    auto_queued = auto_queue_from_shape(root)
    auto_released = release_completed_lanes(root)

    cfg = load_workflow_config(root)
    settings = dispatcher_settings_cfg(cfg)

    # Check global hold (graceful shutdown in progress).
    try:
        from .application import is_global_hold
        if is_global_hold(root):
            return {
                "enabled": True,
                "status": "global_hold",
                "reason": "Global hold active (graceful shutdown in progress).",
                "autoQueued": auto_queued,
                "autoReleased": auto_released,
                "leased": [], "autoPlanned": [], "autoPlanSkipped": [], "planErrors": [],
                "autoReviewed": [], "autoReviewSkipped": [], "reviewErrors": [],
                "autoShipStarted": [], "autoShipSkipped": [], "shipErrors": [],
                "reclaimed": [], "skipped": [],
                "activeLaneCount": 0, "autonomy": settings["autonomy"],
                "defaultWipLimit": settings["defaultWipLimit"], "leaseTimeoutMinutes": settings["leaseTimeoutMinutes"],
            }
    except Exception:
        pass
    if not settings["enabled"]:
        return {
            "enabled": False,
            "autonomy": settings["autonomy"],
            "defaultWipLimit": settings["defaultWipLimit"],
            "leaseTimeoutMinutes": settings["leaseTimeoutMinutes"],
            "leased": [],
            "autoPlanned": [],
            "autoPlanSkipped": [],
            "planErrors": [],
            "reclaimed": [],
            "skipped": [{"feature": feature_filter, "reason": "dispatcher_disabled"}] if feature_filter else [],
            "autoQueued": auto_queued,
            "autoReleased": auto_released,
            "activeLaneCount": len(list_feature_lanes(root)),
        }
    reclaimed = reclaim_stale_feature_lanes(root, lease_owner=lease_owner)
    for entry in reclaimed:
        feature = str(entry.get("feature", "")).strip()
        if feature:
            sync_work_order(root, feature)
    orders = sync_all_work_orders(root, feature_filter=feature_filter)
    orders_by_feature = {order.feature: order for order in orders}
    active_lanes = list_feature_lanes(root)
    active_features = {lane.feature for lane in active_lanes}
    available_slots = max(int(settings["defaultWipLimit"]) - len(active_lanes), 0)
    queued_orders = [order for order in orders if order.status == "queued"]
    queued_orders.sort(
        key=lambda order: (
            _priority(root, order.feature),
            _sequence_index(root, order.feature),
            order.updated_at,
            order.feature,
        )
    )

    leased_features: list[str] = []
    skipped: list[dict[str, Any]] = []
    for order in queued_orders:
        if available_slots <= 0:
            skipped.append({"feature": order.feature, "reason": "wip_limit_reached"})
            continue
        if order.feature in active_features:
            skipped.append({"feature": order.feature, "reason": "already_active"})
            continue
        # Circuit breaker: skip features held due to repeated dispatch failures.
        hold = check_dispatch_hold(root, order.feature)
        if hold is not None:
            skipped.append({
                "feature": order.feature,
                "reason": "circuit_breaker",
                "holdUntil": hold.get("holdUntil", ""),
                "consecutiveFailures": hold.get("consecutiveFailures", 0),
                "lastError": hold.get("lastError", ""),
            })
            continue
        deps_ok, unresolved = _dependencies_satisfied(root, order.feature, orders_by_feature)
        if not deps_ok:
            skipped.append({"feature": order.feature, "reason": "dependencies_unresolved", "dependencies": unresolved})
            continue
        if settings["overlapPolicy"] == "block":
            overlapping = sorted(
                active_feature for active_feature in active_features if _context_overlap(root, order.feature, active_feature)
            )
            if overlapping:
                skipped.append({"feature": order.feature, "reason": "overlap_blocked", "overlaps": overlapping})
                continue

        lane = ensure_feature_lane(
            root,
            feature=order.feature,
            work_order_id=order.work_order_id or order.feature,
            lease_owner=lease_owner,
            status="leased",
        )
        sync_work_order(root, order.feature)
        active_features.add(order.feature)
        available_slots -= 1
        leased_features.append(lane.feature)

    stage_limits = settings.get("stageMaxPerTick", {})

    auto_planned: list[dict[str, Any]] = []
    auto_plan_skipped: list[dict[str, Any]] = []
    plan_errors: list[dict[str, Any]] = []
    plan_limit = int(stage_limits.get("autoPlan", 2))
    if str(settings.get("autonomy", "")).strip() == "high":
        for feature in _autoplan_candidates(root, feature_filter=feature_filter):
            if len(auto_planned) >= plan_limit:
                auto_plan_skipped.append({"feature": feature, "reason": "stage_limit_reached"})
                continue
            hold = check_dispatch_hold(root, feature)
            if hold is not None:
                auto_plan_skipped.append({"feature": feature, "reason": "circuit_breaker_hold", "holdUntil": hold.get("holdUntil", "")})
                continue
            planned, skipped_plan, error = _attempt_auto_plan(root, feature=feature, lease_owner=lease_owner)
            if planned is not None:
                auto_planned.append(planned)
            if skipped_plan is not None:
                auto_plan_skipped.append(skipped_plan)
            if error is not None:
                plan_errors.append(error)

    # --- Auto-review ---
    auto_reviewed: list[dict[str, Any]] = []
    auto_review_skipped: list[dict[str, Any]] = []
    review_errors: list[dict[str, Any]] = []
    review_limit = int(stage_limits.get("autoReview", 1))
    if str(settings.get("autonomy", "")).strip() == "high":
        for feature in _autoreview_candidates(root, feature_filter=feature_filter):
            if len(auto_reviewed) >= review_limit:
                auto_review_skipped.append({"feature": feature, "reason": "stage_limit_reached"})
                continue
            hold = check_dispatch_hold(root, feature)
            if hold is not None:
                auto_review_skipped.append({"feature": feature, "reason": "circuit_breaker", "holdUntil": hold.get("holdUntil", "")})
                continue
            reviewed, skipped_review, error = _attempt_auto_review(root, feature=feature, lease_owner=lease_owner)
            if reviewed is not None:
                auto_reviewed.append(reviewed)
            if skipped_review is not None:
                auto_review_skipped.append(skipped_review)
            if error is not None:
                review_errors.append(error)

    # --- Auto-ship ---
    auto_ship_started: list[dict[str, Any]] = []
    auto_ship_skipped: list[dict[str, Any]] = []
    ship_errors: list[dict[str, Any]] = []
    ship_limit = int(stage_limits.get("autoShip", 1))
    if str(settings.get("autonomy", "")).strip() == "high":
        for feature in _autoship_candidates(root, feature_filter=feature_filter):
            if len(auto_ship_started) >= ship_limit:
                auto_ship_skipped.append({"feature": feature, "reason": "stage_limit_reached"})
                continue
            hold = check_dispatch_hold(root, feature)
            if hold is not None:
                auto_ship_skipped.append({"feature": feature, "reason": "circuit_breaker", "holdUntil": hold.get("holdUntil", "")})
                continue
            shipped, skipped_ship, error = _attempt_auto_ship(root, feature=feature, lease_owner=lease_owner)
            if shipped is not None:
                auto_ship_started.append(shipped)
            if skipped_ship is not None:
                auto_ship_skipped.append(skipped_ship)
            if error is not None:
                ship_errors.append(error)

    leased: list[dict[str, Any]] = []
    for feature in leased_features:
        lane = load_feature_lane(root, feature)
        if lane is not None:
            leased.append(feature_lane_payload(root, lane))

    return {
        "enabled": settings["enabled"],
        "autonomy": settings["autonomy"],
        "defaultWipLimit": settings["defaultWipLimit"],
        "leaseTimeoutMinutes": settings["leaseTimeoutMinutes"],
        "leased": leased,
        "autoPlanned": auto_planned,
        "autoPlanSkipped": auto_plan_skipped,
        "planErrors": plan_errors,
        "autoReviewed": auto_reviewed,
        "autoReviewSkipped": auto_review_skipped,
        "reviewErrors": review_errors,
        "autoShipStarted": auto_ship_started,
        "autoShipSkipped": auto_ship_skipped,
        "shipErrors": ship_errors,
        "reclaimed": reclaimed,
        "skipped": skipped,
        "autoQueued": auto_queued,
        "autoReleased": auto_released,
        "activeLaneCount": len(list_feature_lanes(root)),
    }


def sync_shape_feedback(
    root: Path,
    *,
    feature_filter: str | None = None,
) -> dict[str, Any]:
    updated_shapes: list[dict[str, Any]] = []
    features_root = root / "docs" / "planning" / "work" / "features"
    if not features_root.is_dir():
        return {"updatedShapes": [], "itemsAdded": 0}

    attention_queue = load_attention_queue(root) or {}
    attention_items = [
        dict(item)
        for item in attention_queue.get("items", [])
        if isinstance(item, dict)
    ] if isinstance(attention_queue, dict) else []
    grouped: dict[Path, list[dict[str, Any]]] = {}
    for feature_dir in sorted(path for path in features_root.iterdir() if path.is_dir()):
        feature = feature_dir.name
        if feature_filter and feature != feature_filter:
            continue
        context = _read_json(feature_dir / "CONTEXT.json")
        if not isinstance(context, dict):
            continue
        parent_shape = context.get("parentShape")
        if not isinstance(parent_shape, dict):
            continue
        raw_path = parent_shape.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        shape_path = Path(raw_path.strip())
        if not shape_path.is_absolute():
            shape_path = root / shape_path
        if not shape_path.exists():
            continue

        items: list[dict[str, Any]] = []
        work_order = _read_json(runtime_path(root, "work-orders", f"{feature}.json")) or {}
        for entry in context.get("shapeFeedback", []) if isinstance(context.get("shapeFeedback"), list) else []:
            if isinstance(entry, dict) and isinstance(entry.get("summary"), str) and entry.get("summary", "").strip():
                item = dict(entry)
                item["sourceFeature"] = feature
                item.setdefault("kind", "shape_feedback")
                items.append(item)
            elif isinstance(entry, str) and entry.strip():
                items.append({"summary": entry.strip(), "sourceFeature": feature, "kind": "shape_feedback"})

        review = _read_json(feature_dir / "REVIEW.json")
        if isinstance(review, dict):
            verdict = str(review.get("verdict", "pending")).strip()
            if verdict in {"warn", "fail"}:
                items.append(
                    {
                        "summary": f"Review verdict for {feature} is {verdict}.",
                        "sourceFeature": feature,
                        "kind": "review_verdict",
                    }
                )

        for attention in attention_items:
            if str(attention.get("feature", "")).strip() != feature:
                continue
            message = str(attention.get("message", "")).strip()
            if not message:
                continue
            items.append(
                {
                    "summary": message,
                    "sourceFeature": feature,
                    "kind": "patrol_attention",
                    "severity": str(attention.get("severity", "warn")).strip() or "warn",
                    "nextAction": str(attention.get("nextAction", "")).strip(),
                }
            )

        ship_summary = work_order.get("shipSummary")
        if isinstance(ship_summary, dict) and str(ship_summary.get("status", "")).strip() == "failed":
            last_error = str(ship_summary.get("lastError", "")).strip()
            summary = f"Ship failed for {feature}."
            if last_error:
                summary = f"{summary} {last_error}"
            items.append(
                {
                    "summary": summary,
                    "sourceFeature": feature,
                    "kind": "ship_failure",
                }
            )

        from scripts.memory import runtime as _mem_rt, storage as _mem_st  # noqa: lazy to break circular import
        if _mem_rt.db_path(root).exists():
            conn = _mem_rt.conn(root)
            try:
                contradictions = _mem_st.list_contradictions(
                    conn,
                    feature_slug=feature,
                    status="open",
                    limit=5,
                )
            finally:
                conn.close()
            for contradiction in contradictions:
                summary = str(contradiction.get("summary", "")).strip()
                if not summary:
                    continue
                items.append(
                    {
                        "summary": summary,
                        "sourceFeature": feature,
                        "kind": "contradiction",
                    }
                )

        if items:
            grouped.setdefault(shape_path, []).extend(items)

    total_added = 0
    for shape_path, items in grouped.items():
        shape = _read_json(shape_path)
        if not isinstance(shape, dict):
            continue
        inbox = shape.get("feedbackInbox")
        if not isinstance(inbox, list):
            inbox = []
        existing_keys = {
            (
                str(entry.get("summary", "")).strip(),
                str(entry.get("sourceFeature", "")).strip(),
                str(entry.get("kind", "")).strip(),
            )
            for entry in inbox
            if isinstance(entry, dict)
        }
        added = 0
        for item in items:
            key = (
                str(item.get("summary", "")).strip(),
                str(item.get("sourceFeature", "")).strip(),
                str(item.get("kind", "")).strip(),
            )
            if key in existing_keys:
                continue
            existing_keys.add(key)
            inbox.append(item)
            added += 1
        if added:
            shape["feedbackInbox"] = inbox
            from scripts.workflow.shared.atomic_write import atomic_write_json as _atomic_write
            _atomic_write(shape_path, shape, sort_keys=False)
            total_added += added
            updated_shapes.append({"shapePath": str(shape_path), "itemsAdded": added})
    return {"updatedShapes": updated_shapes, "itemsAdded": total_added}
