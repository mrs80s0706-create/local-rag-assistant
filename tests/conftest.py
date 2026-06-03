"""
Shared fixtures for the test suite.

All tests run without Ollama, Tesseract, or ffmpeg installed.
External dependencies are replaced with deterministic fakes.
"""

from __future__ import annotations

from typing import Any, List, Optional

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


# ── Fake embedder ──────────────────────────────────────────────────────────

class FakeEmbedder:
    """Deterministic embedder: returns a fixed-length vector derived from text length."""

    DIM = 8

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._vec(text)

    @staticmethod
    def _vec(text: str) -> List[float]:
        seed = len(text) % FakeEmbedder.DIM
        return [(seed + i) / 10.0 for i in range(FakeEmbedder.DIM)]


# ── Fake LLM ───────────────────────────────────────────────────────────────

class FakeLLM(BaseChatModel):
    """Deterministic LLM: echoes the last human message prefixed with 'ANSWER:'.

    Extends BaseChatModel so it is a proper LangChain Runnable and can be
    composed in LCEL chains without wrapping.
    """

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last = messages[-1].content if messages else ""
        text = f"ANSWER: {str(last)[:60]}"
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


# ── Sample documents ───────────────────────────────────────────────────────

@pytest.fixture
def sample_docs() -> List[Document]:
    return [
        Document(
            page_content="The product manual describes installation steps.",
            metadata={"source": "manual.pdf", "page": 1},
        ),
        Document(
            page_content="Chapter 2 covers configuration options in detail.",
            metadata={"source": "manual.pdf", "page": 2},
        ),
        Document(
            page_content="Meeting notes from the project kickoff session.",
            metadata={"source": "meeting_notes.md"},
        ),
    ]


@pytest.fixture
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()
