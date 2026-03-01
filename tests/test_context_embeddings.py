"""Tests for the semantic embedding engine."""
from __future__ import annotations

import sys
sys.path.insert(0, ".cnogo")

from pathlib import Path
import pytest

from scripts.context.model import GraphNode, NodeLabel, generate_id
from scripts.context.embeddings import EmbeddingEngine, cosine_similarity, _EMBEDDING_DIM


@pytest.fixture
def engine(tmp_path):
    """Create an EmbeddingEngine with temporary cache dir."""
    return EmbeddingEngine(cache_dir=tmp_path / "models")


# ---------------------------------------------------------------------------
# cosine_similarity tests
# ---------------------------------------------------------------------------


def test_cosine_identical_vectors():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0, abs=1e-6)


def test_cosine_orthogonal_vectors():
    a = [1.0, 0.0, 0.0]
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_empty_vectors():
    assert cosine_similarity([], []) == 0.0


def test_cosine_different_lengths():
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


# ---------------------------------------------------------------------------
# EmbeddingEngine dimension test (no model needed)
# ---------------------------------------------------------------------------


def test_engine_dimension_is_384(engine):
    assert engine.dimension == 384


def test_engine_dimension_matches_constant():
    assert _EMBEDDING_DIM == 384


# ---------------------------------------------------------------------------
# embed_text / embed_batch / embed_nodes
# ---------------------------------------------------------------------------


def test_embed_text_returns_384_dim(engine):
    result = engine.embed_text("hello")
    assert len(result) == 384


def test_embed_text_returns_floats(engine):
    result = engine.embed_text("hello world")
    assert all(isinstance(x, float) for x in result)


def test_embed_batch_multiple_texts(engine):
    texts = ["alpha", "beta", "gamma"]
    results = engine.embed_batch(texts)
    assert len(results) == 3
    for vec in results:
        assert len(vec) == 384


def test_embed_batch_empty_returns_empty(engine):
    assert engine.embed_batch([]) == []


def test_embed_nodes_returns_vectors(engine):
    nodes = [
        GraphNode(
            id=generate_id(NodeLabel.FUNCTION, "foo.py", "bar"),
            label=NodeLabel.FUNCTION,
            name="bar",
            file_path="foo.py",
            signature="def bar(x: int) -> str:",
            content="    return str(x)",
        ),
        GraphNode(
            id=generate_id(NodeLabel.CLASS, "baz.py", "MyClass"),
            label=NodeLabel.CLASS,
            name="MyClass",
            file_path="baz.py",
        ),
    ]
    results = engine.embed_nodes(nodes)
    assert len(results) == 2
    for vec in results:
        assert len(vec) == 384


def test_embed_nodes_uses_signature(engine):
    node_a = GraphNode(
        id=generate_id(NodeLabel.FUNCTION, "a.py", "fn_a"),
        label=NodeLabel.FUNCTION,
        name="fn_a",
        file_path="a.py",
        signature="def fn_a(x: int) -> int:",
    )
    node_b = GraphNode(
        id=generate_id(NodeLabel.FUNCTION, "b.py", "fn_b"),
        label=NodeLabel.FUNCTION,
        name="fn_b",
        file_path="b.py",
        signature="def fn_b(name: str) -> bool:",
    )
    vecs = engine.embed_nodes([node_a, node_b])
    # Different signatures should produce vectors that are not identical
    assert vecs[0] != vecs[1]


def test_similar_texts_high_cosine(engine):
    vec_a = engine.embed_text("python function")
    vec_b = engine.embed_text("python method")
    sim = cosine_similarity(vec_a, vec_b)
    assert sim > 0.5, f"Expected similarity > 0.5, got {sim}"


def test_dissimilar_texts_low_cosine(engine):
    vec_a = engine.embed_text("authentication login")
    vec_b = engine.embed_text("database migration")
    sim_dissimilar = cosine_similarity(vec_a, vec_b)
    vec_c = engine.embed_text("user login authentication")
    sim_similar = cosine_similarity(vec_a, vec_c)
    # Similar pair should score higher than dissimilar pair
    assert sim_similar > sim_dissimilar


def test_lazy_model_loading(tmp_path):
    eng = EmbeddingEngine(cache_dir=tmp_path / "models")
    # Model should be None before any embed call
    assert eng._model is None
    # Trigger loading
    eng.embed_text("trigger")
    # Model should now be loaded
    assert eng._model is not None


def test_custom_cache_dir(tmp_path):
    custom_dir = tmp_path / "custom_models"
    eng = EmbeddingEngine(cache_dir=custom_dir)
    assert eng._cache_dir == custom_dir
    # After embedding, cache dir should exist
    eng.embed_text("test")
    assert custom_dir.exists()
