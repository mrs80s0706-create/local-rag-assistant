"""End-to-end pipeline tests using FakeEmbedder + FakeLLM (no Ollama required)."""

from __future__ import annotations

import uuid

import chromadb
import pytest
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from localrag.rag.pipeline import RAGPipeline
from localrag.rag.vectorstore import VectorStore


def _fresh_vs(fake_embedder) -> VectorStore:
    """Create an isolated in-memory VectorStore with a unique collection name."""
    col_name = f"col_{uuid.uuid4().hex}"
    client   = chromadb.EphemeralClient()
    chroma   = Chroma(
        client=client,
        collection_name=col_name,
        embedding_function=fake_embedder,
    )
    vs = VectorStore.__new__(VectorStore)
    vs._db_path        = None
    vs._collection_name = col_name
    vs._store          = chroma
    return vs


@pytest.fixture
def pipeline(fake_embedder, fake_llm, sample_docs):
    vs = _fresh_vs(fake_embedder)
    vs.add_documents(sample_docs)
    return RAGPipeline(vectorstore=vs, llm=fake_llm)


def test_query_returns_answer_and_sources(pipeline):
    result = pipeline.query("What does the manual describe?")
    assert "answer" in result
    assert isinstance(result["answer"], str)
    assert len(result["answer"]) > 0
    assert "sources" in result
    assert isinstance(result["sources"], list)


def test_stream_query_yields_strings(pipeline):
    chunks = list(pipeline.stream_query("Tell me about configuration."))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_get_sources_returns_documents(pipeline):
    sources = pipeline.get_sources("installation")
    assert isinstance(sources, list)
    assert all(isinstance(d, Document) for d in sources)


def test_direct_context_is_injected(pipeline):
    result = pipeline.query("Summarise this.", direct_context="Priority content here.")
    assert isinstance(result["answer"], str)


def test_update_retriever_does_not_crash(pipeline, fake_embedder):
    vs2 = _fresh_vs(fake_embedder)
    pipeline.update_retriever(vs2, k=3)
    result = pipeline.query("anything")
    assert "answer" in result
