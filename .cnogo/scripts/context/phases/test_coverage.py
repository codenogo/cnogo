"""Test coverage mapping phase.

Detects test files by path convention and walks CALLS edges from test
file symbols to production symbols to identify which production symbols
are exercised by tests.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from scripts.context.model import NodeLabel, RelType
from scripts.context.storage import GraphStorage


def _is_test_file(file_path: str) -> bool:
    """Return True if file_path looks like a test file."""
    pure = PurePosixPath(file_path)
    name = pure.name
    # Match: test_*.py, *_test.py, or any file under a tests/ directory
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    parts = pure.parts
    if any(part in ("tests", "test") for part in parts[:-1]):
        return True
    return False


def analyze_test_coverage(storage: GraphStorage) -> dict:
    """Analyze test coverage by walking CALLS edges from test file symbols.

    Returns a dict with:
        covered_symbols: list of node IDs of production symbols called from tests.
        uncovered_symbols: list of node IDs of production symbols not called from tests.
        coverage_by_file: dict mapping file_path -> {covered: [...], uncovered: [...]}.
        summary: {total_symbols, covered, uncovered, coverage_pct}.
    """
    assert storage._conn is not None

    # Get all symbol nodes
    all_symbol_nodes = storage.get_all_symbol_nodes()

    # Partition into test nodes and production nodes
    test_node_ids: set[str] = set()
    prod_node_ids: set[str] = set()

    for node in all_symbol_nodes:
        if _is_test_file(node.file_path):
            test_node_ids.add(node.id)
        else:
            prod_node_ids.add(node.id)

    # Walk CALLS edges to find which production symbols are called by test nodes
    covered_ids: set[str] = set()

    if test_node_ids and prod_node_ids:
        # BFS: start from test nodes, follow CALLS edges, collect prod node IDs
        visited: set[str] = set(test_node_ids)
        frontier = list(test_node_ids)

        while frontier:
            # Batch query: find all callees of nodes in the frontier
            placeholders = ",".join("?" * len(frontier))
            cur = storage._conn.execute(
                f"""SELECT r.source, r.target FROM relationships r
                    WHERE r.source IN ({placeholders}) AND r.type = ?""",
                frontier + [RelType.CALLS.value],
            )
            rows = cur.fetchall()

            next_frontier: list[str] = []
            for src, tgt in rows:
                if tgt in visited:
                    continue
                visited.add(tgt)
                if tgt in prod_node_ids:
                    covered_ids.add(tgt)
                # Continue BFS even through production code (transitive coverage)
                next_frontier.append(tgt)

            frontier = next_frontier

    uncovered_ids = prod_node_ids - covered_ids

    # Build coverage_by_file
    coverage_by_file: dict[str, dict[str, list[str]]] = {}
    for node in all_symbol_nodes:
        if node.id not in prod_node_ids:
            continue
        fp = node.file_path
        if fp not in coverage_by_file:
            coverage_by_file[fp] = {"covered": [], "uncovered": []}
        if node.id in covered_ids:
            coverage_by_file[fp]["covered"].append(node.id)
        else:
            coverage_by_file[fp]["uncovered"].append(node.id)

    total = len(prod_node_ids)
    covered_count = len(covered_ids)
    uncovered_count = len(uncovered_ids)
    coverage_pct = (covered_count / total * 100.0) if total > 0 else 0.0

    return {
        "covered_symbols": sorted(covered_ids),
        "uncovered_symbols": sorted(uncovered_ids),
        "coverage_by_file": coverage_by_file,
        "summary": {
            "total_symbols": total,
            "covered": covered_count,
            "uncovered": uncovered_count,
            "coverage_pct": round(coverage_pct, 2),
        },
    }
