"""Doctor command helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def cmd_doctor(
    root: Path,
    *,
    run_shell: Any,
    subprocess_module: Any,
    sys_executable: str,
    json_output: bool = False,
) -> int:
    import sqlite3

    checks = []

    try:
        result = subprocess_module.run(
            [sys_executable, ".cnogo/scripts/workflow_validate.py", "--json"],
            capture_output=True, text=True, timeout=30, cwd=str(root),
        )
        if result.returncode == 0:
            checks.append({"name": "workflow_validation", "status": "pass", "details": "WORKFLOW.json and contracts valid"})
        else:
            details = result.stdout.strip()[:200] or result.stderr.strip()[:200] or "Validation failed"
            checks.append({"name": "workflow_validation", "status": "fail", "details": details})
    except Exception as exc:
        checks.append({"name": "workflow_validation", "status": "fail", "details": str(exc)[:200]})

    db_path = root / ".cnogo" / "memory.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if result and result[0] == "ok":
                checks.append({"name": "memory_db_integrity", "status": "pass", "details": "PRAGMA integrity_check: ok"})
            else:
                checks.append({"name": "memory_db_integrity", "status": "fail", "details": f"integrity_check: {result[0] if result else 'no result'}"})
        except Exception as exc:
            checks.append({"name": "memory_db_integrity", "status": "fail", "details": str(exc)[:200]})
    else:
        checks.append({"name": "memory_db_integrity", "status": "warn", "details": "memory.db not found (not initialized)"})

    try:
        wt_result = subprocess_module.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10, cwd=str(root),
        )
        session_file = root / ".cnogo" / "worktree-session.json"
        tracked_paths = set()
        if session_file.exists():
            with open(session_file) as handle:
                session_data = json.load(handle)
            for worktree in session_data.get("worktrees", []):
                tracked_paths.add(worktree.get("path", ""))

        worktree_paths = []
        for line in wt_result.stdout.splitlines():
            if line.startswith("worktree "):
                worktree_path = line[len("worktree "):]
                if worktree_path != str(root):
                    worktree_paths.append(worktree_path)

        orphaned = [path for path in worktree_paths if path not in tracked_paths]
        if orphaned:
            checks.append({"name": "orphaned_worktrees", "status": "warn", "details": f"{len(orphaned)} orphaned worktree(s): {', '.join(orphaned[:3])}"})
        else:
            checks.append({"name": "orphaned_worktrees", "status": "pass", "details": f"No orphaned worktrees ({len(worktree_paths)} tracked)"})
    except Exception as exc:
        checks.append({"name": "orphaned_worktrees", "status": "warn", "details": str(exc)[:200]})

    try:
        import sys as _sys
        _repo = str(root)
        if _repo not in _sys.path:
            _sys.path.insert(0, _repo)
        from scripts.memory.watchdog import check_stale_issues

        stale = check_stale_issues(root)
        if stale:
            titles = [s.get("title", s.get("id", "?"))[:40] for s in stale[:3]]
            checks.append({"name": "stale_issues", "status": "warn", "details": f"{len(stale)} stale issue(s): {', '.join(titles)}"})
        else:
            checks.append({"name": "stale_issues", "status": "pass", "details": "No stale issues found"})
    except Exception as exc:
        checks.append({"name": "stale_issues", "status": "warn", "details": f"Could not check: {exc}"})

    settings_path = root / ".claude" / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path) as handle:
                settings = json.load(handle)
            hooks = settings.get("hooks", {})
            missing_scripts = []
            for hook_entries in hooks.values():
                if isinstance(hook_entries, list):
                    for entry in hook_entries:
                        cmd = entry.get("command", "") if isinstance(entry, dict) else ""
                        parts = cmd.split()
                        for part in parts:
                            if part.endswith((".sh", ".py")) and not part.startswith("-"):
                                script_path = root / part
                                if not script_path.exists():
                                    missing_scripts.append(part)
            if missing_scripts:
                checks.append({"name": "hook_config", "status": "warn", "details": f"Missing hook scripts: {', '.join(missing_scripts[:3])}"})
            else:
                checks.append({"name": "hook_config", "status": "pass", "details": "All hook script paths valid"})
        except Exception as exc:
            checks.append({"name": "hook_config", "status": "fail", "details": str(exc)[:200]})
    else:
        checks.append({"name": "hook_config", "status": "warn", "details": ".claude/settings.json not found"})

    git_issues = []
    try:
        rc_status, out_status = run_shell("git status --porcelain", cwd=root, timeout_sec=10)
        if rc_status == 0 and out_status.strip():
            git_issues.append("dirty working tree (uncommitted changes)")
    except Exception as exc:
        git_issues.append(f"could not check working tree: {exc}")

    try:
        rc_head, _ = run_shell("git symbolic-ref HEAD", cwd=root, timeout_sec=10)
        if rc_head != 0:
            git_issues.append("detached HEAD")
    except Exception as exc:
        git_issues.append(f"could not check HEAD: {exc}")

    try:
        rc_merged, out_merged = run_shell("git branch --merged main", cwd=root, timeout_sec=10)
        if rc_merged == 0:
            stale_branches = [
                branch.strip().lstrip("* ")
                for branch in out_merged.splitlines()
                if branch.strip() and branch.strip().lstrip("* ") not in {"main", "master", ""}
            ]
            if len(stale_branches) > 3:
                git_issues.append(f"{len(stale_branches)} stale merged branches (exclude main)")
    except Exception as exc:
        git_issues.append(f"could not check merged branches: {exc}")

    if git_issues:
        checks.append({"name": "git_state", "status": "warn", "details": "; ".join(git_issues)})
    else:
        checks.append({"name": "git_state", "status": "pass", "details": "clean working tree, no detached HEAD, merged branches ok"})

    has_fail = any(check["status"] == "fail" for check in checks)

    if json_output:
        print(json.dumps({"checks": checks}, indent=2))
    else:
        status_icons = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        print("cnogo doctor — diagnostic checks\n")
        for check in checks:
            icon = status_icons.get(check["status"], "?")
            print(f"  {icon} {check['name']}: {check['details']}")
        print()
        if has_fail:
            print("Some checks failed. Run with --json for machine-readable output.")
        else:
            print("All checks passed.")

    return 1 if has_fail else 0
