#!/usr/bin/env python3
"""
Workflow Validator for Universal Development Workflow Pack

Validates that planning artifacts follow the workflow rules and that
machine-checkable contracts exist for key markdown files.

No external dependencies.
"""

from __future__ import annotations

try:
    import _bootstrap  # noqa: F401
except ImportError:
    pass  # imported as module; caller manages sys.path

import sys
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from workflow_utils import load_json as _load_json
    from workflow_utils import iter_skill_paths as _iter_skill_paths
    from workflow_utils import parse_skill_frontmatter as _parse_skill_frontmatter
except ModuleNotFoundError:
    from .workflow_utils import load_json as _load_json  # type: ignore
    from .workflow_utils import iter_skill_paths as _iter_skill_paths  # type: ignore
    from .workflow_utils import parse_skill_frontmatter as _parse_skill_frontmatter  # type: ignore

from scripts.workflow.shared.config import DEFAULT_BOOTSTRAP_CONTEXT
from scripts.workflow.shared.config import DEFAULT_TOKEN_BUDGETS
from scripts.workflow.shared.artifacts import age_days as _shared_age_days
from scripts.workflow.shared.artifacts import artifact_time as _shared_artifact_time
from scripts.workflow.shared.artifacts import linked_artifact_time as _shared_linked_artifact_time
from scripts.workflow.shared.artifacts import resolve_contract_ref as _shared_resolve_contract_ref
from scripts.workflow.shared.artifacts import utc_now as _shared_utc_now
from scripts.workflow.shared.config import bootstrap_context_cfg as _shared_bootstrap_context_cfg
from scripts.workflow.shared.config import freshness_cfg as _shared_freshness_cfg
from scripts.workflow.shared.config import load_workflow_config as _shared_load_workflow_config
from scripts.workflow.shared.config import token_budgets_cfg as _shared_token_budgets_cfg
from scripts.workflow.shared.git import is_git_repo as _shared_is_git_repo
from scripts.workflow.shared.git import repo_root as _shared_repo_root
from scripts.workflow.shared.git import staged_files as _shared_staged_files
from scripts.workflow.shared.timestamps import parse_iso_timestamp as _shared_parse_ts
from scripts.workflow.validate import baseline as _baseline_helpers
from scripts.workflow.validate import cli as _cli_helpers
from scripts.workflow.validate import common as _common_helpers
from scripts.workflow.validate import config_policy as _config_policy_helpers
from scripts.workflow.validate import contracts_feature as _feature_helpers
from scripts.workflow.validate import contracts_plan as _plan_helpers
from scripts.workflow.validate import contracts_quick as _quick_helpers
from scripts.workflow.validate import contracts_research as _research_helpers
from scripts.workflow.validate import repo as _repo_helpers
from scripts.workflow.validate import repo_policy as _repo_policy_helpers
from scripts.workflow.validate import contracts_shape as _shape_helpers

_is_positive_int = _common_helpers.is_positive_int
FEATURE_SLUG_RE = _common_helpers.FEATURE_SLUG_RE
QUICK_DIR_RE = _common_helpers.QUICK_DIR_RE
PLAN_MD_RE = _common_helpers.PLAN_MD_RE
SUMMARY_MD_RE = _common_helpers.SUMMARY_MD_RE
SHAPE_CANDIDATE_STATUSES = _common_helpers.SHAPE_CANDIDATE_STATUSES

_repo_root = _shared_repo_root
_is_git_repo = _shared_is_git_repo
_staged_files = _shared_staged_files


@dataclass
class Finding:
    level: str  # "ERROR" | "WARN"
    message: str
    path: str | None = None

    def format(self) -> str:
        loc = f" ({self.path})" if self.path else ""
        return f"[{self.level}]{loc} {self.message}"


