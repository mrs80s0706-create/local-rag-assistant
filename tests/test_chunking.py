"""Tests for localrag.rag.chunking — pure functions, no external dependencies."""

from __future__ import annotations

from langchain_core.documents import Document

from localrag.rag.chunking import split_documents, make_splitter


def test_split_empty_list():
    assert split_documents([]) == []


def test_split_returns_multiple_chunks():
    doc = Document(page_content="word " * 200, metadata={"source": "test.txt"})
    chunks = split_documents([doc], chunk_size=100, chunk_overlap=10)
    assert len(chunks) > 1


def test_chunks_fit_within_size():
    doc = Document(page_content="x " * 500, metadata={"source": "test.txt"})
    chunk_size = 80
    chunks = split_documents([doc], chunk_size=chunk_size, chunk_overlap=0)
    # allow small tolerance for separator characters
    for c in chunks:
        assert len(c.page_content) <= chunk_size + 20


def test_metadata_preserved():
    meta = {"source": "report.pdf", "page": 3}
    doc  = Document(page_content="a " * 300, metadata=meta)
    chunks = split_documents([doc], chunk_size=50, chunk_overlap=5)
    for c in chunks:
        assert c.metadata["source"] == "report.pdf"


def test_make_splitter_defaults():
    splitter = make_splitter()
    assert splitter._chunk_size == 600
    assert splitter._chunk_overlap == 80


def test_make_splitter_custom():
    splitter = make_splitter(chunk_size=200, chunk_overlap=20)
    assert splitter._chunk_size == 200
    assert splitter._chunk_overlap == 20
