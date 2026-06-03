# Architecture

## System overview

```
[ Ingestion ]
  PDF (PyMuPDF)
  Text / Markdown
  Image OCR (Tesseract)
  Audio / Video (faster-whisper)
  YouTube (subtitle API → Whisper fallback)
        |
        v
[ Chunking ]
  RecursiveCharacterTextSplitter
  chunk_size=600 / chunk_overlap=80
        |
        v
[ Embeddings ]  ← local, no external API
  nomic-embed-text via Ollama (localhost:11434)
        |
        v
[ VectorStore ]
  ChromaDB — persisted to local disk
        |
        v
[ Retriever ]
  similarity search, top-k chunks
        |
        v
[ Prompt builder ]
  context (retrieved chunks) + user question
        |
        v
[ LLM ]  ← local by default, no external API
  qwen2.5:7b via Ollama (localhost:11434)
        |
        v
[ UI — Streamlit ]
  CHAT mode  |  REPORT mode
  Session manager (JSON persistence)
```

---

## Data flow — no external transmission

```
User uploads document
  → DocumentManager.load_file()
      extracts text (PyMuPDF / Tesseract / Whisper)
  → split into chunks
  → OllamaEmbeddings.embed_documents()   [localhost:11434 — no external call]
  → ChromaDB.add()                        [local disk]
  → "Indexed" confirmation to UI

User asks a question
  → OllamaEmbeddings.embed_query()       [localhost:11434 — no external call]
  → ChromaDB similarity_search()          [local disk]
  → top-k chunks returned
  → prompt assembled (chunks + question)
  → Ollama LLM stream()                  [localhost:11434 — no external call]
  → streamed answer + citations → UI
```

---

## Module structure

```
src/localrag/
├── config.py                   # pydantic-settings: all tuneable parameters
├── ingestion/
│   ├── base.py                 # Loader Protocol, FileIndex, load_text_file
│   ├── pdf_loader.py           # PyMuPDF → Documents
│   ├── image_loader.py         # Tesseract OCR → Documents
│   ├── audio_loader.py         # faster-whisper → Documents
│   ├── youtube_loader.py       # transcript API + yt-dlp/Whisper fallback
│   └── manager.py              # DocumentManager: coordinates loaders + index
├── rag/
│   ├── chunking.py             # RecursiveCharacterTextSplitter wrapper
│   ├── embeddings.py           # EmbedderProtocol + OllamaEmbeddings factory
│   ├── llm.py                  # LLMProtocol + Ollama / Cloud LLM factory
│   ├── vectorstore.py          # VectorStore (ChromaDB wrapper)
│   ├── pipeline.py             # RAGPipeline: retrieve → prompt → generate
│   └── system.py               # RAGSystem: thin facade wiring all rag/ modules
├── session/
│   └── store.py                # SessionStore: JSON file per chat session
└── ui/
    └── app.py                  # Streamlit app: sidebar, CHAT mode, REPORT mode
```

---

## Privacy boundary

```
[ Default: USE_CLOUD_LLM=false ]

  Documents
    → Ingestion (local)
    → ChromaDB  (local disk)
    → Ollama    (localhost:11434)
    → Answer
  ✓ Everything stays on your machine. Zero outbound data.

[ Opt-in: USE_CLOUD_LLM=true ]

  Documents
    → Ingestion     (local)
    → ChromaDB      (local disk)
    → Anthropic API (query text sent externally)
    → Answer
  ⚠ Query text is sent to the Anthropic API.
    Embeddings still run via Ollama locally — always.
```

**When `USE_CLOUD_LLM=false` (default):** the dashed arrow does not exist.  
**Embeddings always stay local**, regardless of the `USE_CLOUD_LLM` setting.
