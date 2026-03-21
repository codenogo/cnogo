"""Runtime/output helpers for workflow checks."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.timestamps import parse_iso_timestamp as _shared_parse_iso_timestamp

DEFAULT_COMMAND_TIMEOUT_SEC = 300
DEFAULT_OUTPUT_COMPACT_MAX_LINES = 120
DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES = 80
DEFAULT_OUTPUT_COMPACT_PASS_LINES = 30
DEFAULT_TEE_MIN_CHARS = 500
DEFAULT_TEE_MAX_FILES = 20
DEFAULT_TEE_MAX_FILE_SIZE = 1_048_576
DEFAULT_COMMAND_USAGE_SINCE_DAYS = 30

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_TEST_SUMMARY_RE = re.compile(
    r"(?i)(test result:|collected\s+\d+|ran\s+\d+\s+tests?|pass(?:ed|ing)|fail(?:ed|ures?)|error(?:s)?|xfailed|xpassed|skipped|duration|time:)"
)
_FAILURE_LINE_RE = re.compile(r"(?i)(fail(?:ed|ure)?|error|exception|traceback|panic|assert|E\s+)")
_LINT_RULE_RE = re.compile(r"(?i)\b([A-Z]{1,4}\d{2,4}|[a-z][a-z0-9_-]{2,})\b")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_shell(cmd: str, cwd: Path, *, timeout_sec: int = DEFAULT_COMMAND_TIMEOUT_SEC) -> tuple[int, str]:
    # WORKFLOW.json is a trusted file (equivalent to Makefile) — shell=True is intentional.
    try:
        out = subprocess.check_output(
            cmd,
            cwd=cwd,
            shell=True,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        ).decode(errors="replace")
        return 0, out
    except subprocess.CalledProcessError as exc:
        out = (exc.output or b"").decode(errors="replace")
        return int(exc.returncode or 1), out
    except subprocess.TimeoutExpired as exc:
        out = (exc.output or b"").decode(errors="replace")
        return 124, f"Command timed out after {timeout_sec}s.\n{out}".strip()
    except FileNotFoundError as exc:
        return 127, str(exc)
    except Exception as exc:
        return 1, str(exc)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def normalize_cmd_text(cmd: str) -> str:
    return " ".join(cmd.strip().split())


def sanitize_slug(text: str, *, max_len: int = 40) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "output"
    return slug[:max_len]


def relative_display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def _append_compact_line(
    ordered: list[str],
    counts: dict[str, int],
    line: str,
    *,
    dedupe: bool,
) -> None:
    text = line.strip()
    if not text:
        return
    if not dedupe:
        ordered.append(text)
        return
    if text in counts:
        counts[text] += 1
        return
    counts[text] = 1
    ordered.append(text)


def _materialize_compact_lines(ordered: list[str], counts: dict[str, int], *, dedupe: bool) -> list[str]:
    if not dedupe:
        return ordered
    out: list[str] = []
    for line in ordered:
        count = counts.get(line, 1)
        out.append(f"{line} (x{count})" if count > 1 else line)
    return out


def _clip_lines(lines: list[str], max_lines: int) -> list[str]:
    if len(lines) <= max_lines:
        return lines
    hidden = len(lines) - max_lines
    return lines[:max_lines] + [f"... +{hidden} more lines"]


def _compact_test_output(
    lines: list[str],
    *,
    max_lines: int,
    fail_tail_lines: int,
    pass_lines: int,
    dedupe: bool,
    rc: int,
) -> tuple[str, str]:
    summary: list[str] = []
    failures: list[str] = []
    keep_context = False
    blank_run = 0

    for raw in lines:
        line = raw.rstrip()
        if _TEST_SUMMARY_RE.search(line):
            summary.append(line.strip())

        if _FAILURE_LINE_RE.search(line):
            failures.append(line.strip())
            keep_context = True
            blank_run = 0
            continue

        if keep_context:
            if not line.strip():
                blank_run += 1
                if blank_run >= 2:
                    keep_context = False
                continue
            if (
                line.startswith((" ", "\t"))
                or line.lstrip().startswith(("at ", "File \"", "...", "Caused by:"))
            ):
                failures.append(line.strip())
                blank_run = 0
                continue
            keep_context = False

    ordered: list[str] = []
    counts: dict[str, int] = {}
    if rc != 0 and failures:
        _append_compact_line(ordered, counts, "FAILURES:", dedupe=False)
        for line in failures:
            _append_compact_line(ordered, counts, line, dedupe=dedupe)
    if summary:
        _append_compact_line(ordered, counts, "SUMMARY:", dedupe=False)
        limit = pass_lines if rc == 0 else max(8, pass_lines // 2)
        for line in summary[:limit]:
            _append_compact_line(ordered, counts, line, dedupe=dedupe)

    if not ordered:
        _append_compact_line(ordered, counts, "OUTPUT (tail):", dedupe=False)
        for line in lines[-fail_tail_lines:]:
            _append_compact_line(ordered, counts, line.strip(), dedupe=dedupe)

    compact_lines = _materialize_compact_lines(ordered, counts, dedupe=dedupe)
    compact_lines = _clip_lines(compact_lines, max_lines)
    return "\n".join(compact_lines).strip(), "failure-focus"


def _compact_lint_output(
    lines: list[str],
    *,
    max_lines: int,
    fail_tail_lines: int,
    pass_lines: int,
    dedupe: bool,
    rc: int,
) -> tuple[str, str]:
    summary: list[str] = []
    findings: list[str] = []
    grouped_rules: dict[str, int] = {}

    for raw in lines:
        line = raw.rstrip()
        low = line.lower()
        if any(token in low for token in ("error", "warning", "failed", "issues", "found", "passed", "success")):
            summary.append(line.strip())
        if _FAILURE_LINE_RE.search(line) or ":" in line:
            findings.append(line.strip())
            match = _LINT_RULE_RE.search(line)
            if match:
                rule = match.group(1).lower()
                if rule not in {"error", "warning", "failed"}:
                    grouped_rules[rule] = grouped_rules.get(rule, 0) + 1

    ordered: list[str] = []
    counts: dict[str, int] = {}
    if grouped_rules:
        _append_compact_line(ordered, counts, "GROUPED FINDINGS:", dedupe=False)
        for rule, count in sorted(grouped_rules.items(), key=lambda item: (-item[1], item[0]))[:10]:
            _append_compact_line(ordered, counts, f"{rule}: {count}", dedupe=False)
    if findings:
        _append_compact_line(ordered, counts, "FINDINGS:", dedupe=False)
        finding_cap = max(10, max_lines // 2)
        for line in findings[:finding_cap]:
            _append_compact_line(ordered, counts, line, dedupe=dedupe)
    if summary:
        _append_compact_line(ordered, counts, "SUMMARY:", dedupe=False)
        limit = pass_lines if rc == 0 else max(8, pass_lines // 2)
        for line in summary[:limit]:
            _append_compact_line(ordered, counts, line, dedupe=dedupe)
    if not ordered:
        _append_compact_line(ordered, counts, "OUTPUT (tail):", dedupe=False)
        for line in lines[-fail_tail_lines:]:
            _append_compact_line(ordered, counts, line.strip(), dedupe=dedupe)

    compact_lines = _materialize_compact_lines(ordered, counts, dedupe=dedupe)
    compact_lines = _clip_lines(compact_lines, max_lines)
    return "\n".join(compact_lines).strip(), "grouped-errors"


def compact_check_output(
    check_name: str,
    cmd: str,
    output: str,
    *,
    rc: int,
    max_lines: int,
    fail_tail_lines: int,
    pass_lines: int,
    dedupe: bool,
    enabled: bool,
) -> tuple[str, str]:
    del cmd  # reducer currently keys off the check type and output, not the command text
    text = strip_ansi(output or "").replace("\r\n", "\n")
    lines = [line for line in text.splitlines() if line.strip()]

    if not enabled:
        tail = lines[-max_lines:] if lines else []
        return "\n".join(tail).strip(), "raw-tail"
    if not lines:
        return "", "empty"

    if check_name == "test":
        return _compact_test_output(
            lines,
            max_lines=max_lines,
            fail_tail_lines=fail_tail_lines,
            pass_lines=pass_lines,
            dedupe=dedupe,
            rc=rc,
        )
    if check_name in {"lint", "typecheck"}:
        return _compact_lint_output(
            lines,
            max_lines=max_lines,
            fail_tail_lines=fail_tail_lines,
            pass_lines=pass_lines,
            dedupe=dedupe,
            rc=rc,
        )

    clipped = _clip_lines(lines, max_lines)
    return "\n".join(clipped).strip(), "tail"


def write_recovery_output(
    root: Path,
    raw_output: str,
    *,
    command_slug: str,
    rc: int,
    cfg: dict[str, Any],
) -> str | None:
    if not cfg.get("enabled", True):
        return None
    mode = str(cfg.get("mode", "failures"))
    if mode == "never":
        return None
    if mode == "failures" and rc == 0:
        return None
    if len(raw_output) < int(cfg.get("minChars", DEFAULT_TEE_MIN_CHARS)):
        return None

    dir_raw = cfg.get("directory", ".cnogo/tee")
    base = Path(str(dir_raw))
    tee_dir = base if base.is_absolute() else (root / base)
    tee_dir.mkdir(parents=True, exist_ok=True)

    max_file_size = int(cfg.get("maxFileSize", DEFAULT_TEE_MAX_FILE_SIZE))
    max_files = int(cfg.get("maxFiles", DEFAULT_TEE_MAX_FILES))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    filename = f"{stamp}_{os.getpid()}_{sanitize_slug(command_slug)}.log"
    path = tee_dir / filename

    content = raw_output
    if len(content) > max_file_size:
        content = content[:max_file_size] + f"\n\n--- truncated at {max_file_size} chars ---"
    path.write_text(content, encoding="utf-8", errors="replace")

    entries = sorted((p for p in tee_dir.glob("*.log") if p.is_file()), key=lambda item: item.name)
    if len(entries) > max_files:
        for old in entries[: len(entries) - max_files]:
            try:
                old.unlink()
            except Exception:
                pass

    return relative_display_path(path, root)


def summarize_token_telemetry(per_pkg: list[dict[str, Any]]) -> dict[str, Any]:
    total_checks = 0
    skipped_checks = 0
    input_tokens = 0
    output_tokens = 0
    saved_tokens = 0

    for pkg in per_pkg:
        for check in pkg.get("checks", []):
            if check.get("result") == "skipped":
                skipped_checks += 1
                continue
            total_checks += 1
            telemetry = check.get("tokenTelemetry")
            if not isinstance(telemetry, dict):
                continue
            input_tokens += int(telemetry.get("inputTokens", 0))
            output_tokens += int(telemetry.get("outputTokens", 0))
            saved_tokens += int(telemetry.get("savedTokens", 0))

    savings_pct = round((saved_tokens * 100.0 / input_tokens), 1) if input_tokens else 0.0
    return {
        "checksRun": total_checks,
        "checksSkipped": skipped_checks,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "savedTokens": saved_tokens,
        "savingsPct": savings_pct,
    }


def parse_iso_timestamp(raw: str) -> datetime | None:
    return _shared_parse_iso_timestamp(raw)


def discover_command_usage(
    root: Path,
    *,
    log_file: str,
    since_days: int,
    limit: int,
) -> dict[str, Any]:
    path = Path(log_file)
    log_path = path if path.is_absolute() else (root / path)
    if not log_path.exists():
        return {
            "logPath": relative_display_path(log_path, root),
            "commandsScanned": 0,
            "optimized": 0,
            "missed": [],
            "unhandled": [],
            "parseErrors": 0,
            "sinceDays": since_days,
        }

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(0, since_days))
    total = 0
    optimized = 0
    parse_errors = 0
    missed_map: dict[str, dict[str, Any]] = {}
    unhandled: dict[str, int] = {}

    for raw_line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except Exception:
            parse_errors += 1
            continue
        if not isinstance(row, dict):
            parse_errors += 1
            continue

        timestamp = parse_iso_timestamp(str(row.get("timestamp") or ""))
        if timestamp is not None and timestamp < cutoff:
            continue

        total += 1
        status = str(row.get("status") or "neutral")
        cmd = normalize_cmd_text(str(row.get("command") or ""))
        if status == "optimized":
            optimized += 1
            continue
        if status == "missed":
            suggestion = str(row.get("suggestion") or "").strip() or "[no suggestion]"
            key = f"{row.get('category', 'other')}::{suggestion}"
            bucket = missed_map.setdefault(
                key,
                {
                    "category": str(row.get("category") or "other"),
                    "suggestion": suggestion,
                    "count": 0,
                    "estimatedSaveableTokens": 0,
                },
            )
            bucket["count"] += 1
            bucket["estimatedSaveableTokens"] += int(row.get("estimatedSaveableTokens") or 0)
            continue

        base = cmd.split(" ", 1)[0] if cmd else "[empty]"
        unhandled[base] = unhandled.get(base, 0) + 1

    missed_all = sorted(
        missed_map.values(),
        key=lambda item: (-int(item["estimatedSaveableTokens"]), -int(item["count"]), str(item["suggestion"])),
    )
    missed = missed_all[:limit]
    unhandled_rows = sorted(
        ({"command": key, "count": value} for key, value in unhandled.items()),
        key=lambda item: (-int(item["count"]), str(item["command"])),
    )[:limit]
    total_saveable = sum(int(item.get("estimatedSaveableTokens", 0)) for item in missed_all)

    return {
        "logPath": relative_display_path(log_path, root),
        "commandsScanned": total,
        "optimized": optimized,
        "optimizedPct": round((optimized * 100.0 / total), 1) if total else 0.0,
        "missed": missed,
        "unhandled": unhandled_rows,
        "estimatedSaveableTokens": total_saveable,
        "parseErrors": parse_errors,
        "sinceDays": since_days,
    }


def print_discover_text(report: dict[str, Any]) -> None:
    print("CNOGO Discover -- Savings Opportunities")
    print("====================================================")
    print(
        f"Scanned: {report.get('commandsScanned', 0)} commands "
        f"(last {report.get('sinceDays', DEFAULT_COMMAND_USAGE_SINCE_DAYS)} days)"
    )
    print(
        f"Already optimized: {report.get('optimized', 0)} "
        f"({report.get('optimizedPct', 0.0)}%)"
    )
    print(f"Command log: {report.get('logPath', '[unknown]')}")
    print("")

    missed = report.get("missed") if isinstance(report.get("missed"), list) else []
    if missed:
        print("MISSED SAVINGS")
        print("----------------------------------------------------")
        for row in missed:
            suggestion = str(row.get("suggestion") or "")
            print(
                f"- {row.get('category', 'other')}: {row.get('count', 0)}x -> "
                f"`{suggestion}` (~{row.get('estimatedSaveableTokens', 0)} tokens)"
            )
        print("----------------------------------------------------")
        print(f"Estimated saveable tokens: ~{report.get('estimatedSaveableTokens', 0)}")
        print("")

    unhandled = report.get("unhandled") if isinstance(report.get("unhandled"), list) else []
    if unhandled:
        print("TOP UNHANDLED COMMANDS")
        print("----------------------------------------------------")
        for row in unhandled:
            print(f"- {row.get('command', '[unknown]')}: {row.get('count', 0)}")
        print("")

    if int(report.get("parseErrors", 0)) > 0:
        print(f"Parse errors: {report.get('parseErrors', 0)}")
