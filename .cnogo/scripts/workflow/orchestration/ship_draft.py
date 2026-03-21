"""Compute ship drafts for features.

Decision record:
  D1 — Hardcoded SHIP_EXCLUDE_PATTERNS for runtime-only paths.
  D2 — Commit message sourced from plan commitMessage field; no LLM re-summarization.
  D3 — Terse PR body: Summary, Test Plan, Review, Planning References.
       Follow-ups section only on warn verdict or open items.
  D5 — Module at .cnogo/scripts/workflow/orchestration/ship_draft.py
  D8 — Returns commitSurface[] + gitAddCommand convenience string.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHIP_EXCLUDE_PATTERNS: tuple[str, ...] = (
    ".cnogo/issues.jsonl",
    ".cnogo/runs/",
    ".cnogo/work-orders/",
    ".cnogo/feature-phases.json",
    ".cnogo/watch/",
    ".cnogo/worktree-session.json",
    ".cnogo/memory.db",
    ".cnogo/memory.db-wal",
    ".cnogo/memory.db-shm",
    ".cnogo/compaction-checkpoint.json",
    ".cnogo/validate-baseline.json",
    ".cnogo/validate-latest.json",
    ".cnogo/scheduler/",
    ".cnogo/graph.db",
    ".cnogo/graph.kuzu/",
    ".cnogo/.venv/",
    ".cnogo/tee/",
    ".cnogo/command-usage.jsonl",
    ".cnogo/task-descriptions-",
    ".cnogo/prompt-",
)

_GITKEEP_EXCEPTION = ".cnogo/work-orders/.gitkeep"

_FEATURES_DIR = Path("docs") / "planning" / "work" / "features"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict[str, Any] | None:
    """Return parsed JSON dict from path, or None on missing/corrupt/non-dict."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _is_excluded(file_path: str) -> bool:
    """Return True if file_path should be excluded from the ship commit.

    Special case: .cnogo/work-orders/.gitkeep is NOT excluded (D1).
    """
    normalized = file_path.lstrip("/")
    if normalized == _GITKEEP_EXCEPTION:
        return False
    for pattern in SHIP_EXCLUDE_PATTERNS:
        if normalized.startswith(pattern) or normalized == pattern.rstrip("/"):
            return True
    return False


def _load_changed_files(root: Path) -> list[str]:
    """Return files changed relative to main branch via git diff.

    Returns empty list if git is unavailable or the main branch doesn't exist.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main...HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        if result.returncode != 0:
            return []
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        expanded: list[str] = []
        for line in lines:
            candidate = (root / line)
            if candidate.is_dir():
                for path in candidate.rglob("*"):
                    if path.is_file():
                        try:
                            expanded.append(str(path.relative_to(root)))
                        except ValueError:
                            expanded.append(str(path))
            else:
                expanded.append(line)
        return expanded
    except Exception:
        return []


def _load_working_tree_files(root: Path) -> list[str]:
    """Return files currently modified or untracked in the working tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        if result.returncode != 0:
            return []
        entries: list[str] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            path = line[3:].strip()
            if not path:
                continue
            candidate = root / path
            if candidate.is_dir():
                for child in candidate.rglob("*"):
                    if not child.is_file():
                        continue
                    try:
                        entries.append(str(child.relative_to(root)))
                    except ValueError:
                        entries.append(str(child))
            else:
                entries.append(path)
        return entries
    except Exception:
        return []


def _load_all_plan_jsons(root: Path, feature: str) -> list[dict[str, Any]]:
    """Return all NN-PLAN.json dicts for the feature, sorted numerically."""
    feature_dir = root / _FEATURES_DIR / feature
    if not feature_dir.is_dir():
        return []
    plans: list[tuple[int, dict[str, Any]]] = []
    for path in feature_dir.glob("[0-9][0-9]-PLAN.json"):
        data = _read_json(path)
        if data is not None:
            try:
                num = int(path.stem.split("-")[0])
            except (ValueError, IndexError):
                num = 0
            plans.append((num, data))
    plans.sort(key=lambda t: t[0])
    return [d for _, d in plans]


def _load_all_summary_jsons(root: Path, feature: str) -> list[dict[str, Any]]:
    """Return all NN-SUMMARY.json dicts for the feature, sorted numerically."""
    feature_dir = root / _FEATURES_DIR / feature
    if not feature_dir.is_dir():
        return []
    summaries: list[tuple[int, dict[str, Any]]] = []
    for path in feature_dir.glob("[0-9][0-9]-SUMMARY.json"):
        data = _read_json(path)
        if data is not None:
            try:
                num = int(path.stem.split("-")[0])
            except (ValueError, IndexError):
                num = 0
            summaries.append((num, data))
    summaries.sort(key=lambda t: t[0])
    return [d for _, d in summaries]


def _latest_plan(root: Path, feature: str) -> dict[str, Any] | None:
    """Return the latest (highest-numbered) plan JSON for the feature."""
    plans = _load_all_plan_jsons(root, feature)
    return plans[-1] if plans else None


