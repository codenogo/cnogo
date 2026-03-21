"""Research artifact validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_research(
    root: Path,
    findings: list[Any],
    touched: Any,
    *,
    iter_research_dirs: Any,
    require: Any,
    load_json: Any,
    finding_type: Any,
) -> None:
    """Validate research artifact directories."""
    for research_dir in iter_research_dirs(root):
        if not touched(research_dir):
            continue
        research_md = research_dir / "RESEARCH.md"
        research_json = research_dir / "RESEARCH.json"
        if research_md.exists():
            require(research_json, findings, "Missing RESEARCH.json contract for RESEARCH.md")
            if research_json.exists():
                try:
                    contract = load_json(research_json)
                    if not isinstance(contract, dict):
                        findings.append(
                            finding_type("ERROR", "RESEARCH.json must be a JSON object.", str(research_json))
                        )
                    else:
                        if "schemaVersion" not in contract:
                            findings.append(
                                finding_type(
                                    "WARN",
                                    "RESEARCH.json missing schemaVersion (recommended).",
                                    str(research_json),
                                )
                            )
                        sources = contract.get("sources")
                        if sources is not None and not isinstance(sources, list):
                            findings.append(
                                finding_type("WARN", "RESEARCH.json: sources should be an array.", str(research_json))
                            )
                except Exception as exc:
                    findings.append(
                        finding_type("ERROR", f"Failed to parse RESEARCH.json: {exc}", str(research_json))
                    )
