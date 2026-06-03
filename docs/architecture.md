# Architecture

## System overview

```mermaid
flowchart TD
    subgraph Ingestion["📥 Ingestion (local)"]
        PDF["PDF\n(PyMuPDF)"]
        TXT["Text / Markdown"]
        IMG["Image\n(Tesseract OCR)"]
        AUD["Audio / Video\n(faster-whisper)"]
        YT["YouTube\n(subtitle API → Whisper)"]
    end

    subgraph RAG["🔍 RAG Pipeline (local)"]
        CHUNK["Chunking\n(RecursiveCharacterTextSplitter)"]
        EMBED["Embeddings\nnomic-embed-text\nvia Ollama"]
        CHROMA[("ChromaDB\n(local disk)")]
        RETRIEVE["Retriever\n(similarity search, top-k)"]
        PROMPT["Prompt builder\n(context + question)"]
        LLM["LLM\nqwen2.5:7b\nvia Ollama"]
    end

    subgraph UI["🖥️ Streamlit UI"]
        CHAT["CHAT mode\n(streaming Q&A)"]
        REPORT["REPORT mode\n(structured analysis + PDF)"]
        SESSION["Session manager\n(JSON persistence)"]
    end

    PDF & TXT & IMG & AUD & YT --> CHUNK
    CHUNK --> EMBED
    EMBED --> CHROMA
    CHROMA --> RETRIEVE
    RETRIEVE --> PROMPT
    PROMPT --> LLM
    LLM --> CHAT & REPORT
    CHAT & REPORT --> SESSION

    style Ingestion fill:#1a2f1a,stroke:#4a8a4a,color:#ccffcc
    style RAG      fill:#1a1a2f,stroke:#4a4a8a,color:#ccccff
    style UI       fill:#2f1a1a,stroke:#8a4a4a,color:#ffcccc
```

## Data flow — no external transmission

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit UI
    participant Mgr as DocumentManager
    participant VS as VectorStore
    participant Emb as OllamaEmbeddings
    participant LLM as Ollama LLM

    User->>UI: Upload document
    UI->>Mgr: load_file(path)
    Mgr->>Mgr: Extract text (PyMuPDF / Tesseract / Whisper)
    Mgr->>VS: add_documents(chunks)
    VS->>Emb: embed_documents(texts)
    Note over Emb: localhost:11434 — no external call
    Emb-->>VS: vectors
    VS-->>UI: Indexed

    User->>UI: Ask question
    UI->>VS: similarity_search(query)
    VS->>Emb: embed_query(query)
    Emb-->>VS: query vector
    VS-->>UI: top-k chunks
    UI->>LLM: prompt (context + question)
    Note over LLM: localhost:11434 — no external call
    LLM-->>UI: streamed answer
    UI-->>User: Answer + citations
```

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

## Privacy boundary

```mermaid
graph LR
    subgraph local["🔒 Your machine — air-gapped by default"]
        docs["Documents"] --> ingest["Ingestion"]
        ingest --> chromadb["ChromaDB<br/>local disk"]
        chromadb --> ollama["Ollama<br/>localhost:11434"]
        ollama --> answer["Answer"]
    end

    subgraph cloud["☁️ Internet — opt-in only"]
        anthropic["Anthropic API<br/>USE_CLOUD_LLM=true"]
    end

    ollama -.->|opt-in only| anthropic

    style local fill:#0d1f0d,stroke:#2a6a2a,color:#aaffaa
    style cloud fill:#1f0d0d,stroke:#6a2a2a,color:#ffaaaa
```

**When `USE_CLOUD_LLM=false` (default):** the dashed arrow does not exist.  
**Embeddings always stay local**, regardless of the `USE_CLOUD_LLM` setting.
