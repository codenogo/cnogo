# Context: O(n^2) Coupling Optimization

## Problem

`coupling.py` computes pairwise Jaccard similarity across all symbol nodes using an O(n^2) nested loop. For n symbols, this means n*(n-1)/2 comparisons. Most pairs share zero neighbors and are skipped immediately, but the iteration itself dominates runtime for large codebases.

## Decision: Inverted-Index Candidate Pruning

Replace the O(n^2) loop with an inverted-index approach:

1. Build `neighbor_to_symbols: dict[str, set[str]]` — maps each neighbor to the set of symbols that reference it.
2. Generate candidate pairs from co-occurrence in posting lists — only pairs sharing >= 1 neighbor.
3. Compute Jaccard similarity only for candidate pairs using the existing `neighbor_sets` dict.

Complexity drops from O(n^2) to O(E + C) where E = total edges and C = candidate pairs with shared neighbors (typically C << n^2).

## API Stability

- `compute_coupling()` signature unchanged
- `CouplingResult` dataclass unchanged
- Result ordering (descending strength) preserved
- `COUPLED_WITH` relationship creation unchanged

## Constraints

- Python stdlib only
- Existing 14 tests in `test_context_coupling.py` must pass unchanged
- Purely internal optimization — no behavior change

## Related Code

- `.cnogo/scripts/context/phases/coupling.py` — target file
- `tests/test_context_coupling.py` — regression suite
- `.cnogo/scripts/context/__init__.py` — `coupling()` API method
- `.cnogo/scripts/context/storage.py` — `get_all_callable_nodes()`, `get_all_relationships_by_types()`
