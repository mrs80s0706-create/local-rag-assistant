"""Text chunking utilities — pure functions, no external I/O."""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def make_splitter(chunk_size: int = 600, chunk_overlap: int = 80) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "、", " ", ""],
    )


def split_documents(
    documents: List[Document],
    chunk_size: int = 600,
    chunk_overlap: int = 80,
) -> List[Document]:
    """Split a list of Documents into chunks and return them."""
    if not documents:
        return []
    splitter = make_splitter(chunk_size, chunk_overlap)
    return splitter.split_documents(documents)
