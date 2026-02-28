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


def test_coverage_report(repo_path: Path | str) -> dict[str, Any]:
    """Generate a test coverage report by walking CALLS edges from test symbols.

    Args:
        repo_path: Path to the repository root.

    Returns:
        Dict with keys:
            enabled: True if graph was available.
            covered_symbols, uncovered_symbols, coverage_by_file, summary.
        On failure:
            enabled: False, error: str describing the failure.
    """
    try:
        graph = ContextGraph(repo_path=repo_path)
        try:
            result = graph.test_coverage()
            return {"enabled": True, **result}
        finally:
            graph.close()
    except Exception as e:
        return {"enabled": False, "error": str(e)}


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

            suggestions = list(seen.values())
            # auto_populate: top files sorted by confidence descending
            auto_populate = sorted(suggestions, key=lambda s: s["confidence"], reverse=True)

            return {
                "enabled": True,
                "suggestions": suggestions,
                "auto_populate": auto_populate,
            }
        finally:
            graph.close()

    except Exception as e:
        return {"enabled": False, "error": str(e)}


def enrich_context(
    repo_path: Path | str,
    keywords: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Discover related code and architecture for context enrichment.

    Args:
        repo_path: Path to the repository root.
        keywords: Keywords to search for in the graph.
        limit: Maximum search results per keyword.

    Returns:
        Dict with keys:
            enabled: True if graph was available.
            related_code: List of {path, name, label, relationship, confidence, node_id}.
            architecture: {communities_hint: int}.
        On failure:
            enabled: False, error: str.
    """
    try:
        graph = ContextGraph(repo_path=repo_path)
        try:
            graph.index()

            seen: dict[str, dict[str, Any]] = {}  # node_id -> entry
            files_touched: set[str] = set()

            for kw in keywords or []:
                results = graph.search(kw, limit=limit)
                for node, score in results:
                    if node.id in seen:
                        continue
                    # Add the matched node itself
                    seen[node.id] = {
                        "path": node.file_path,
                        "name": node.name,
                        "label": node.label.value if hasattr(node.label, "value") else str(node.label),
                        "relationship": "self",
                        "confidence": 1.0,
                        "node_id": node.id,
                    }
                    if node.file_path:
                        files_touched.add(node.file_path)

                    # Get context neighborhood
                    try:
                        ctx = graph.context(node.id)
                    except ValueError:
                        continue

                    for rel_key, rel_label in [
                        ("callers", "caller"),
                        ("callees", "callee"),
                        ("importers", "importer"),
                        ("imports", "import"),
                        ("parent_classes", "parent_class"),
                        ("child_classes", "child_class"),
                    ]:
                        for related_node in ctx.get(rel_key, []):
                            if related_node.id in seen:
                                continue
                            seen[related_node.id] = {
                                "path": related_node.file_path,
                                "name": related_node.name,
                                "label": related_node.label.value if hasattr(related_node.label, "value") else str(related_node.label),
                                "relationship": rel_label,
                                "confidence": 1.0,
                                "node_id": related_node.id,
                            }
                            if related_node.file_path:
                                files_touched.add(related_node.file_path)

            return {
                "enabled": True,
                "related_code": list(seen.values()),
                "architecture": {
                    "communities_hint": len(files_touched),
                },
            }
        finally:
            graph.close()

    except Exception as e:
        return {"enabled": False, "error": str(e)}


def validate_scope(
    repo_path: Path | str,
    declared_files: list[str],
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    """Validate that changes stay within declared file scope.

    Args:
        repo_path: Path to the repository root.
        declared_files: Files declared in the task scope.
        changed_files: Files actually changed (defaults to declared_files).

    Returns:
        Dict with keys:
            enabled, within_scope, declared, changed, blast_radius,
            violations, warnings.
        On failure:
            enabled: False, error: str.
    """
    if changed_files is None:
        changed_files = list(declared_files)

    try:
        graph = ContextGraph(repo_path=repo_path)
        try:
            graph.index()

            impact = graph.review_impact(changed_files)

            declared_set = set(declared_files)
            blast_radius: list[dict[str, Any]] = []
            violations: list[dict[str, Any]] = []
            warnings: list[dict[str, Any]] = []

            for sym in impact.get("affected_symbols", []):
                path = sym.get("file_path", "")
                if not path:
                    continue
                blast_radius.append({
                    "path": path,
                    "symbols": sym.get("name", ""),
                    "depth": sym.get("depth", 0),
                })

            # Check affected files against declared scope
            for affected_path in impact.get("affected_files", []):
                if affected_path in declared_set:
                    continue
                # Check confidence for this edge
                confidence = _get_affected_confidence(
                    graph, affected_path, changed_files
                )
                if confidence <= 0.5:
                    warnings.append({
                        "path": affected_path,
                        "confidence": confidence,
                        "low_confidence": True,
                    })
                else:
                    violations.append({
                        "path": affected_path,
                        "reason": f"affected by changes to {', '.join(changed_files)} but not in declared scope",
                    })

            within_scope = len(violations) == 0

            return {
                "enabled": True,
                "within_scope": within_scope,
                "declared": list(declared_files),
                "changed": list(changed_files),
                "blast_radius": blast_radius,
                "violations": violations,
                "warnings": warnings,
            }
        finally:
            graph.close()

    except Exception as e:
        return {"enabled": False, "error": str(e)}


def contract_warnings(
    repo_path: Path | str,
    changed_files: list[str],
) -> dict[str, Any]:
    """Detect API contract breaks in changed files and find affected callers.

    Follows same graceful degradation pattern as suggest_scope, validate_scope,
    and enrich_context.

    Args:
        repo_path: Path to the repository root.
        changed_files: File paths that were changed.

    Returns:
        Dict with keys:
            enabled: True if graph was available and indexed.
            breaks: List of {symbol, old_signature, new_signature, change_type, callers}.
            summary: {total_breaks, total_affected_callers}.
        On failure:
            enabled: False, error: str.
    """
    try:
        graph = ContextGraph(repo_path)
        if not graph.is_indexed():
            graph.close()
            return {"enabled": False, "error": "Graph not indexed"}
        result = graph.contract_check(changed_files)
        graph.close()
        return {"enabled": True, **result}
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def prioritize_context(
    repo_path: Path | str,
    focal_symbols: list[str] | None = None,
    max_files: int = 20,
) -> dict[str, Any]:
    """Rank files by graph proximity from focal symbols.

    Args:
        repo_path: Path to the repository root.
        focal_symbols: Symbol names to use as BFS seeds.
        max_files: Maximum number of files to return (default 20).

    Returns:
        Dict with keys:
            enabled: True if graph was available and indexed.
            ranked_files: List of {path, distance, reason} dicts.
            focal_symbols_resolved: The focal_symbols list used.
        On failure:
            enabled: False, error: str.
    """
    try:
        graph = ContextGraph(repo_path)
        if not graph.is_indexed():
            graph.close()
            return {"enabled": False, "error": "Graph not indexed"}
        ranked = graph.prioritize_files(focal_symbols or [], max_files)
        graph.close()
        return {
            "enabled": True,
            "ranked_files": [
                {
                    "path": r["file_path"],
                    "distance": r["min_distance"],
                    "reason": f"graph distance {r['min_distance']}",
                }
                for r in ranked
            ],
            "focal_symbols_resolved": focal_symbols or [],
        }
    except Exception as e:
        return {"enabled": False, "error": str(e)}


def _get_affected_confidence(
    graph: Any, affected_path: str, changed_files: list[str]
) -> float:
    """Get the confidence of the edge linking affected_path to changed files."""
    try:
        changed_set = set(changed_files)
        for node in graph.nodes_in_file(affected_path):
            callers = graph.callers_with_confidence(node.id)
            for caller, conf in callers:
                if caller.file_path in changed_set:
                    return conf
            # Check outgoing calls too
            for callee in graph.callees(node.id):
                if callee.file_path in changed_set:
                    # Get confidence from relationship
                    for c, conf in graph.callers_with_confidence(callee.id):
                        if c.id == node.id:
                            return conf
    except Exception:
        pass
    return 1.0


def _get_edge_confidence(graph: Any, node: Any, source_file: str) -> float:
    """Extract confidence score for the edge connecting node to source_file.

    Checks callers_with_confidence for CALLS edges that carry explicit
    confidence values. Falls back to 1.0 if no confidence data is stored.
    """
    try:
        for caller_node, confidence in graph.callers_with_confidence(node.id):
            if caller_node.file_path == source_file or caller_node.id == node.id:
                return confidence
        # Check if this node is a caller of something in source_file
        # by looking at reverse direction
        for callee in graph.callees(node.id):
            if callee.file_path == source_file:
                for caller, conf in graph.callers_with_confidence(callee.id):
                    if caller.id == node.id:
                        return conf
    except Exception:
        pass
    return 1.0
