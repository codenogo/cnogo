"""Live initiative rollup computed from SHAPE.json, feature directories, and Work Orders.

Decision record:
  D1 — Rollup is computed live on demand; no persisted artifact.
  D2 — Work Order status 'cancelled' stays 'cancelled' in the initiative view (not mapped to 'parked').
  D5 — Per-feature review signal is a compact reviewVerdict field: pending|pass|warn|fail.
  D6 — Unified status mapping (see _derive_feature_status).
  D7 — Read-only on SHAPE.json; shapeFeedback is collected from child CONTEXT.json files.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INITIATIVE_ROLLUP_STATUSES = frozenset(
    {
        # SHAPE candidate statuses (no FEATURE.json stub yet)
        "draft",
        "parked",
        "blocked",
        # Post-stub progression statuses
        "discuss-ready",
        "discussing",
        "planned",
        # Work Order driven statuses
        "implementing",
        "reviewing",
        "shipping",
        "completed",
        "cancelled",
    }
)

REVIEW_VERDICTS = frozenset({"pending", "pass", "warn", "fail"})

_FEATURES_DIR = Path("docs") / "planning" / "work" / "features"
_IDEAS_DIR = Path("docs") / "planning" / "work" / "ideas"
_WORK_ORDERS_DIR = Path(".cnogo") / "work-orders"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    """Return parsed JSON dict from path, or None on missing/corrupt/non-dict."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _has_plan(feature_dir: Path) -> bool:
    """Return True if any NN-PLAN.json exists under the feature directory."""
    if not feature_dir.is_dir():
        return False
    return bool(list(feature_dir.glob("[0-9][0-9]-PLAN.json")))


# ---------------------------------------------------------------------------
# Status derivation (D6)
# ---------------------------------------------------------------------------


def _derive_feature_status(root: Path, slug: str, shape_candidate_status: str) -> str:
    """Compute the unified status for a candidate feature.

    Logic (D6):
      1. No FEATURE.json stub  → use shape_candidate_status (draft/parked/blocked)
      2. FEATURE.json exists   → 'discuss-ready'
      3. CONTEXT.json exists   → 'discussing'
      4. PLAN exists, no WO    → 'planned'
      5. Work Order exists     → use WO status verbatim
         Note (D2): 'cancelled' is preserved as-is.
    """
    feature_dir = root / _FEATURES_DIR / slug
    feature_json = feature_dir / "FEATURE.json"
    context_json = feature_dir / "CONTEXT.json"
    wo_path = root / _WORK_ORDERS_DIR / f"{slug}.json"

    # Step 1 — no FEATURE.json stub → fall back to SHAPE candidate status
    if not feature_json.exists():
        candidate = shape_candidate_status.strip()
        if candidate in INITIATIVE_ROLLUP_STATUSES:
            return candidate
        return "draft"

    # Step 5 — Work Order exists → its status wins (D2: preserve 'cancelled')
    wo_data = _read_json(wo_path)
    if wo_data is not None:
        wo_status = str(wo_data.get("status", "")).strip()
        if wo_status in INITIATIVE_ROLLUP_STATUSES:
            return wo_status
        # Fallthrough: WO exists but status is unrecognised; treat as implementing
        return "implementing"

    # Step 4 — PLAN exists but no Work Order → 'planned'
    if _has_plan(feature_dir):
        return "planned"

    # Step 3 — CONTEXT.json exists → 'discussing'
    if context_json.exists():
        return "discussing"

    # Step 2 — FEATURE.json exists, nothing else → 'discuss-ready'
    return "discuss-ready"


# ---------------------------------------------------------------------------
# Review verdict (D5)
# ---------------------------------------------------------------------------


def _review_verdict(wo_data: dict[str, Any] | None) -> str:
    """Extract a compact review verdict from Work Order data.

    Returns one of: pending|pass|warn|fail
    """
    if wo_data is None:
        return "pending"
    review_summary = wo_data.get("reviewSummary")
    if not isinstance(review_summary, dict):
        return "pending"
    # Prefer finalVerdict, fall back to verdict, then status
    for key in ("finalVerdict", "verdict", "status"):
        raw = review_summary.get(key)
        if isinstance(raw, str) and raw.strip():
            val = raw.strip().lower()
            # Normalise common synonyms
            if val in {"pass", "passed", "approved"}:
                return "pass"
            if val in {"fail", "failed", "rejected"}:
                return "fail"
            if val in {"warn", "warning", "needs-changes"}:
                return "warn"
    return "pending"


# ---------------------------------------------------------------------------
# Shape feedback collection (D7)
# ---------------------------------------------------------------------------