def _latest_summary(root: Path, feature: str) -> dict[str, Any] | None:
    """Return the latest (highest-numbered) summary JSON for the feature."""
    summaries = _load_all_summary_jsons(root, feature)
    return summaries[-1] if summaries else None


def _review_json(root: Path, feature: str) -> dict[str, Any] | None:
    """Return REVIEW.json for the feature, or None."""
    return _read_json(root / _FEATURES_DIR / feature / "REVIEW.json")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_commit_surface(root: Path, feature: str) -> list[str]:
    """Compute files to include in ship commit.

    Strategy:
    1. Collect task files[] from all plan JSONs for this feature.
    2. Add planning artifacts (docs/planning/work/features/<slug>/).
    3. Add .cnogo/issues.jsonl if present (memory sync artifact).
    4. Fallback: union with git diff --name-only main...HEAD.
    5. Filter through SHIP_EXCLUDE_PATTERNS.
    6. Only include files that actually exist on disk.
    Returns sorted, deduplicated list.
    """
    collected: set[str] = set()

    # Step 1: task files[] from all plans
    for plan in _load_all_plan_jsons(root, feature):
        tasks = plan.get("tasks", [])
        if isinstance(tasks, list):
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                for f in task.get("files", []):
                    if isinstance(f, str) and f.strip():
                        collected.add(f.strip())

    # Step 2: planning artifacts under the feature directory
    feature_dir = root / _FEATURES_DIR / feature
    if feature_dir.is_dir():
        for artifact in feature_dir.iterdir():
            if artifact.is_file():
                try:
                    rel = str(artifact.relative_to(root))
                except ValueError:
                    rel = str(artifact)
                collected.add(rel)

    # Step 3: fallback union with git diff
    git_files = _load_changed_files(root)
    collected.update(git_files)

    # Step 4: also include active working-tree files for the branch
    collected.update(_load_working_tree_files(root))

    # Step 5: filter excluded
    filtered = [f for f in collected if not _is_excluded(f)]

    # Step 6: only files that actually exist on disk
    existing = [f for f in filtered if (root / f).exists()]

    return sorted(set(existing))


def generate_commit_message(root: Path, feature: str) -> str:
    """Generate commit message from latest plan's commitMessage field.

    Fallback: derive from feat/fix/refactor + feature slug + plan goal.
    """
    plan = _latest_plan(root, feature)
    if plan is not None:
        msg = str(plan.get("commitMessage", "")).strip()
        if msg:
            return msg

    # Fallback: derive from plan goal or slug
    if plan is not None:
        goal = str(plan.get("goal", "")).strip()
        if goal:
            slug_lower = feature.lower()
            if any(kw in slug_lower for kw in ("fix", "bug", "repair", "patch")):
                prefix = "fix"
            elif any(kw in slug_lower for kw in ("refactor", "cleanup", "clean", "dead-code")):
                prefix = "refactor"
            else:
                prefix = "feat"
            scope = feature
            return f"{prefix}({scope}): {goal}"

    return f"feat({feature}): implement {feature}"


