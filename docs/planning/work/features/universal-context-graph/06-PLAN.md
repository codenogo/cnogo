# Plan 06: Hybrid search engine: BM25 full-text + BAAI/bge-small-en-v1.5 semantic vectors + fuzzy matching with Reciprocal Rank Fusion

## Goal
Hybrid search engine: BM25 full-text + BAAI/bge-small-en-v1.5 semantic vectors + fuzzy matching with Reciprocal Rank Fusion

## Tasks

### Task 1: BM25 + fuzzy search engine
**Files:** `.cnogo/scripts/context/search.py`, `tests/test_context_search.py`
**Action:**
Create search.py with BM25Search (using rank-bm25 library) for full-text search over symbol names, signatures, and docstrings. Add FuzzySearch using stdlib difflib.SequenceMatcher for approximate name matching. Both return SearchResult objects with score and source attribution.

**Micro-steps:**
- Write failing tests: BM25 search over symbol names/signatures/content returns ranked results; fuzzy search handles typos and partial names
- Implement search.py with BM25Search class using rank-bm25 library: tokenize symbol names, signatures, docstrings; score queries against corpus
- Implement FuzzySearch using difflib.SequenceMatcher (stdlib) for approximate string matching on symbol names
- Define SearchResult dataclass (node_id, score, source) to track which search method produced each result
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_search.py -x -k 'bm25 or fuzzy' 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_search.py -x -k 'bm25 or fuzzy' 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_search.py -v -k 'bm25 or fuzzy' 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Semantic embedding engine
**Files:** `.cnogo/scripts/context/embeddings.py`, `tests/test_context_embeddings.py`
**Action:**
Create embeddings.py with EmbeddingEngine wrapping sentence-transformers using BAAI/bge-small-en-v1.5 (384-dim). Lazy model loading on first use. Model cache at ~/.cache/cnogo/models/. Provides embed_text(text) -> list[float], embed_batch(texts) -> list[list[float]], and cosine_similarity helper. embed_nodes combines symbol name + signature + content snippet for embedding.

**Micro-steps:**
- Write failing tests: embed_text returns 384-dim vector; embed_batch handles multiple texts; model cached at ~/.cache/cnogo/models/
- Implement embeddings.py: EmbeddingEngine class wrapping sentence-transformers with BAAI/bge-small-en-v1.5 model
- Lazy model loading: don't load model until first embed call
- Cache model at ~/.cache/cnogo/models/ (shared across projects)
- Implement cosine_similarity helper for vector comparison
- Add embed_nodes method: embed symbol name + signature + first N lines of content as combined text
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_embeddings.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_embeddings.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_embeddings.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: Hybrid search with Reciprocal Rank Fusion
**Files:** `.cnogo/scripts/context/search.py`, `tests/test_context_search.py`
**Action:**
Add HybridSearch to search.py that combines BM25, semantic, and fuzzy search via Reciprocal Rank Fusion (RRF). RRF score = sum(1/(k+rank_i)) with k=60 (Axon pattern). Stores embedding vectors on graph nodes during indexing. hybrid_search() runs all three rankers in parallel, fuses results, and returns top-k (GraphNode, score) tuples.

**Micro-steps:**
- Write failing tests: hybrid_search combines BM25 + semantic + fuzzy results via RRF; returns correctly fused rankings
- Implement HybridSearch class: takes BM25Search, EmbeddingEngine, FuzzySearch as components
- Implement Reciprocal Rank Fusion: RRF_score = sum(1/(k+rank_i)) across all rankers where k=60
- hybrid_search(query, storage, limit) runs all three searches, fuses results, returns top-k
- Store embedding vectors on GraphNode.embedding field in KuzuDB for vector search
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_search.py -x -k 'hybrid' 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_search.py -x -k 'hybrid' 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_search.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_search.py tests/test_context_embeddings.py -v 2>&1 | tail -10
```

## Commit Message
```
feat(context-graph): hybrid search (BM25 + semantic embeddings + fuzzy + RRF)
```