def _collect_shape_feedback(root: Path, candidate_slugs: list[str]) -> list[dict[str, Any]]:
    """Scan child CONTEXT.json files for shapeFeedback entries.

    Each entry is normalised to: {summary, suggestedAction?, affectedFeatures?, sourceFeature}
    Read-only — never writes to SHAPE.json (D7).
    """
    feedback: list[dict[str, Any]] = []
    for slug in candidate_slugs:
        context_path = root / _FEATURES_DIR / slug / "CONTEXT.json"
        ctx_data = _read_json(context_path)
        if not isinstance(ctx_data, dict):
            continue
        raw_feedback = ctx_data.get("shapeFeedback")
        if not isinstance(raw_feedback, list):
            continue
        for item in raw_feedback:
            if isinstance(item, str) and item.strip():
                feedback.append({"summary": item.strip(), "sourceFeature": slug})
            elif isinstance(item, dict):
                entry: dict[str, Any] = {"sourceFeature": slug}
                summary = item.get("summary")
                if isinstance(summary, str) and summary.strip():
                    entry["summary"] = summary.strip()
                else:
                    # Skip malformed entries without a summary
                    continue
                suggested = item.get("suggestedAction")
                if isinstance(suggested, str) and suggested.strip():
                    entry["suggestedAction"] = suggested.strip()
                affected = item.get("affectedFeatures")
                if isinstance(affected, list):
                    entry["affectedFeatures"] = [str(f) for f in affected if str(f).strip()]
                feedback.append(entry)
    return feedback


# ---------------------------------------------------------------------------
# Initiative-level next action
# ---------------------------------------------------------------------------


