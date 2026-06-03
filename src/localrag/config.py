from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    embedding_model: str = "nomic-embed-text"

    # Storage
    data_dir: str = "data"
    chroma_collection: str = "localrag"

    # Retrieval
    retrieval_top_k: int = 5
    chunk_size: int = 600
    chunk_overlap: int = 80

    # Whisper
    whisper_model: str = "small"

    # Logging
    log_level: str = "INFO"

    # Cloud LLM (opt-in, default OFF — embedding stays local regardless)
    use_cloud_llm: bool = False
    anthropic_api_key: str = ""
    cloud_llm_model: str = "claude-3-5-sonnet-20241022"

    @property
    def chroma_db_path(self) -> Path:
        return Path(self.data_dir) / "chroma_db"

    @property
    def sessions_dir(self) -> Path:
        return Path(self.data_dir) / "chat_sessions"

    @property
    def documents_dir(self) -> Path:
        return Path(self.data_dir) / "documents"

    @property
    def indexed_files_path(self) -> Path:
        return Path(self.data_dir) / "indexed_files.json"


settings = Settings()
