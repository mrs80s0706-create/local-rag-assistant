"""Embedding interface and local Ollama implementation.

All embeddings run entirely on the local machine via Ollama — no data is
sent to any external API.
"""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from langchain_ollama import OllamaEmbeddings


@runtime_checkable
class EmbedderProtocol(Protocol):
    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, text: str) -> List[float]: ...


def make_ollama_embedder(
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> OllamaEmbeddings:
    """Return an OllamaEmbeddings instance (local, no external API)."""
    return OllamaEmbeddings(model=model, base_url=base_url)