_require = partial(_common_helpers.require, finding_type=Finding)
_validate_memory_runtime = partial(_common_helpers.validate_memory_runtime, finding_type=Finding)
_validate_feature_slug = partial(_common_helpers.validate_feature_slug, finding_type=Finding)
_is_nonempty_str = _common_helpers.is_nonempty_str
_resolve_contract_ref = _shared_resolve_contract_ref
_linked_artifact_time = partial(_shared_linked_artifact_time, load_json=_load_json)
_utc_now = _shared_utc_now
_parse_ts = _shared_parse_ts
_artifact_time = partial(_shared_artifact_time, load_json=_load_json)
_age_days = partial(_shared_age_days, now=_utc_now)
_freshness_cfg = _shared_freshness_cfg
_token_budgets_cfg = _shared_token_budgets_cfg
_bootstrap_context_cfg = _shared_bootstrap_context_cfg
_word_count = _common_helpers.word_count
_policy_level_to_finding = _plan_helpers.policy_level_to_finding
_validate_plan_contract = partial(
    _plan_helpers.validate_plan_contract,
    is_positive_int=_is_positive_int,
    finding_type=Finding,
)
_validate_quick_contract = partial(_quick_helpers.validate_quick_contract, finding_type=Finding)
_validate_quick_summary = partial(_quick_helpers.validate_quick_summary, finding_type=Finding)
_iter_feature_dirs = _common_helpers.iter_feature_dirs
_iter_quick_dirs = _common_helpers.iter_quick_dirs
_iter_research_dirs = _common_helpers.iter_research_dirs
_iter_ideas_dirs = _common_helpers.iter_ideas_dirs
_detect_repo_shape = _repo_policy_helpers.detect_repo_shape
_load_workflow_config = _shared_load_workflow_config
_validate_workflow_config = partial(
    _config_policy_helpers.validate_workflow_config,
    is_positive_int=_is_positive_int,
    finding_type=Finding,
)
_packages_from_cfg = _repo_policy_helpers.packages_from_cfg
_infer_task_package = _repo_policy_helpers.infer_task_package
_get_monorepo_scope_level = _repo_policy_helpers.get_monorepo_scope_level
_get_operating_principles_level = _repo_policy_helpers.get_operating_principles_level
_get_tdd_mode_level = _repo_policy_helpers.get_tdd_mode_level
_get_verification_before_completion_level = _repo_policy_helpers.get_verification_before_completion_level
_get_two_stage_review_level = _repo_policy_helpers.get_two_stage_review_level
_get_task_ownership_level = _repo_policy_helpers.get_task_ownership_level
_verify_cmd_scoped = _repo_policy_helpers.verify_cmd_scoped

_validate_ci_verification = partial(
    _feature_helpers.validate_ci_verification,
    require=_require,
    load_json=_load_json,
    policy_level_to_finding=_policy_level_to_finding,
    finding_type=Finding,
)
_validate_feature_lifecycle_and_freshness = partial(
    _feature_helpers.validate_feature_lifecycle_and_freshness,
    artifact_time=_artifact_time,
    age_days=_age_days,
    finding_type=Finding,
)
_validate_quick_tasks = partial(
    _quick_helpers.validate_quick_tasks,
    iter_quick_dirs=_iter_quick_dirs,
    quick_dir_re=QUICK_DIR_RE,
    require=_require,
    load_json=_load_json,
    validate_quick_contract=_validate_quick_contract,
    validate_quick_summary=_validate_quick_summary,
    finding_type=Finding,
)
_validate_research = partial(
    _research_helpers.validate_research,
    iter_research_dirs=_iter_research_dirs,
    require=_require,
    load_json=_load_json,
    finding_type=Finding,
)
_validate_legacy_brainstorm_contract = partial(
    _shape_helpers.validate_legacy_brainstorm_contract,
    finding_type=Finding,
)
_validate_decision_log = partial(
    _shape_helpers.validate_decision_log,
    is_nonempty_str=_is_nonempty_str,
    finding_type=Finding,
)
_validate_shape_threads = partial(
    _shape_helpers.validate_shape_threads,
    is_nonempty_str=_is_nonempty_str,
    finding_type=Finding,
)
_validate_next_shape_moves = partial(
    _shape_helpers.validate_next_shape_moves,
    is_nonempty_str=_is_nonempty_str,
    finding_type=Finding,
)
_validate_shape_feedback = partial(
    _shape_helpers.validate_shape_feedback,
    is_nonempty_str=_is_nonempty_str,
    finding_type=Finding,
)
_validate_contract_link = partial(
    _feature_helpers.validate_contract_link,
    is_nonempty_str=_is_nonempty_str,
    resolve_contract_ref=_resolve_contract_ref,
    parse_ts=_parse_ts,
    finding_type=Finding,
)
_warn_if_link_stale = partial(
    _feature_helpers.warn_if_link_stale,
    is_nonempty_str=_is_nonempty_str,
    parse_ts=_parse_ts,
    linked_artifact_time=_linked_artifact_time,
    finding_type=Finding,
)
_validate_feature_stub_contract = partial(
    _feature_helpers.validate_feature_stub_contract,
    is_nonempty_str=_is_nonempty_str,
    shape_candidate_statuses=SHAPE_CANDIDATE_STATUSES,
    validate_contract_link=_validate_contract_link,
    warn_if_link_stale=_warn_if_link_stale,
    finding_type=Finding,
)
_validate_shape_contract = partial(
    _shape_helpers.validate_shape_contract,
    feature_slug_re=FEATURE_SLUG_RE,
    shape_candidate_statuses=SHAPE_CANDIDATE_STATUSES,
    is_nonempty_str=_is_nonempty_str,
    validate_decision_log=_validate_decision_log,
    validate_shape_threads=_validate_shape_threads,
    validate_next_shape_moves=_validate_next_shape_moves,
    finding_type=Finding,
)
_validate_shape_artifacts = partial(
    _shape_helpers.validate_shape_artifacts,
    iter_ideas_dirs=_iter_ideas_dirs,
    require=_require,
    load_json=_load_json,
    validate_shape_contract=_validate_shape_contract,
    validate_legacy_brainstorm_contract=_validate_legacy_brainstorm_contract,
    finding_type=Finding,
)


