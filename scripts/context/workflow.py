"""Context graph workflow integration functions.

Bridges the context graph with cnogo workflow commands (/plan, /implement,
/discuss) for automatic file scope suggestions, blast-radius validation,
and related code discovery.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.context import ContextGraph


def suggest_scope(
    repo_path: Path | str,
    keywords: list[str] | None = None,
    related_files: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Suggest file scope for a plan based on keyword search and impact analysis.

    Args:
        repo_path: Path to the repository root.
        keywords: Keywords to search for in the graph (symbol names, etc.).
        related_files: File paths to run impact analysis on.
        limit: Maximum number of search results per keyword.

    Returns:
        Dict with keys:
            enabled: True if graph was available.
            suggestions: List of {path, reason, confidence, low_confidence?} dicts.
        On failure:
            enabled: False, error: str describing the failure.
    """
    try:
        graph = ContextGraph(repo_path=repo_path)
        try:
            graph.index()

            seen: dict[str, dict[str, Any]] = {}  # path -> suggestion dict

            # Search for keywords
            for kw in keywords or []:
                results = graph.search(kw, limit=limit)
                for node, score in results:
                    if node.file_path and node.file_path not in seen:
                        seen[node.file_path] = {
                            "path": node.file_path,
                            "reason": f"keyword match: {kw}",
                            "confidence": 1.0,
                        }

            # Impact analysis on related files
            for fpath in related_files or []:
                impacts = graph.impact(fpath, max_depth=3)
                for ir in impacts:
                    node = ir.node
                    if not node.file_path or node.file_path in seen:
                        continue
                    # Check confidence from callers
                    confidence = _get_edge_confidence(graph, node, fpath)
                    suggestion: dict[str, Any] = {
                        "path": node.file_path,
                        "reason": f"impact from {fpath} (depth {ir.depth})",
                        "confidence": confidence,
                    }
                    if confidence <= 0.5:
                        suggestion["low_confidence"] = True
                    seen[node.file_path] = suggestion

            return {
                "enabled": True,
                "suggestions": list(seen.values()),
            }
        finally:
            graph.close()

    except Exception as e:
        return {"enabled": False, "error": str(e)}


def _get_edge_confidence(graph: Any, node: Any, source_file: str) -> float:
    """Extract confidence score for the edge connecting node to source_file.

    Checks callers_with_confidence for CALLS edges that carry explicit
    confidence values. Falls back to 1.0 if no confidence data is stored.
    """
    try:
        callers = graph._storage.get_callers_with_confidence(node.id)
        for caller_node, confidence in callers:
            if caller_node.file_path == source_file or caller_node.id == node.id:
                return confidence
        # Check if this node is a caller of something in source_file
        # by looking at reverse direction
        callees = graph._storage.get_callees(node.id)
        for callee in callees:
            if callee.file_path == source_file:
                # Get confidence from the relationship
                callers_of_callee = graph._storage.get_callers_with_confidence(
                    callee.id
                )
                for caller, conf in callers_of_callee:
                    if caller.id == node.id:
                        return conf
    except Exception:
        pass
    return 1.0
