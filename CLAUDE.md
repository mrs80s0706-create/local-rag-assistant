# CLAUDE.md — local-rag-assistant

## Project overview

Privacy-first local document Q&A system. All inference (LLM + embeddings) runs via Ollama on the local machine. No data leaves the machine by default.

Python package: `localrag` | Streamlit UI entry: `src/localrag/ui/app.py`

## Key rules

- **Never write absolute paths** into source code. Use `Path(__file__).parent`, `Settings`, or environment variables.
- **Never commit real documents or data** to the repo. `data/` is git-ignored except `data/samples/`.
- **Never commit `.env`**. Only `.env.example` (with placeholder values) goes to git.
- The `data/samples/` directory holds **neutral synthetic** demo documents only.

## Architecture

```
ingestion/  →  rag/  →  session/  →  ui/
```

- `config.py` — single source of truth for all tuneable settings (via pydantic-settings + `.env`)
- `ingestion/manager.py` — high-level coordinator; individual loaders are in `pdf_loader.py`, `image_loader.py`, `audio_loader.py`, `youtube_loader.py`
- `rag/system.py` — thin facade; all prompt logic lives in `rag/pipeline.py`
- `rag/pipeline.py` — holds `SYSTEM_PROMPT` (generic, domain-neutral)

## Running locally

```bash
ollama pull qwen2.5:7b && ollama pull nomic-embed-text
pip install -e .
cp .env.example .env
streamlit run src/localrag/ui/app.py
```

## Testing (no Ollama required)

```bash
pip install -e ".[dev]"
pytest          # 15 tests, all green
```

LLM and embeddings are replaced by `FakeLLM` / `FakeEmbedder` in `tests/conftest.py`.
ChromaDB uses `EphemeralClient()` with unique collection names per test.

## Adding a new loader

1. Add `src/localrag/ingestion/<name>_loader.py` with a `load_<name>_file(path) -> List[Document]` function.
2. Export it from `src/localrag/ingestion/__init__.py`.
3. Register the file extension in `ingestion/base.py` (`ALL_SUPPORTED` set) and dispatch it in `ingestion/manager.py` (`load_file` method).
4. Add a `@pytest.mark.requires_<name>` test in `tests/`.

## Sensitive string checklist (run before every commit)

```bash
grep -r "kamikaze\|KAMIKAZE" .
grep -rE "C:\\|D:\\" .
grep -r "Satoshi\|Yoshida" .
```

All must return 0 matches (the README "internal codename" line is the only permitted exception for the first pattern).
