# 📚 local-rag-assistant

**A privacy-first, fully local document knowledge assistant.**  
Ask questions about your own documents — PDF, images (OCR), audio/video transcription, YouTube subtitles — without sending a single byte to an external API.

> Internal codename: *kamikaze* (retired)

---

## ✨ Features

| Feature | Detail |
|---------|--------|
| **Fully local inference** | LLM runs via [Ollama](https://ollama.com) on your machine |
| **Local embeddings** | `nomic-embed-text` through Ollama — zero external embedding API calls |
| **Multimodal ingestion** | PDF · plain text / Markdown · image OCR (Tesseract) · audio & video (faster-whisper) · YouTube (subtitle API → Whisper fallback) |
| **ChromaDB vector store** | Persistent local vector DB; no cloud required |
| **CHAT mode** | Streaming Q&A with source citations |
| **REPORT mode** | One-shot structured analysis + PDF export |
| **Multi-session management** | Multiple named chat sessions, persisted as local JSON |
| **Cloud LLM opt-in** | Anthropic Claude can replace the local LLM if needed (disabled by default) |

---

## 🏗️ Design philosophy

The constraint that drove every architecture decision was: **confidential documents must not leave the machine**.

Working backwards from that constraint:

- **LLM** → Ollama (local inference server)
- **Embeddings** → `nomic-embed-text` via Ollama (no embedding API calls)
- **Vector DB** → ChromaDB with a local persistence directory
- **OCR** → Tesseract (local binary)
- **Audio transcription** → faster-whisper (local model weights)

The result is a system where the data pipeline from ingestion to answer generation is entirely air-gapped from the internet by default.

---

## 🚀 Quick start

### 1. Install Ollama and pull models

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:7b          # default LLM
ollama pull nomic-embed-text    # embedding model (required)
```

### 2. Clone and install

```bash
git clone https://github.com/<your-username>/local-rag-assistant.git
cd local-rag-assistant
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env if you want to change the model or data directory
```

### 4. Run

```bash
streamlit run src/localrag/ui/app.py
```

Open http://localhost:8501, press **Start / Restart system** in the sidebar, then drop a document into the **Document library** section.

---

## 🎬 Demo (sample data)

`data/samples/` contains two neutral synthetic documents:

- `meeting_notes_sample.md` — fictional project kickoff minutes
- `product_manual_sample.pdf` — fictional middleware product manual

To run an end-to-end demo:

1. Start the system (sidebar → **Start / Restart system**)
2. Import the samples: sidebar → **Import folder** (point to `data/samples/`)
3. Ask a question in **Chat** mode, e.g.:  
   *"What are the action items from the kickoff meeting?"*  
   *"How do I configure the DataBridge Connector?"*

---

## 🧪 Running tests

Tests run **without Ollama, Tesseract, or ffmpeg** installed. LLM and embeddings are replaced by deterministic fakes.

```bash
pip install -e ".[dev]"
pytest
```

Expected: **15 passed**.

---

## ⚙️ Optional dependencies

| Capability | Package | System dependency |
|-----------|---------|-------------------|
| Image OCR | `pytesseract` | `tesseract-ocr` binary |
| Audio / video | `faster-whisper` | — (model downloaded on first use) |
| YouTube audio fallback | `yt-dlp` | `ffmpeg` binary |
| Cloud LLM | `langchain-anthropic` | `ANTHROPIC_API_KEY` in `.env` |

If a system dependency is missing, that ingestion type is **skipped gracefully**; the rest of the pipeline continues.

---

## 📁 Project layout

```
local-rag-assistant/
├── src/localrag/
│   ├── config.py              # pydantic-settings typed Settings
│   ├── ingestion/             # loaders: PDF, OCR, Whisper, YouTube
│   ├── rag/                   # chunking, embeddings, LLM, ChromaDB, pipeline
│   ├── session/               # JSON-based chat session persistence
│   └── ui/                    # Streamlit entry point
├── data/
│   └── samples/               # neutral synthetic demo documents
├── tests/                     # pytest suite (Fake LLM + Fake Embedder)
├── docs/
│   └── architecture.md        # Mermaid architecture diagram
├── .env.example
└── pyproject.toml
```

---

## 🔒 Privacy guarantee

When `USE_CLOUD_LLM=false` (default):

- No document text leaves your machine
- No embedding vectors are sent externally
- ChromaDB stores all vectors locally
- The only outbound traffic is Ollama serving on `localhost`

When `USE_CLOUD_LLM=true`: query text is sent to the Anthropic API. **Embeddings remain local regardless.**

---

## 📄 License

MIT — see [LICENSE](LICENSE).
