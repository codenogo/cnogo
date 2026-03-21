"""Package-level check execution and verify-ci artifact helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def run_package_checks(
    root: Path,
    packages: list[dict[str, Any]],
    *,
    changed_relpaths: set[str] | None,
    timeout_sec: int,
    output_compaction: dict[str, Any] | None,
    output_recovery: dict[str, Any] | None,
    token_telemetry_enabled: bool,
    default_output_compact_max_lines: int,
    default_output_compact_fail_tail_lines: int,
    default_output_compact_pass_lines: int,
    default_tee_min_chars: int,
    default_tee_max_files: int,
    default_tee_max_file_size: int,
    package_has_changes: Callable[[str, set[str]], bool],
    command_prefers_repo_root: Callable[[str, str], bool],
    is_spotless_not_configured: Callable[[str, str], bool],
    run_shell: Callable[..., tuple[int, str]],
    compact_check_output: Callable[..., tuple[str, str]],
    write_recovery_output: Callable[..., str | None],
    estimate_tokens: Callable[[str], int],
    relative_display_path: Callable[[Path, Path], str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    compact_cfg = output_compaction or {
        "enabled": True,
        "maxLines": default_output_compact_max_lines,
        "failTailLines": default_output_compact_fail_tail_lines,
        "passLines": default_output_compact_pass_lines,
        "dedupe": True,
    }
    recovery_cfg = output_recovery or {
        "enabled": True,
        "mode": "failures",
        "minChars": default_tee_min_chars,
        "maxFiles": default_tee_max_files,
        "maxFileSize": default_tee_max_file_size,
        "directory": ".cnogo/tee",
    }

    for package in packages:
        path = str(package.get("path") or ".")
        kind = str(package.get("kind") or "other")
        name = str(package.get("name") or Path(path).name or path)
        commands = package.get("commands") if isinstance(package.get("commands"), dict) else {}

        pkg_dir = (root / path).resolve()
        pkg_result: dict[str, Any] = {"name": name, "path": path, "kind": kind, "checks": []}
        pkg_changed = True if changed_relpaths is None else package_has_changes(path, changed_relpaths)

        for check_name in ["lint", "typecheck", "test"]:
            command = commands.get(check_name)
            if not isinstance(command, str) or not command.strip():
                pkg_result["checks"].append({"name": check_name, "result": "skipped", "cmd": None})
                continue
            if not pkg_changed:
                pkg_result["checks"].append(
                    {
                        "name": check_name,
                        "result": "skipped",
                        "cmd": command,
                        "reason": "no changed files for package",
                    }
                )
                continue

            check_cwd = root if command_prefers_repo_root(path, command) else pkg_dir
            rc, out = run_shell(command, cwd=check_cwd, timeout_sec=timeout_sec)
            compact_out, reducer = compact_check_output(
                check_name,
                command,
                out,
                rc=rc,
                max_lines=int(compact_cfg.get("maxLines", default_output_compact_max_lines)),
                fail_tail_lines=int(compact_cfg.get("failTailLines", default_output_compact_fail_tail_lines)),
                pass_lines=int(compact_cfg.get("passLines", default_output_compact_pass_lines)),
                dedupe=bool(compact_cfg.get("dedupe", True)),
                enabled=bool(compact_cfg.get("enabled", True)),
            )
            recovery_path = write_recovery_output(
                root,
                out,
                command_slug=f"{name}_{check_name}",
                rc=rc,
                cfg=recovery_cfg,
            )
            input_tokens = estimate_tokens(out)
            output_tokens = estimate_tokens(compact_out)
            saved_tokens = max(0, input_tokens - output_tokens)
            savings_pct = round((saved_tokens * 100.0 / input_tokens), 1) if input_tokens else 0.0
            if not token_telemetry_enabled:
                input_tokens = 0
                output_tokens = 0
                saved_tokens = 0
                savings_pct = 0.0

            result = "pass" if rc == 0 else "fail"
            reason = ""
            if rc != 0 and is_spotless_not_configured(command, out):
                result = "skipped"
                reason = "spotless plugin not configured"

            pkg_result["checks"].append(
                {
                    "name": check_name,
                    "result": result,
                    "cmd": command,
                    "cwd": relative_display_path(check_cwd, root) if check_cwd != root else ".",
                    "reason": reason or None,
                    "exitCode": rc,
                    "output": compact_out,
                    "outputReducer": reducer,
                    "fullOutputPath": recovery_path,
                    "tokenTelemetry": {
                        "inputTokens": input_tokens,
                        "outputTokens": output_tokens,
                        "savedTokens": saved_tokens,
                        "savingsPct": savings_pct,
                    },
                }
            )

        results.append(pkg_result)
    return results


def summarize_checksets(per_pkg: list[dict[str, Any]]) -> dict[str, str]:
    summary = {"lint": "skipped", "typecheck": "skipped", "tests": "skipped"}
    mapping = {"lint": "lint", "typecheck": "typecheck", "test": "tests"}

    for package in per_pkg:
        for check in package.get("checks", []):
            name = check.get("name")
            result = check.get("result")
            if name not in mapping:
                continue
            key = mapping[name]
            if result == "fail":
                summary[key] = "fail"
            elif result == "pass" and summary[key] != "fail":
                summary[key] = "pass"
            elif summary[key] == "skipped" and result == "skipped":
                summary[key] = "skipped"
    return summary


def write_verify_ci(
    root: Path,
    feature: str,
    per_pkg: list[dict[str, Any]],
    invariant_findings: list[Any],
    *,
    now_iso: Callable[[], str],
    summarize_invariants: Callable[[list[Any]], dict[str, int]],
    summarize_token_telemetry: Callable[[list[dict[str, Any]]], dict[str, Any]],
    write_json: Callable[[Path, Any], None],
    write_text: Callable[[Path, str], None],
) -> int:
    base = root / "docs" / "planning" / "work" / "features" / feature
    timestamp = now_iso()
    aggregate = summarize_checksets(per_pkg)
    invariant_summary = summarize_invariants(invariant_findings)
    tokens = summarize_token_telemetry(per_pkg)

    contract = {
        "schemaVersion": 1,
        "feature": feature,
        "timestamp": timestamp,
        "checks": [
            {"name": "lint", "result": aggregate["lint"]},
            {"name": "types", "result": aggregate["typecheck"]},
            {"name": "tests", "result": aggregate["tests"]},
        ],
        "packages": per_pkg,
        "invariants": {
            "summary": invariant_summary,
            "findings": [
                {
                    "rule": finding.rule,
                    "severity": finding.severity,
                    "file": finding.file,
                    "line": finding.line,
                    "message": finding.message,
                }
                for finding in invariant_findings[:200]
            ],
        },
        "tokenTelemetry": tokens,
        "notes": [],
    }
    write_json(base / "VERIFICATION-CI.json", contract)

    md_lines = [
        f"# Verification (CI): {feature}",
        "",
        f"**Timestamp:** {timestamp}",
        "",
        "## Summary",
        "",
        f"- Lint: **{aggregate['lint']}**",
        f"- Types: **{aggregate['typecheck']}**",
        f"- Tests: **{aggregate['tests']}**",
        f"- Invariants: **{invariant_summary['fail']} fail / {invariant_summary['warn']} warn**",
        (
            f"- Token savings: **{tokens['savedTokens']} tokens** "
            f"({tokens['savingsPct']}%, {tokens['checksRun']} checks)"
        ),
        "",
        "## Per-Package Results",
        "",
    ]
    for package in per_pkg:
        md_lines.append(f"### {package['name']} (`{package['path']}`)")
        for check in package.get("checks", []):
            suffix = ""
            if check.get("cmd"):
                cwd = check.get("cwd")
                cwd_part = f", cwd `{cwd}`" if isinstance(cwd, str) and cwd else ""
                suffix = f" (`{check.get('cmd')}`{cwd_part})"
            md_lines.append(f"- {check.get('name')}: **{check.get('result')}**{suffix}")
            telemetry = check.get("tokenTelemetry")
            if isinstance(telemetry, dict) and check.get("result") != "skipped":
                md_lines.append(
                    f"  - tokenTelemetry: in={telemetry.get('inputTokens', 0)} out={telemetry.get('outputTokens', 0)} "
                    f"saved={telemetry.get('savedTokens', 0)} ({telemetry.get('savingsPct', 0.0)}%)"
                )
            full = check.get("fullOutputPath")
            if isinstance(full, str) and full:
                md_lines.append(f"  - full output: `{full}`")
        md_lines.append("")

    if invariant_findings:
        md_lines.append("## Invariant Findings")
        md_lines.append("")
        for finding in invariant_findings[:50]:
            md_lines.append(f"- [{finding.severity}] `{finding.file}:{finding.line}` {finding.message} ({finding.rule})")
        if len(invariant_findings) > 50:
            md_lines.append(f"- ... {len(invariant_findings) - 50} more")
        md_lines.append("")
    write_text(base / "VERIFICATION-CI.md", "\n".join(md_lines).strip() + "\n")

    has_pkg_fail = any(check["result"] == "fail" for package in per_pkg for check in package.get("checks", []))
    return 1 if has_pkg_fail or invariant_summary["fail"] > 0 else 0