def _compute_next_initiative_action(
    features_rollup: list[dict[str, Any]],
    recommended_sequence: list[str],
) -> dict[str, Any]:
    """Return a prescriptive next-action dict for the initiative.

    Priority:
      1. If any feature is 'blocked' → unblock it
      2. Follow recommendedSequence order: pick the first non-completed/non-cancelled feature
      3. If everything completed → initiative is done
    """
    status_map = {f["slug"]: f["status"] for f in features_rollup}

    # Priority 1: blocked features
    blocked = [f for f in features_rollup if f["status"] == "blocked"]
    if blocked:
        slug = blocked[0]["slug"]
        return {
            "kind": "unblock",
            "summary": f"Unblock '{slug}' before proceeding with the initiative.",
            "command": f"python3 .cnogo/scripts/workflow_memory.py work-show {slug}",
            "targetFeature": slug,
        }

    terminal_statuses = {"completed", "cancelled"}

    # Priority 2: follow recommended sequence
    for slug in recommended_sequence:
        st = status_map.get(slug)
        if st is None or st in terminal_statuses:
            continue
        # Determine the appropriate command for the current status
        action_map = {
            "draft": ("shape", f"/shape {slug}", "Shape or promote the feature stub."),
            "parked": ("review", f"/shape {slug}", "Review and re-engage with parked feature."),
            "discuss-ready": ("discuss", f"/discuss {slug}", "Begin feature discussion."),
            "discussing": ("discuss", f"/discuss {slug}", "Continue feature discussion."),
            "planned": ("implement", f"/implement {slug}", "Start implementation."),
            "implementing": ("implement", f"/implement {slug}", "Continue implementation."),
            "reviewing": ("review", f"/review {slug}", "Complete review."),
            "shipping": ("ship", f"/ship {slug}", "Complete ship tracking."),
        }
        kind, command, summary = action_map.get(st, ("implement", f"/implement {slug}", f"Advance '{slug}'."))
        return {
            "kind": kind,
            "summary": summary,
            "command": command,
            "targetFeature": slug,
        }

    # Priority 3: all terminal
    non_terminal = [f for f in features_rollup if f["status"] not in terminal_statuses]
    if non_terminal:
        # Sequence not specified or exhausted — pick the first non-terminal feature
        slug = non_terminal[0]["slug"]
        return {
            "kind": "implement",
            "summary": f"Advance '{slug}' to completion.",
            "command": f"/implement {slug}",
            "targetFeature": slug,
        }

    return {
        "kind": "complete",
        "summary": "All features are completed or cancelled. Initiative is done.",
        "command": "",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_initiative_rollup(root: Path, shape_path: Path) -> dict[str, Any]:
    """Build a live rollup for one initiative from its SHAPE.json.

    Returns dict with:
      - initiative: str
      - slug: str
      - shapePath: str
      - totalFeatures: int
      - completedFeatures: int
      - features: list[dict]  (slug, displayName, status, reviewVerdict, nextAction)
      - pendingFeedback: list[dict]
      - nextAction: dict
      - timestamp: str

    On error (missing/corrupt SHAPE.json), returns dict with an 'error' key
    instead of raising.
    """
    shape_data = _read_json(shape_path)
    if shape_data is None:
        return {
            "error": f"Cannot read SHAPE.json at {shape_path}",
            "shapePath": str(shape_path),
            "timestamp": _now_iso(),
        }

    initiative = str(shape_data.get("initiative", "")).strip()
    slug = str(shape_data.get("slug", shape_path.parent.name)).strip()
    candidate_features = shape_data.get("candidateFeatures", [])
    if not isinstance(candidate_features, list):
        candidate_features = []

    recommended_sequence: list[str] = []
    raw_seq = shape_data.get("recommendedSequence", [])
    if isinstance(raw_seq, list):
        recommended_sequence = [str(s).strip() for s in raw_seq if str(s).strip()]

    features_rollup: list[dict[str, Any]] = []
    candidate_slugs: list[str] = []

    for candidate in candidate_features:
        if not isinstance(candidate, dict):
            continue
        c_slug = str(candidate.get("slug", "")).strip()
        if not c_slug:
            continue
        candidate_slugs.append(c_slug)
        display_name = str(candidate.get("displayName", c_slug)).strip()
        shape_candidate_status = str(candidate.get("status", "draft")).strip()

        status = _derive_feature_status(root, c_slug, shape_candidate_status)

        # Review verdict from Work Order
        wo_path = root / _WORK_ORDERS_DIR / f"{c_slug}.json"
        wo_data = _read_json(wo_path)
        verdict = _review_verdict(wo_data)

        # Per-feature next action (lightweight — initiative-level action below is richer)
        feature_next_action = _feature_next_action(c_slug, status)

        features_rollup.append(
            {
                "slug": c_slug,
                "displayName": display_name,
                "status": status,
                "reviewVerdict": verdict,
                "nextAction": feature_next_action,
            }
        )

    completed_count = sum(1 for f in features_rollup if f["status"] == "completed")
    pending_feedback = _collect_shape_feedback(root, candidate_slugs)
    next_action = _compute_next_initiative_action(features_rollup, recommended_sequence)

    return {
        "initiative": initiative,
        "slug": slug,
        "shapePath": str(shape_path),
        "totalFeatures": len(features_rollup),
        "completedFeatures": completed_count,
        "features": features_rollup,
        "pendingFeedback": pending_feedback,
        "nextAction": next_action,
        "timestamp": _now_iso(),
    }


def _feature_next_action(slug: str, status: str) -> dict[str, Any]:
    """Return a minimal next-action for a single feature within an initiative."""
    action_map: dict[str, tuple[str, str, str]] = {
        "draft": ("shape", f"/shape {slug}", "Shape or promote this feature."),
        "parked": ("review", f"/shape {slug}", "Review and re-engage with this feature."),
        "blocked": ("attention", f"python3 .cnogo/scripts/workflow_memory.py work-show {slug}", "Resolve blocker."),
        "discuss-ready": ("discuss", f"/discuss {slug}", "Begin discussion."),
        "discussing": ("discuss", f"/discuss {slug}", "Continue discussion."),
        "planned": ("implement", f"/implement {slug}", "Start implementation."),
        "implementing": ("implement", f"/implement {slug}", "Continue implementation."),
        "reviewing": ("review", f"/review {slug}", "Complete review."),
        "shipping": ("ship", f"/ship {slug}", "Complete ship tracking."),
        "completed": ("none", "", "Feature is complete."),
        "cancelled": ("none", "", "Feature is cancelled."),
    }
    kind, command, summary = action_map.get(status, ("implement", f"/implement {slug}", f"Advance '{slug}'."))
    result: dict[str, Any] = {"kind": kind, "summary": summary}
    if command:
        result["command"] = command
    return result


def list_initiatives(root: Path) -> list[dict[str, Any]]:
    """Scan docs/planning/work/ideas/ for SHAPE.json files.

    Returns list of dicts with: slug, initiative, shapePath, candidateCount.
    Results are sorted alphabetically by slug.
    """
    ideas_dir = root / _IDEAS_DIR
    results: list[dict[str, Any]] = []
    if not ideas_dir.is_dir():
        return results

    for idea_dir in sorted(ideas_dir.iterdir()):
        if not idea_dir.is_dir():
            continue
        shape_path = idea_dir / "SHAPE.json"
        if not shape_path.exists():
            continue
        shape_data = _read_json(shape_path)
        if shape_data is None:
            continue
        initiative = str(shape_data.get("initiative", "")).strip()
        slug = str(shape_data.get("slug", idea_dir.name)).strip() or idea_dir.name
        candidate_features = shape_data.get("candidateFeatures", [])
        candidate_count = len(candidate_features) if isinstance(candidate_features, list) else 0
        results.append(
            {
                "slug": slug,
                "initiative": initiative,
                "shapePath": str(shape_path),
                "candidateCount": candidate_count,
            }
        )

    return results