def _validate_features(
    root: Path,
    findings: list[Finding],
    touched,
    shape: dict[str, Any],
    monorepo_scope_level: str,
    operating_principles_level: str,
    tdd_mode_level: str,
    verification_before_completion_level: str,
    two_stage_review_level: str,
    packages_cfg: list[dict[str, str]],
    freshness_cfg: dict[str, Any],
    feature_filter: str | None = None,
) -> None:
    _feature_helpers.validate_features(
        root,
        findings,
        touched,
        shape=shape,
        monorepo_scope_level=monorepo_scope_level,
        operating_principles_level=operating_principles_level,
        tdd_mode_level=tdd_mode_level,
        verification_before_completion_level=verification_before_completion_level,
        two_stage_review_level=two_stage_review_level,
        packages_cfg=packages_cfg,
        freshness_cfg=freshness_cfg,
        feature_filter=feature_filter,
        iter_feature_dirs=_iter_feature_dirs,
        require=_require,
        load_json=_load_json,
        validate_feature_slug=_validate_feature_slug,
        validate_feature_stub_contract=_validate_feature_stub_contract,
        validate_shape_feedback=_validate_shape_feedback,
        validate_contract_link=_validate_contract_link,
        warn_if_link_stale=_warn_if_link_stale,
        validate_plan_contract=_validate_plan_contract,
        infer_task_package=_infer_task_package,
        verify_cmd_scoped=_verify_cmd_scoped,
        plan_md_re=PLAN_MD_RE,
        summary_md_re=SUMMARY_MD_RE,
        validate_ci_verification=_validate_ci_verification,
        validate_feature_lifecycle_and_freshness=_validate_feature_lifecycle_and_freshness,
        finding_type=Finding,
    )
_validate_worktree_session = partial(
    _repo_helpers.validate_worktree_session,
    load_json=_load_json,
    finding_type=Finding,
)
_validate_token_budgets = partial(
    _config_policy_helpers.validate_token_budgets,
    default_token_budgets=DEFAULT_TOKEN_BUDGETS,
    iter_feature_dirs=_iter_feature_dirs,
    iter_quick_dirs=_iter_quick_dirs,
    iter_research_dirs=_iter_research_dirs,
    iter_ideas_dirs=_iter_ideas_dirs,
    word_count=_word_count,
    finding_type=Finding,
)
_validate_bootstrap_context = partial(
    _config_policy_helpers.validate_bootstrap_context,
    default_bootstrap_context=DEFAULT_BOOTSTRAP_CONTEXT,
    word_count=_word_count,
    finding_type=Finding,
)
_validate_skills = partial(
    _config_policy_helpers.validate_skills,
    iter_skill_paths=_iter_skill_paths,
    parse_skill_frontmatter=_parse_skill_frontmatter,
    finding_type=Finding,
)
validate_repo = partial(
    _repo_helpers.validate_repo,
    load_workflow_config=_load_workflow_config,
    validate_workflow_config=_validate_workflow_config,
    detect_repo_shape=_detect_repo_shape,
    get_monorepo_scope_level=_get_monorepo_scope_level,
    get_operating_principles_level=_get_operating_principles_level,
    get_tdd_mode_level=_get_tdd_mode_level,
    get_verification_before_completion_level=_get_verification_before_completion_level,
    get_two_stage_review_level=_get_two_stage_review_level,
    packages_from_cfg=_packages_from_cfg,
    freshness_cfg=_freshness_cfg,
    token_budgets_cfg=_token_budgets_cfg,
    bootstrap_context_cfg=_bootstrap_context_cfg,
    require=_require,
    validate_memory_runtime=_validate_memory_runtime,
    build_touched=_repo_helpers.build_touched_predicate,
    is_git_repo=_is_git_repo,
    staged_files=_staged_files,
    validate_features=_validate_features,
    validate_quick_tasks=_validate_quick_tasks,
    validate_research=_validate_research,
    validate_shape_artifacts=_validate_shape_artifacts,
    validate_worktree_session=_validate_worktree_session,
    validate_token_budgets=_validate_token_budgets,
    validate_bootstrap_context=_validate_bootstrap_context,
    validate_skills=_validate_skills,
    finding_type=Finding,
)
_finding_to_warning = _baseline_helpers.finding_to_warning
save_baseline = _baseline_helpers.save_baseline
load_baseline = _baseline_helpers.load_baseline
_save_latest = _baseline_helpers.save_latest


def diff_baselines(
    baseline: list[dict[str, Any]], current: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    return _baseline_helpers.diff_baselines(baseline, current)


def main() -> int:
    parser = _cli_helpers.build_parser()
    args = parser.parse_args()
    return _cli_helpers.run_cli(
        args,
        repo_root=_repo_root,
        validate_repo=validate_repo,
        finding_to_warning=_finding_to_warning,
        save_baseline=save_baseline,
        load_baseline=load_baseline,
        diff_baselines=diff_baselines,
        save_latest=_save_latest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
