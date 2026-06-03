"""RAG pipeline: retrieve → build prompt → generate.

SYSTEM_PROMPT is intentionally generic — this assistant answers questions
grounded in the documents provided by the user, with no domain assumptions.
"""

from __future__ import annotations

from typing import Generator, List

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

SYSTEM_PROMPT = """You are a helpful document assistant. Answer the user's \
question based on the provided reference materials. Cite the source when \
the answer comes from a specific document.

If the answer is not found in the materials, say so clearly rather than \
guessing. If you make an inference beyond the documents, label it explicitly \
as an inference.

Respond in the same language the user writes in.

[Reference materials]
{context}"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])


def _format_docs(docs: List[Document]) -> str:
    parts = []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        page = d.metadata.get("page")
        loc = f"p.{page}" if page else ""
        header = f"[Source: {src} {loc}]".strip()
        parts.append(f"{header}\n{d.page_content}")
    return "\n\n---\n\n".join(parts)


class RAGPipeline:
    def __init__(self, vectorstore, llm) -> None:
        self._retriever = vectorstore.as_retriever()
        self._llm = llm
        self._chain = self._build_chain()

    def _build_chain(self):
        return (
            {"context": self._retriever | _format_docs, "question": RunnablePassthrough()}
            | PROMPT
            | self._llm
            | StrOutputParser()
        )

    def update_retriever(self, vectorstore, k: int | None = None) -> None:
        self._retriever = vectorstore.as_retriever(k=k) if k else vectorstore.as_retriever()
        self._chain = self._build_chain()

    def query(self, question: str, direct_context: str = "") -> dict:
        sources = self._retriever.invoke(question)
        q = self._inject_context(question, direct_context)
        answer = self._chain.invoke(q)
        return {"answer": answer, "sources": sources}

    def stream_query(self, question: str, direct_context: str = "") -> Generator[str, None, None]:
        q = self._inject_context(question, direct_context)
        yield from self._chain.stream(q)

    def get_sources(self, question: str) -> List[Document]:
        return self._retriever.invoke(question)

    @staticmethod
    def _inject_context(question: str, direct_context: str) -> str:
        if not direct_context:
            return question
        return f"[Priority reference]\n{direct_context}\n\n[Question]\n{question}"