def generate_pr_body(root: Path, feature: str) -> str:
    """Generate terse deterministic PR body.

    Sections: Summary, Test Plan, Review, Planning References.
    Follow-ups only when verdict is warn or open items exist.
    """
    plan = _latest_plan(root, feature)
    summary = _latest_summary(root, feature)
    review = _review_json(root, feature)
    feature_dir_rel = str(_FEATURES_DIR / feature)

    lines: list[str] = []

    # Summary section — from plan goals
    lines.append("## Summary")
    if plan is not None:
        goal = str(plan.get("goal", "")).strip()
        if goal:
            lines.append(f"- {goal}")
        tasks = plan.get("tasks", [])
        if isinstance(tasks, list):
            for task in tasks:
                if isinstance(task, dict):
                    name = str(task.get("name", "")).strip()
                    if name:
                        lines.append(f"- {name}")
    if len(lines) == 1:
        lines.append(f"- Implement {feature}")
    lines.append("")

    # Test Plan section — from SUMMARY verification
    lines.append("## Test Plan")
    if summary is not None:
        verifications = summary.get("verification", [])
        if isinstance(verifications, list) and verifications:
            for entry in verifications:
                if isinstance(entry, dict):
                    cmds = entry.get("commands", [])
                    # Fall back to singular "command" for legacy summaries
                    if not cmds:
                        legacy = str(entry.get("command", "")).strip()
                        cmds = [legacy] if legacy else []
                    result = str(entry.get("result", "")).strip()
                    for cmd in cmds:
                        cmd = str(cmd).strip()
                        if cmd:
                            item = f"- `{cmd}`"
                            if result:
                                item += f" — {result}"
                            lines.append(item)
                elif isinstance(entry, str) and entry.strip():
                    lines.append(f"- {entry.strip()}")
        else:
            lines.append("- See SUMMARY.json for verification details")
    else:
        lines.append("- No SUMMARY.json found")
    lines.append("")

    # Review section — verdict + reviewers
    lines.append("## Review")
    if review is not None:
        verdict = str(review.get("verdict", "")).strip()
        if verdict:
            lines.append(f"- Verdict: **{verdict}**")
        reviewers = review.get("reviewers", [])
        if isinstance(reviewers, list) and reviewers:
            lines.append(f"- Reviewers: {', '.join(str(r) for r in reviewers if str(r).strip())}")
        stage_reviews = review.get("stageReviews", [])
        if isinstance(stage_reviews, list):
            for stage in stage_reviews:
                if isinstance(stage, dict):
                    stage_name = str(stage.get("stage", "")).strip()
                    stage_status = str(stage.get("status", "")).strip()
                    if stage_name and stage_status:
                        lines.append(f"- {stage_name}: {stage_status}")
    else:
        lines.append("- No REVIEW.json found")
    lines.append("")

    # Planning References section
    lines.append("## Planning References")
    lines.append(f"- Feature dir: `{feature_dir_rel}/`")
    if plan is not None:
        plan_number = str(plan.get("planNumber", "")).strip()
        if plan_number:
            lines.append(f"- Latest plan: `{feature_dir_rel}/{plan_number}-PLAN.json`")
    if summary is not None:
        summary_number = str(summary.get("planNumber", "")).strip()
        if summary_number:
            lines.append(f"- Latest summary: `{feature_dir_rel}/{summary_number}-SUMMARY.json`")
    if review is not None:
        lines.append(f"- Review: `{feature_dir_rel}/REVIEW.json`")
    lines.append("")

    # Follow-ups — only on warn verdict or open items
    verdict = ""
    if review is not None:
        verdict = str(review.get("verdict", "")).strip().lower()
    warnings: list[str] = []
    if review is not None:
        raw_warnings = review.get("warnings", [])
        if isinstance(raw_warnings, list):
            warnings = [str(w).strip() for w in raw_warnings if str(w).strip()]
    blockers: list[str] = []
    if review is not None:
        raw_blockers = review.get("blockers", [])
        if isinstance(raw_blockers, list):
            blockers = [str(b).strip() for b in raw_blockers if str(b).strip()]

    if verdict in {"warn"} or warnings or blockers:
        lines.append("## Follow-ups")
        for w in warnings:
            lines.append(f"- (warn) {w}")
        for b in blockers:
            lines.append(f"- (blocker) {b}")
        if not warnings and not blockers and verdict == "warn":
            lines.append("- Review returned warn verdict — address open items before merge")
        lines.append("")

    return "\n".join(lines)


def build_ship_draft(root: Path, feature: str) -> dict[str, Any]:
    """Build complete ship draft.

    Returns:
        {
            commitSurface: list[str],
            excludedFiles: list[str],
            commitMessage: str,
            prTitle: str,
            prBody: str,
            branch: str,
            gitAddCommand: str,
            warnings: list[str],
        }
    """
    feature = feature.strip()

    # Compute commit surface
    commit_surface = compute_commit_surface(root, feature)

    # Compute excluded files from both committed branch diff and current working tree.
    git_files = set(_load_changed_files(root))
    working_tree_files = set(_load_working_tree_files(root))
    excluded_files = sorted(set(f for f in git_files.union(working_tree_files) if _is_excluded(f)))

    # Commit message
    commit_message = generate_commit_message(root, feature)

    # PR title: first line of commit message, capped at 72 chars
    pr_title = commit_message.split("\n")[0]
    if len(pr_title) > 72:
        pr_title = pr_title[:69] + "..."

    # PR body
    pr_body = generate_pr_body(root, feature)

    # Branch: try to read from current directory name or use feature/<slug>
    branch = _infer_branch(root, feature)

    # gitAddCommand: quote paths with spaces
    quoted_files = [f'"{f}"' if " " in f else f for f in commit_surface]
    git_add_command = "git add " + " ".join(quoted_files) if quoted_files else "git add"

    # Warnings
    warnings: list[str] = []
    if not commit_surface:
        warnings.append("No files found for commit surface — verify plans and git diff are available")
    if not _latest_plan(root, feature):
        warnings.append(f"No plan JSON found for feature '{feature}'")
    if _latest_summary(root, feature) is None:
        warnings.append(f"No SUMMARY.json found for feature '{feature}'")
    review = _review_json(root, feature)
    if review is None:
        warnings.append(f"No REVIEW.json found for feature '{feature}'")
    elif str(review.get("verdict", "")).strip().lower() == "fail":
        warnings.append("Review verdict is 'fail' — do not ship until blockers are resolved")
    if excluded_files:
        warnings.append(
            "Excluded operational files are present in the branch or working tree: "
            + ", ".join(excluded_files[:5])
        )

    return {
        "commitSurface": commit_surface,
        "excludedFiles": excluded_files,
        "commitMessage": commit_message,
        "prTitle": pr_title,
        "prBody": pr_body,
        "branch": branch,
        "gitAddCommand": git_add_command,
        "warnings": warnings,
    }


def _infer_branch(root: Path, feature: str) -> str:
    """Infer current branch from git, or return feature/<slug> as default."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch and branch != "HEAD":
                return branch
    except Exception:
        pass
    return f"feature/{feature}"
