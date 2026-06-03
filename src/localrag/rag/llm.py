"""LLM interface and Ollama / cloud implementations.

Default: Ollama (local). Cloud LLM (Anthropic) is opt-in via USE_CLOUD_LLM=true.
Embedding always uses local Ollama regardless of this setting.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama


@runtime_checkable
class LLMProtocol(Protocol):
    def invoke(self, input, **kwargs): ...
    def stream(self, input, **kwargs): ...


def make_ollama_llm(
    model: str = "qwen2.5:7b",
    temperature: float = 0.1,
    base_url: str = "http://localhost:11434",
) -> ChatOllama:
    return ChatOllama(model=model, temperature=temperature, base_url=base_url)


def make_cloud_llm(
    model: str = "claude-3-5-sonnet-20241022",
    api_key: str = "",
    temperature: float = 0.1,
) -> BaseChatModel:
    """Return an Anthropic ChatModel. Requires langchain-anthropic installed."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError as exc:
        raise ImportError(
            "USE_CLOUD_LLM=true requires langchain-anthropic.\n"
            "  pip install 'localrag[cloud]'"
        ) from exc

    if not api_key:
        raise ValueError(
            "USE_CLOUD_LLM=true but ANTHROPIC_API_KEY is not set in .env"
        )
    return ChatAnthropic(model=model, temperature=temperature, api_key=api_key)


def make_llm(
    use_cloud: bool = False,
    ollama_model: str = "qwen2.5:7b",
    ollama_url: str = "http://localhost:11434",
    cloud_model: str = "claude-3-5-sonnet-20241022",
    api_key: str = "",
    temperature: float = 0.1,
) -> BaseChatModel:
    """Factory: returns local Ollama LLM unless use_cloud is True."""
    if use_cloud:
        return make_cloud_llm(model=cloud_model, api_key=api_key, temperature=temperature)
    return make_ollama_llm(model=ollama_model, temperature=temperature, base_url=ollama_url)
