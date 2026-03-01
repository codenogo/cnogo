"""Search engines for the context graph: BM25 full-text and fuzzy matching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rank_bm25 import BM25Okapi

from scripts.context.model import GraphNode, NodeLabel
from scripts.context.storage import GraphStorage


@dataclass
class SearchResult:
    """A single search result with provenance."""
    node_id: str
    name: str
    score: float
    source: str  # "bm25", "fuzzy", "semantic", or "hybrid"


class BM25Search:
    """BM25 full-text search over symbol nodes.

    Indexes symbol names, signatures, and content (first 500 chars).
    Uses rank-bm25 BM25Okapi for scoring.
    """

    def __init__(self) -> None:
        self._corpus: list[list[str]] = []  # tokenized documents
        self._node_map: list[GraphNode] = []  # parallel array of nodes
        self._bm25: BM25Okapi | None = None

    def build_index(self, storage: GraphStorage) -> None:
        """Build BM25 index from all symbol nodes in storage."""
        nodes = storage.get_all_symbol_nodes()
        self._corpus = []
        self._node_map = []

        for node in nodes:
            # Combine name + signature + content snippet as document
            text = f"{node.name} {node.signature} {node.content[:500]}"
            tokens = self._tokenize(text)
            self._corpus.append(tokens)
            self._node_map.append(node)

        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Search for nodes matching query. Returns SearchResult list sorted by score desc."""
        if not self._bm25 or not self._corpus:
            return []

        tokens = self._tokenize(query)
        scores = self._bm25.get_scores(tokens)

        # Pair (score, node), filter zeros, sort desc
        scored = [(scores[i], self._node_map[i]) for i in range(len(scores)) if scores[i] > 0]
        scored.sort(key=lambda x: -x[0])

        results = []
        for score, node in scored[:limit]:
            results.append(SearchResult(
                node_id=node.id,
                name=node.name,
                score=float(score),
                source="bm25",
            ))
        return results

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenization."""
        return text.lower().split()


class FuzzySearch:
    """Fuzzy string matching search on symbol names.

    Uses difflib.SequenceMatcher for approximate matching.
    """

    def __init__(self, threshold: float = 0.4) -> None:
        self._threshold = threshold
        self._nodes: list[GraphNode] = []

    def build_index(self, storage: GraphStorage) -> None:
        """Load all symbol nodes for fuzzy matching."""
        self._nodes = storage.get_all_symbol_nodes()

    def search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """Fuzzy search symbol names. Returns SearchResult list sorted by score desc."""
        import difflib

        if not self._nodes:
            return []

        query_lower = query.lower()
        scored: list[tuple[float, GraphNode]] = []

        for node in self._nodes:
            # Match against node name
            ratio = difflib.SequenceMatcher(None, query_lower, node.name.lower()).ratio()
            if ratio >= self._threshold:
                scored.append((ratio, node))

        scored.sort(key=lambda x: -x[0])

        results = []
        for score, node in scored[:limit]:
            results.append(SearchResult(
                node_id=node.id,
                name=node.name,
                score=float(score),
                source="fuzzy",
            ))
        return results
