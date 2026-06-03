"""Tests for localrag.rag.vectorstore using in-memory ChromaDB + FakeEmbedder."""

from __future__ import annotations

import uuid

import chromadb
import pytest
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from localrag.rag.vectorstore import VectorStore


@pytest.fixture
def mem_store(fake_embedder):
    """VectorStore backed by a fresh in-memory ChromaDB collection per test."""
    col_name = f"test_{uuid.uuid4().hex}"
    client   = chromadb.EphemeralClient()
    store    = VectorStore.__new__(VectorStore)
    store._db_path        = None
    store._collection_name = col_name
    store._store = Chroma(
        client=client,
        collection_name=col_name,
        embedding_function=fake_embedder,
    )
    return store


def test_empty_store_count(mem_store):
    assert mem_store.count() == 0


def test_add_and_count(mem_store, sample_docs):
    mem_store.add_documents(sample_docs)
    assert mem_store.count() == len(sample_docs)


def test_add_empty_list_is_noop(mem_store):
    mem_store.add_documents([])
    assert mem_store.count() == 0


def test_retriever_returns_documents(mem_store, sample_docs):
    mem_store.add_documents(sample_docs)
    retriever = mem_store.as_retriever(k=2)
    results   = retriever.invoke("installation steps")
    assert len(results) <= 2
    assert all(isinstance(d, Document) for d in results)
