"""ChromaDB wrapper — local persistent vector store."""

from __future__ import annotations

from pathlib import Path
from typing import List

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


class VectorStore:
    def __init__(
        self,
        embedding_function,
        persist_directory: str | Path = "data/chroma_db",
        collection_name: str = "localrag",
    ) -> None:
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        self._store = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=embedding_function,
            collection_name=collection_name,
        )

    def add_documents(self, documents: List[Document]) -> None:
        if documents:
            self._store.add_documents(documents)

    def as_retriever(self, k: int = 5):
        return self._store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k},
        )

    def count(self) -> int:
        try:
            return self._store._collection.count()
        except Exception:
            return 0

    def clear(self, collection_name: str, embedding_function, persist_directory: str | Path) -> None:
        try:
            self._store.delete_collection()
        except Exception:
            pass
        self._store = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=embedding_function,
            collection_name=collection_name,
        )
