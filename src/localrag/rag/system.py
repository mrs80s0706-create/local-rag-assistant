"""
RAGSystem — thin facade that wires VectorStore + RAGPipeline + LLM + Embedder.

All prompt logic lives in pipeline.py. This class holds no domain-specific
text or instructions; it only manages component lifecycle and delegates to
the appropriate module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator, List

from langchain_core.documents import Document

from .chunking import split_documents
from .embeddings import make_ollama_embedder
from .llm import make_llm
from .pipeline import RAGPipeline
from .vectorstore import VectorStore


class RAGSystem:
    def __init__(
        self,
        llm_model: str = "qwen2.5:7b",
        embedding_model: str = "nomic-embed-text",
        ollama_url: str = "http://localhost:11434",
        db_path: str | Path = "data/chroma_db",
        collection_name: str = "localrag",
        retrieval_top_k: int = 5,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
        use_cloud_llm: bool = False,
        cloud_llm_model: str = "claude-3-5-sonnet-20241022",
        anthropic_api_key: str = "",
    ) -> None:
        self._db_path = Path(db_path)
        self._collection_name = collection_name
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

        self._embedder = make_ollama_embedder(
            model=embedding_model,
            base_url=ollama_url,
        )
        self._llm = make_llm(
            use_cloud=use_cloud_llm,
            ollama_model=llm_model,
            ollama_url=ollama_url,
            cloud_model=cloud_llm_model,
            api_key=anthropic_api_key,
        )
        self._vectorstore = VectorStore(
            embedding_function=self._embedder,
            persist_directory=self._db_path,
            collection_name=collection_name,
        )
        self._pipeline = RAGPipeline(
            vectorstore=self._vectorstore,
            llm=self._llm,
        )
        # Apply configured top-k
        self._pipeline.update_retriever(self._vectorstore, k=retrieval_top_k)

    # ── Document ingestion ─────────────────────────────────────────────────

    def add_documents(self, documents: List[Document]) -> int:
        """Chunk and index documents. Returns number of chunks added."""
        if not documents:
            return 0
        chunks = split_documents(documents, self._chunk_size, self._chunk_overlap)
        if chunks:
            self._vectorstore.add_documents(chunks)
        return len(chunks)

    # ── Query ──────────────────────────────────────────────────────────────

    def query(self, question: str, direct_context: str = "") -> dict:
        return self._pipeline.query(question, direct_context)

    def stream_query(self, question: str, direct_context: str = "") -> Generator[str, None, None]:
        yield from self._pipeline.stream_query(question, direct_context)

    def get_sources(self, question: str) -> List[Document]:
        return self._pipeline.get_sources(question)

    # ── DB management ─────────────────────────────────────────────────────

    def get_document_count(self) -> int:
        return self._vectorstore.count()

    def clear_database(self) -> None:
        self._vectorstore.clear(
            collection_name=self._collection_name,
            embedding_function=self._embedder,
            persist_directory=self._db_path,
        )
        self._pipeline.update_retriever(self._vectorstore)
