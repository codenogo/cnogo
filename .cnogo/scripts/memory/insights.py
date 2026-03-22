"""Deterministic derived-memory sync for workflow artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import dispatcher_settings_cfg, load_workflow_config
from scripts.workflow.shared.runtime_root import runtime_path

from . import runtime as _runtime
from . import storage as _st


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _feature_dir(root: Path, feature: str) -> Path:
    return root / "docs" / "planning" / "work" / "features" / feature


def _feature_stub(root: Path, feature: str) -> dict[str, Any]:
    payload = _read_json(_feature_dir(root, feature) / "FEATURE.json")
    return payload if isinstance(payload, dict) else {}


def _feature_context(root: Path, feature: str) -> dict[str, Any]:
    payload = _read_json(_feature_dir(root, feature) / "CONTEXT.json")
    return payload if isinstance(payload, dict) else {}


def _feature_review(root: Path, feature: str) -> dict[str, Any]:
    payload = _read_json(_feature_dir(root, feature) / "REVIEW.json")
    return payload if isinstance(payload, dict) else {}


def _parent_shape_path(root: Path, feature: str) -> Path | None:
    for contract in (_feature_context(root, feature), _feature_stub(root, feature)):
        parent_shape = contract.get("parentShape")
        if not isinstance(parent_shape, dict):
            continue
        raw_path = parent_shape.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        shape_path = Path(raw_path.strip())
        return shape_path if shape_path.is_absolute() else root / shape_path
    return None


def _shape_contract(root: Path, feature: str) -> dict[str, Any]:
    shape_path = _parent_shape_path(root, feature)
    if shape_path is None:
        return {}
    payload = _read_json(shape_path)
    return payload if isinstance(payload, dict) else {}


def _shape_candidate(root: Path, feature: str) -> dict[str, Any]:
    contract = _shape_contract(root, feature)
    candidates = contract.get("candidateFeatures")
    if not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("slug", "")).strip() == feature:
            return candidate
    return {}


def _stable_token(*parts: object) -> str:
    joined = "|".join(str(part).strip() for part in parts if str(part).strip())
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def _observation(
    conn,
    *,
    feature: str,
    kind: str,
    token: str,
    scope: str,
    scope_id: str,
    summary: str,
    detail: str = "",
    confidence: str = "derived",
    observer_role: str = "",
    subject_type: str = "",
    subject_id: str = "",
    metadata: dict[str, Any] | None = None,
    sources: list[dict[str, str]] | None = None,
) -> int:
    observation_id = _st.upsert_observation(
        conn,
        natural_key=f"{feature}|{kind}|{token}",
        kind=kind,
        scope=scope,
        scope_id=scope_id,
        feature_slug=feature,
        subject_type=subject_type,
        subject_id=subject_id,
        observer_role=observer_role,
        confidence=confidence,
        summary=summary,
        detail=detail,
        metadata=metadata,
    )
    _st.replace_observation_sources(conn, observation_id, sources)
    return observation_id


def _sync_cards(
    conn,
    *,
    root: Path,
    feature: str,
    work_order: dict[str, Any],
    open_contradictions: list[dict[str, Any]],
) -> int:
    workflow_cfg = load_workflow_config(root)
    dispatcher_cfg = dispatcher_settings_cfg(workflow_cfg)
    default_profile = str(workflow_cfg.get("profiles", {}).get("default", "feature-delivery")).strip() or "feature-delivery"
    card_count = 0
    _st.upsert_card(
        conn,
        scope="repo",
        scope_id=root.name,
        card_kind="workflow",
        summary=(
            f"Repo defaults to `{default_profile}` with dispatcher autonomy "
            f"`{dispatcher_cfg['autonomy']}` and WIP {dispatcher_cfg['defaultWipLimit']}."
        ),
        content=json.dumps(
            {
                "defaultProfile": default_profile,
                "dispatcher": dispatcher_cfg,
            },
            sort_keys=True,
        ),
        metadata={"root": str(root)},
    )
    card_count += 1

    context = _feature_context(root, feature)
    candidate = _shape_candidate(root, feature)
    decisions = context.get("decisions", []) if isinstance(context.get("decisions"), list) else []
    risks = candidate.get("risks", []) if isinstance(candidate.get("risks"), list) else []
    status = str(work_order.get("status", "queued")).strip() or "queued"
    _st.upsert_card(
        conn,
        scope="feature",
        scope_id=feature,
        card_kind="summary",
        summary=(
            f"Feature `{feature}` is `{status}` with {len(decisions)} decision(s), "
            f"{len(risks)} risk(s), and {len(open_contradictions)} open contradiction(s)."
        ),
        content=json.dumps(
            {
                "status": status,
                "decisions": decisions[:5],
                "risks": risks[:5],
                "contradictions": open_contradictions[:5],
            },
            sort_keys=True,
        ),
        metadata={"feature": feature},
    )
    card_count += 1

    shape = _shape_contract(root, feature)
    if shape:
        sequence = shape.get("recommendedSequence", []) if isinstance(shape.get("recommendedSequence"), list) else []
        _st.upsert_card(
            conn,
            scope="initiative",
            scope_id=str(shape.get("slug", "")).strip() or feature,
            card_kind="summary",
            summary=f"Initiative `{shape.get('initiative', '')}` tracks {len(sequence)} sequenced feature(s).",
            content=json.dumps(
                {
                    "initiative": shape.get("initiative", ""),
                    "sequence": sequence,
                    "openQuestions": shape.get("openQuestions", []),
                },
                sort_keys=True,
            ),
            metadata={"shapePath": str(_parent_shape_path(root, feature) or "")},
        )
        card_count += 1

    preference_observations = [
        item
        for item in _st.list_observations(conn, feature_slug=feature, statuses={"active"}, limit=50)
        if item.get("kind") == "preference"
    ]
    _st.upsert_card(
        conn,
        scope="user",
        scope_id="default",
        card_kind="preferences",
        summary=(
            "No explicit user preferences captured yet."
            if not preference_observations
            else f"Captured {len(preference_observations)} explicit user preference observation(s)."
        ),
        content=json.dumps(preference_observations[:10], sort_keys=True),
        metadata={"feature": feature},
    )
    card_count += 1
    return card_count


def sync_feature_memory(
    root: Path,
    feature: str,
    *,
    work_order: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
    trigger: str = "sync",
) -> dict[str, Any]:
    feature = feature.strip()
    if not feature:
        return {"feature": "", "observations": 0, "contradictions": 0, "cards": 0}

    feature_dir = _feature_dir(root, feature)
    if not feature_dir.exists():
        return {"feature": feature, "observations": 0, "contradictions": 0, "cards": 0}

    stub = _feature_stub(root, feature)
    context = _feature_context(root, feature)
    review_contract = _feature_review(root, feature)
    candidate = _shape_candidate(root, feature)
    work_order_payload = work_order or _read_json(runtime_path(root, "work-orders", f"{feature}.json")) or {}
    run_payload = run or {}

    conn = _runtime.conn(root)
    observation_count = 0
    contradiction_count = 0
    card_count = 0
    try:
        conn.execute("BEGIN")
        observation_ids: dict[str, int] = {}
        decision_observations_by_area: dict[str, list[int]] = {}

        status = str(work_order_payload.get("status", "")).strip()
        if status:
            observation_ids["status_claim"] = _observation(
                conn,
                feature=feature,
                kind="status_claim",
                token="work_order",
                scope="feature",
                scope_id=feature,
                summary=f"Work Order is `{status}`.",
                detail=f"Current phase: {work_order_payload.get('currentPhase', 'unknown')}",
                confidence="explicit",
                observer_role="patrol",
                subject_type="work_order",
                subject_id=str(work_order_payload.get("workOrderId", feature)),
                metadata={
                    "trigger": trigger,
                    "queuePosition": int(work_order_payload.get("queuePosition", 0) or 0),
                    "lane": work_order_payload.get("lane", {}),
                },
                sources=[
                    {
                        "source_kind": "work_order",
                        "source_ref": str(work_order_payload.get("workOrderId", feature)),
                        "source_path": str(runtime_path(root, "work-orders", f"{feature}.json")),
                    }
                ],
            )
            observation_count += 1

        for decision in context.get("decisions", []) if isinstance(context.get("decisions"), list) else []:
            if not isinstance(decision, dict):
                continue
            text = str(decision.get("decision", "")).strip()
            if not text:
                continue
            area = str(decision.get("area", "")).strip()
            rationale = str(decision.get("rationale", "")).strip()
            decision_key = f"decision:{area or text}"
            observation_ids[decision_key] = _observation(
                conn,
                feature=feature,
                kind="decision",
                token=_stable_token(area, text),
                scope="feature",
                scope_id=feature,
                summary=text,
                detail=rationale,
                confidence="explicit",
                observer_role="shape",
                subject_type="context",
                subject_id=feature,
                metadata={"area": area},
                sources=[
                    {
                        "source_kind": "artifact",
                        "source_ref": "CONTEXT.json",
                        "source_path": str(feature_dir / "CONTEXT.json"),
                    }
                ],
            )
            if area:
                decision_observations_by_area.setdefault(area, []).append(observation_ids[decision_key])
            observation_count += 1

        for constraint in context.get("constraints", []) if isinstance(context.get("constraints"), list) else []:
            text = str(constraint).strip()
            if not text:
                continue
            _observation(
                conn,
                feature=feature,
                kind="assumption",
                token=_stable_token(text),
                scope="feature",
                scope_id=feature,
                summary=text,
                confidence="explicit",
                observer_role="shape",
                subject_type="context",
                subject_id=feature,
                sources=[
                    {
                        "source_kind": "artifact",
                        "source_ref": "CONTEXT.json",
                        "source_path": str(feature_dir / "CONTEXT.json"),
                    }
                ],
            )
            observation_count += 1

        for risk in candidate.get("risks", []) if isinstance(candidate.get("risks"), list) else []:
            text = str(risk).strip()
            if not text:
                continue
            _observation(
                conn,
                feature=feature,
                kind="risk",
                token=_stable_token(text),
                scope="feature",
                scope_id=feature,
                summary=text,
                confidence="explicit",
                observer_role="shape",
                subject_type="feature",
                subject_id=feature,
                sources=[
                    {
                        "source_kind": "artifact",
                        "source_ref": "FEATURE.json",
                        "source_path": str(feature_dir / "FEATURE.json"),
                    }
                ],
            )
            observation_count += 1

        handoff_summary = str((stub or candidate).get("handoffSummary", "")).strip()
        if handoff_summary:
            observation_ids["handoff"] = _observation(
                conn,
                feature=feature,
                kind="handoff",
                token="current",
                scope="feature",
                scope_id=feature,
                summary=handoff_summary,
                confidence="explicit",
                observer_role="shape",
                subject_type="feature",
                subject_id=feature,
                sources=[
                    {
                        "source_kind": "artifact",
                        "source_ref": "FEATURE.json",
                        "source_path": str(feature_dir / "FEATURE.json"),
                    }
                ],
            )
            observation_count += 1

        attention_summary = work_order_payload.get("attentionSummary", {}) if isinstance(work_order_payload.get("attentionSummary"), dict) else {}
        if status == "blocked" or int(attention_summary.get("itemCount", 0) or 0) > 0:
            blocker_summary = f"Feature is blocked ({attention_summary.get('highestSeverity', 'warn')})."
            observation_ids["blocker"] = _observation(
                conn,
                feature=feature,
                kind="blocker",
                token="work_order",
                scope="feature",
                scope_id=feature,
                summary=blocker_summary,
                detail=json.dumps(attention_summary, sort_keys=True),
                confidence="derived",
                observer_role="patrol",
                subject_type="work_order",
                subject_id=str(work_order_payload.get("workOrderId", feature)),
                sources=[
                    {
                        "source_kind": "work_order",
                        "source_ref": str(work_order_payload.get("workOrderId", feature)),
                        "source_path": str(runtime_path(root, "work-orders", f"{feature}.json")),
                    }
                ],
            )
            observation_count += 1

        review_summary = work_order_payload.get("reviewSummary", {}) if isinstance(work_order_payload.get("reviewSummary"), dict) else {}
        review_verdict = str(
            review_summary.get("finalVerdict")
            or review_summary.get("verdict")
            or review_contract.get("verdict")
            or "pending"
        ).strip()
        if review_verdict in {"warn", "fail"}:
            observation_ids["review_finding"] = _observation(
                conn,
                feature=feature,
                kind="review_finding",
                token=review_verdict,
                scope="feature",
                scope_id=feature,
                summary=f"Review verdict is `{review_verdict}`.",
                detail=json.dumps(review_summary or review_contract, sort_keys=True),
                confidence="verified",
                observer_role="reviewer",
                subject_type="review",
                subject_id=feature,
                sources=[
                    {
                        "source_kind": "artifact",
                        "source_ref": "REVIEW.json",
                        "source_path": str(feature_dir / "REVIEW.json"),
                    }
                ],
            )
            observation_count += 1

        plan_verify_passed = None
        if isinstance(run_payload.get("review_readiness"), dict):
            plan_verify_passed = run_payload["review_readiness"].get("planVerifyPassed")
        if plan_verify_passed is True:
            observation_ids["verification"] = _observation(
                conn,
                feature=feature,
                kind="verification",
                token="plan_verify_pass",
                scope="feature",
                scope_id=feature,
                summary="Plan verification passed.",
                detail=json.dumps(run_payload.get("review_readiness", {}), sort_keys=True),
                confidence="verified",
                observer_role="implementer",
                subject_type="run",
                subject_id=str(run_payload.get("run_id", "")),
                sources=[
                    {
                        "source_kind": "run",
                        "source_ref": str(run_payload.get("run_id", "")),
                        "source_path": str(runtime_path(root, "runs", feature, f"{run_payload.get('run_id', '')}.json")),
                    }
                ],
            )
            observation_count += 1
        elif plan_verify_passed is False:
            observation_ids["verification_failed"] = _observation(
                conn,
                feature=feature,
                kind="verification",
                token="plan_verify_fail",
                scope="feature",
                scope_id=feature,
                summary="Plan verification failed.",
                detail=json.dumps(run_payload.get("review_readiness", {}), sort_keys=True),
                confidence="verified",
                observer_role="implementer",
                subject_type="run",
                subject_id=str(run_payload.get("run_id", "")),
                sources=[
                    {
                        "source_kind": "run",
                        "source_ref": str(run_payload.get("run_id", "")),
                        "source_path": str(runtime_path(root, "runs", feature, f"{run_payload.get('run_id', '')}.json")),
                    }
                ],
            )
            observation_count += 1

        open_contradictions: list[str] = []
        if status in {"reviewing", "shipping", "completed"} and plan_verify_passed is False:
            _st.upsert_contradiction(
                conn,
                contradiction_key=f"{feature}|verification_failed_but_progressed",
                feature_slug=feature,
                scope="feature",
                subject_id=feature,
                kind="verification_failed_but_progressed",
                summary="Feature progressed even though plan verification is marked failed.",
                left_observation_id=observation_ids.get("status_claim", 0),
                right_observation_id=observation_ids.get("verification_failed", 0),
                metadata={"status": status},
            )
            contradiction_count += 1
            open_contradictions.append("verification_failed_but_progressed")
        else:
            _st.resolve_contradiction(conn, f"{feature}|verification_failed_but_progressed")

        if status in {"shipping", "completed"} and review_verdict == "fail":
            _st.upsert_contradiction(
                conn,
                contradiction_key=f"{feature}|review_failed_but_progressed",
                feature_slug=feature,
                scope="feature",
                subject_id=feature,
                kind="review_failed_but_progressed",
                summary="Feature progressed to ship or completion after a failing review verdict.",
                left_observation_id=observation_ids.get("status_claim", 0),
                right_observation_id=observation_ids.get("review_finding", 0),
                metadata={"status": status, "reviewVerdict": review_verdict},
            )
            contradiction_count += 1
            open_contradictions.append("review_failed_but_progressed")
        else:
            _st.resolve_contradiction(conn, f"{feature}|review_failed_but_progressed")

        if status == "completed" and (
            int(attention_summary.get("itemCount", 0) or 0) > 0 or review_verdict == "fail"
        ):
            _st.upsert_contradiction(
                conn,
                contradiction_key=f"{feature}|completed_but_blocked",
                feature_slug=feature,
                scope="feature",
                subject_id=feature,
                kind="completed_but_blocked",
                summary="Feature is marked completed while blockers or failing review signals remain.",
                left_observation_id=observation_ids.get("status_claim", 0),
                right_observation_id=observation_ids.get("blocker", observation_ids.get("review_finding", 0)),
                metadata={"attention": attention_summary, "reviewVerdict": review_verdict},
            )
            contradiction_count += 1
            open_contradictions.append("completed_but_blocked")
        else:
            _st.resolve_contradiction(conn, f"{feature}|completed_but_blocked")

        for area, items in decision_observations_by_area.items():
            if len(items) > 1:
                _st.upsert_contradiction(
                    conn,
                    contradiction_key=f"{feature}|decision_conflict|{area}",
                    feature_slug=feature,
                    scope="feature",
                    subject_id=feature,
                    kind="decision_conflict",
                    summary=f"Feature has multiple active decisions for area `{area}`.",
                    left_observation_id=items[0],
                    right_observation_id=items[1],
                    metadata={"area": area},
                )
                contradiction_count += 1
                open_contradictions.append(f"decision_conflict:{area}")
            else:
                _st.resolve_contradiction(conn, f"{feature}|decision_conflict|{area}")

        open_contradiction_rows = _st.list_contradictions(conn, feature_slug=feature, status="open", limit=20)
        card_count = _sync_cards(
            conn,
            root=root,
            feature=feature,
            work_order=work_order_payload,
            open_contradictions=open_contradiction_rows,
        )
        conn.commit()
        return {
            "feature": feature,
            "observations": observation_count,
            "contradictions": len(open_contradiction_rows),
            "cards": card_count,
        }
    finally:
        conn.close()
