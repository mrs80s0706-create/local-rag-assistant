"""
Local RAG Assistant — Streamlit Web UI
"""

from __future__ import annotations

import base64
import io
import json
import platform
import traceback
import urllib.error
import urllib.request
import uuid as _uuid
from datetime import datetime
from pathlib import Path

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from localrag.config import settings
from localrag.ingestion import DocumentManager
from localrag.rag import RAGSystem
from localrag.session import SessionStore

import logging
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent.parent  # repo root
DATA_DIR = settings.data_dir
SESSIONS_DIR = ROOT / DATA_DIR / "chat_sessions"
DOCUMENTS_DIR = ROOT / DATA_DIR / "documents"
IMPORT_BOX_DIR = ROOT / DATA_DIR / "import_box"

# Platform-specific CJK font candidates for PDF generation.
# The first existing path is used; falls back to Helvetica if none found.
FONT_CANDIDATES_WINDOWS = [
    "meiryo.ttc",
    "YuGothB.ttc",
    "msgothic.ttc",
]
FONT_CANDIDATES_UNIX = [
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
]

# ── Cached static assets ───────────────────────────────────────────────────

@st.cache_data
def _bg_image_b64() -> str:
    p = Path(__file__).parent / "static" / "background.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""

@st.cache_data
def _title_image_b64() -> str:
    p = Path(__file__).parent / "static" / "title.png"
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


# ── Page config (must be first Streamlit call) ─────────────────────────────

st.set_page_config(
    page_title="Local RAG Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

for _k, _v in {
    "show_file_list": False,
    "is_processing": False,
    "pending_action": None,
    "action_error": "",
    "action_info": "",
    "action_success": "",
    "yt_url_counter": 0,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# =============================================================================
# CSS
# =============================================================================

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;600&family=Noto+Sans+JP:wght@300;400;500&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

:root {
    --navy:        #080F1A;
    --navy-card:   #0E1C2F;
    --navy-light:  #132640;
    --gold:        #C9A84C;
    --gold-light:  #E2C472;
    --gold-dim:    rgba(201,168,76,0.10);
    --gold-border: rgba(201,168,76,0.20);
    --gold-border2:rgba(201,168,76,0.35);
    --text:        #EDE8DF;
    --text-sub:    #8B9EBA;
    --text-muted:  #3E5068;
    --serif:       'Noto Serif JP','Yu Mincho','MS Mincho',Georgia,serif;
    --sans:        'Noto Sans JP','Meiryo','Yu Gothic','Segoe UI',sans-serif;
}

* { box-sizing: border-box; }
html { background-color: var(--navy) !important; scrollbar-gutter: stable; overflow-y: scroll; }
body { background-color: var(--navy) !important; }

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
section[data-testid="stMain"],
section[data-testid="stMain"] > div,
[data-testid="stMainBlockContainer"],
[data-testid="stChatMessageContainer"],
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div {
    background-color: transparent !important;
    background-image: none !important;
}
.stApp [data-testid="stBottom"],
.stApp [data-testid="stBottom"] > div,
.stApp [data-testid="stBottom"] > div > div,
.stApp [data-testid="stBottomBlockContainer"],
.stApp [data-testid="stBottomBlockContainer"] > div,
.stApp [data-testid="stBottomBlockContainer"] * {
    background: transparent !important; box-shadow: none !important; backdrop-filter: none !important;
}

.main .block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 0rem !important; padding-bottom: 1rem !important;
    padding-left: 2rem !important; padding-right: 2rem !important;
    max-width: 880px !important; overflow-x: hidden !important; width: 100% !important;
}
[data-testid="stImage"] { margin-top: 0 !important; margin-bottom: 0 !important; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important; height: 0 !important; min-height: 0 !important;
    padding: 0 !important; overflow: visible !important;
}
[data-testid="stToolbar"] { top: 30px !important; }
section[data-testid="stMain"] { padding-bottom: 2rem !important; }
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stDeployButton"], [data-testid="stAppDeployButton"] { display: none !important; }
[data-testid="stToolbar"] button { display: none !important; }
[data-testid="stExpandSidebarButton"] { visibility: visible !important; top: 0.5rem !important; }
[data-testid="stExpandSidebarButton"] button, button[data-testid="stExpandSidebarButton"] {
    display: flex !important; visibility: visible !important;
}
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stExpandSidebarButton"] button {
    color: rgba(201,168,76,0.8) !important;
    transition: color 0.15s ease !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stExpandSidebarButton"] button:hover {
    color: rgba(201,168,76,1) !important;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(5,12,21,0.88) 0%, rgba(7,14,24,0.88) 100%) !important;
    border-right: 1px solid var(--gold-border2) !important;
}
[data-testid="stSidebarHeader"] { padding: 0 !important; min-height: 0 !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }
[data-testid="stSidebar"] .block-container { padding: 0.3rem 1rem 2rem !important; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top: 0.5rem !important; }

h1,h2,h3,h4 { font-family: var(--serif) !important; color: var(--text) !important; font-weight: 400 !important; }
p, div, label { font-family: var(--sans) !important; }

.stButton > button {
    background: transparent !important; border: 1px solid var(--gold-border) !important;
    color: var(--text-sub) !important; border-radius: 2px !important;
    font-family: var(--sans) !important; font-size: 0.76rem !important;
    letter-spacing: 0.04em !important; padding: 0.26rem 0.65rem !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
    white-space: nowrap !important;
}
.stButton > button:hover {
    border-color: var(--gold) !important; color: var(--gold) !important;
    background: var(--gold-dim) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #8A6820 0%, var(--gold) 50%, var(--gold-light) 100%) !important;
    border-color: var(--gold-light) !important; color: #09131E !important; font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(201,168,76,0.12) !important; border: 1px solid rgba(201,168,76,0.50) !important;
    color: var(--gold-light) !important; font-size: 0.72rem !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #8A6820 0%, var(--gold) 50%, var(--gold-light) 100%) !important;
    border: 1px solid var(--gold-light) !important; color: #050C15 !important; font-weight: 700 !important;
}
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #8A6820, var(--gold), var(--gold-light)) !important;
    border: 1px solid var(--gold-light) !important; color: #09131E !important;
    font-weight: 600 !important; width: 100% !important; border-radius: 2px !important;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: var(--navy-card) !important; border: 1px solid var(--gold-border2) !important;
    color: var(--text) !important; border-radius: 2px !important;
    font-family: var(--sans) !important; font-size: 0.86rem !important; caret-color: var(--gold) !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--gold) !important; box-shadow: 0 0 0 1px rgba(201,168,76,0.35) !important;
}
[data-testid="stTextArea"]:focus-within {
    box-shadow: 0 0 0 1px rgba(201,168,76,0.35) !important;
}
[data-testid="stTextArea"] textarea:focus { outline: none !important; }
[data-testid="stSelectbox"] > div > div {
    background-color: var(--navy-card) !important; border: 1px solid var(--gold-border) !important;
    color: var(--text) !important; border-radius: 2px !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(135deg, var(--navy-card), var(--navy-light)) !important;
    border: 1px solid var(--gold-border2) !important; border-top: 2px solid var(--gold) !important;
    border-radius: 3px !important; padding: 0.6rem 0.9rem !important;
}
[data-testid="stMetricValue"] { color: var(--gold) !important; font-size: 1.5rem !important; }
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.66rem !important; }

.stChatMessage {
    background: linear-gradient(135deg, var(--navy-card), #101E33) !important;
    border: 1px solid var(--gold-border) !important; border-left: 2px solid rgba(201,168,76,0.4) !important;
    border-radius: 3px !important; margin-bottom: 0.65rem !important;
}
[data-testid="stChatInput"],
[data-testid="stChatInputContainer"] > div {
    background-color: var(--navy-card) !important; border: 1px solid rgba(201,168,76,0.35) !important;
    border-radius: 3px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--gold) !important; box-shadow: 0 0 0 1px rgba(201,168,76,0.35) !important;
}
[data-testid="stChatInput"] textarea {
    background-color: var(--navy-card) !important; color: var(--text) !important; border: none !important;
}
[data-testid="stChatInput"] textarea:focus { outline: none !important; }
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-sub) !important; }
[data-testid="stChatInput"] button:not(:disabled) { background-color: var(--gold) !important; color: #09131E !important; }

[data-testid="stBottom"] { position: sticky !important; bottom: 0 !important; background: transparent !important; z-index: 100 !important; }
[data-testid="stBottomBlockContainer"] { max-width: 880px !important; padding: 0 2rem !important; background: transparent !important; }
[data-testid="stBottom"] { margin-bottom: 1rem !important; }

[data-testid="stSidebar"] [data-testid="stExpander"] {
    background-color: rgba(14,28,47,0.4) !important;
    border: 1px solid rgba(201,168,76,0.22) !important; border-radius: 4px !important; margin-bottom: 0.8rem !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary {
    background: linear-gradient(135deg, #8A6820 0%, var(--gold) 50%, var(--gold-light) 100%) !important;
    padding: 0.35rem 0.6rem !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] > details > summary [data-testid="stMarkdownContainer"] p {
    color: #0E1C2F !important; font-size: 0.82rem !important; font-weight: 700 !important;
}

.lr-tree-container { max-height: 400px; overflow-y: auto; padding-right: 4px; margin-top: 0.4rem; }
.lr-tree-container details { margin: 0.2rem 0 0.2rem 0.4rem !important; border-left: 1px dotted rgba(201,168,76,0.15) !important; padding-left: 0.2rem !important; }
.lr-tree-container details summary { list-style: none !important; cursor: pointer !important; font-size: 0.78rem !important; color: var(--gold) !important; }
.lr-tree-container .folder-icon::before { content: "📁" !important; }
.lr-tree-container details[open] > summary > .folder-icon::before { content: "📂" !important; }

.session-group-label { color: rgba(201,168,76,0.40); font-size: 0.58rem; letter-spacing: 0.14em; text-transform: uppercase; padding: 0.25rem 0 0.05rem; }
.new-chat-btn .stButton > button { background: rgba(201,168,76,0.12) !important; border: 1px solid rgba(201,168,76,0.50) !important; color: var(--gold-light) !important; }
.chat-search-wrap [data-testid="stTextInput"] input { font-size: 0.82rem !important; }
.search-match-label { color: rgba(201,168,76,0.75); font-size: 0.72rem; letter-spacing: 0.04em; }


::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: var(--navy-light); border-radius: 2px; }
hr { border: none !important; border-top: 1px solid var(--gold-border) !important; margin: 0.6rem 0 !important; }

@keyframes lr-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.lr-spin {
    display: inline-block; width: 16px; height: 16px;
    border: 2px solid rgba(212,175,55,0.15); border-top: 2px solid #D4AF37;
    border-radius: 50%; animation: lr-spin 1.0s infinite linear;
    vertical-align: middle; margin-right: 6px;
}

div[data-testid="InputInstructions"] { display: none !important; }
button:disabled { opacity: 0.4 !important; cursor: not-allowed !important; }
</style>
"""


# =============================================================================
# Utilities
# =============================================================================

def _log(msg: str, level: str = "INFO") -> None:
    getattr(logger, level.lower(), logger.info)(msg)
    logs = st.session_state.setdefault("debug_logs", [])
    ts = datetime.now().strftime("%H:%M:%S")
    logs.append(f"[{ts}][{level}] {msg}")
    if len(logs) > 200:
        st.session_state["debug_logs"] = logs[-200:]


def _validate_history(history: list) -> list:
    return [
        e for e in history
        if (isinstance(e, dict)
            and e.get("role") in ("user", "assistant")
            and isinstance(e.get("content"), str)
            and e["content"].strip())
    ]


def _store() -> SessionStore:
    if "session_store" not in st.session_state:
        st.session_state["session_store"] = SessionStore(SESSIONS_DIR)
    return st.session_state["session_store"]


def prepare_direct_context() -> str:
    selected = st.session_state.get("chat_context_files", [])
    processor: DocumentManager | None = st.session_state.get("processor")
    if not selected or not processor:
        return ""
    parts = []
    for path in selected:
        doc = processor.extract_text(path)
        if doc.get("content"):
            parts.append(
                f"---\n[File: {doc['name']}]\n[Path: {doc['path']}]\n"
                f"{doc['content']}\n---"
            )
    return "\n\n".join(parts)


# =============================================================================
# Session management
# =============================================================================

def _new_session() -> None:
    st.session_state["current_session_id"] = _uuid.uuid4().hex[:12]
    st.session_state["chat_history"]        = []
    st.session_state["session_name"]        = "New chat"
    st.session_state["last_sources"]        = []
    st.session_state["session_rename_id"]   = None


def _switch_session(session_id: str) -> None:
    data = _store().load(session_id)
    messages = data.get("messages", []) if data else []
    name     = data.get("name", "New chat") if data else "New chat"
    st.session_state["current_session_id"] = session_id
    st.session_state["chat_history"]        = messages
    st.session_state["session_name"]        = name
    st.session_state["last_sources"]        = []
    st.session_state["session_rename_id"]   = None


def _save_current_session() -> None:
    sid      = st.session_state.get("current_session_id", "")
    messages = st.session_state.get("chat_history", [])
    if not sid or not messages:
        return
    name = st.session_state.get("session_name", "New chat")
    if name == "New chat":
        name = SessionStore.auto_name(messages)
        st.session_state["session_name"] = name
    _store().save(sid, name, messages)


def _delete_session(session_id: str) -> None:
    _store().delete(session_id)


def _rename_session(session_id: str, new_name: str) -> None:
    _store().rename(session_id, new_name)


def _load_all_sessions() -> list:
    return _store().list_sessions()


def _session_exists(session_id: str) -> bool:
    return (SESSIONS_DIR / f"chat_{session_id}.json").exists()


# =============================================================================
# Ollama connection / RAGSystem init
# =============================================================================

def connect_ollama(model_name: str) -> tuple:
    _log(f"Connecting: model={model_name}, embed={settings.embedding_model}")
    try:
        with urllib.request.urlopen(
            f"{settings.ollama_url}/api/tags", timeout=5
        ) as resp:
            data      = json.loads(resp.read().decode())
            available = [m["name"] for m in data.get("models", [])]
        _log(f"Available models: {available or '(none)'}")
    except urllib.error.URLError as exc:
        reason  = str(getattr(exc, "reason", exc))
        r_lower = reason.lower()
        if "refused" in r_lower or "actively refused" in r_lower:
            hint = "Ollama is not running. Start it with: ollama serve"
        elif "timed out" in r_lower or "timeout" in r_lower:
            hint = "Connection timed out. Ollama may be busy or still starting."
        else:
            hint = f"Check that Ollama is reachable at {settings.ollama_url}."
        msg = (
            f"Cannot connect to Ollama\n"
            f"URL: {settings.ollama_url}\n"
            f"Reason: {reason}\n\n"
            f"Fix: {hint}"
        )
        _log(msg, "ERROR")
        return None, msg
    except Exception as exc:
        msg = f"Unexpected error during Ollama connection: {type(exc).__name__}: {exc}"
        _log(msg, "ERROR")
        return None, msg

    def _model_ok(name: str) -> bool:
        base = name.split(":")[0]
        return name in available or (name + ":latest") in available or any(
            a.split(":")[0] == base for a in available
        )

    missing = [m for m in (model_name, settings.embedding_model) if not _model_ok(m)]
    if missing:
        pull_cmds = "\n".join(f"  ollama pull {m}" for m in missing)
        msg = (
            f"Required models not found: {', '.join(missing)}\n\n"
            f"Download them with:\n{pull_cmds}\n\n"
            f"Available: {', '.join(available) if available else 'none'}"
        )
        _log(msg, "WARN")
        return None, msg

    try:
        rag = RAGSystem(
            llm_model        = model_name,
            embedding_model  = settings.embedding_model,
            ollama_url       = settings.ollama_url,
            db_path          = str(ROOT / DATA_DIR / "chroma_db"),
            collection_name  = settings.chroma_collection,
            retrieval_top_k  = settings.retrieval_top_k,
            chunk_size       = settings.chunk_size,
            chunk_overlap    = settings.chunk_overlap,
            use_cloud_llm    = settings.use_cloud_llm,
            cloud_llm_model  = settings.cloud_llm_model,
            anthropic_api_key= settings.anthropic_api_key,
        )
        _log(f"RAGSystem ready: {rag.get_document_count()} chunks indexed")
        return rag, ""
    except Exception as exc:
        _log(traceback.format_exc(), "ERROR")
        msg = (
            f"RAGSystem init failed: {type(exc).__name__}: {exc}\n\n"
            f"DB path: {ROOT / DATA_DIR / 'chroma_db'}\n"
            f"Try the 'Rebuild index' button to reset the database."
        )
        return None, msg


# =============================================================================
# PDF report generation
# =============================================================================

def generate_pdf(question: str, answer: str, sources: list) -> bytes:
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    font_name = "Helvetica"
    win_fonts_dir = Path(os.environ.get("SystemRoot") or os.environ.get("WINDIR") or "") / "Fonts"
    candidates = (
        [str(win_fonts_dir / name) for name in FONT_CANDIDATES_WINDOWS]
        if platform.system() == "Windows"
        else FONT_CANDIDATES_UNIX
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                pdfmetrics.registerFont(TTFont("DocFont", fp))
                font_name = "DocFont"
                break
            except Exception:
                continue

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=22*mm, leftMargin=22*mm,
                            topMargin=22*mm, bottomMargin=22*mm)

    def sty(name, sz, align=TA_LEFT, sa=4, sb=4, lm=0):
        return ParagraphStyle(name, fontName=font_name, fontSize=sz,
                               spaceAfter=sa, spaceBefore=sb,
                               leading=sz * 1.65, alignment=align, leftIndent=lm)

    def safe(t):
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story = []
    story.append(Paragraph("Document Analysis Report", sty("t", 16, TA_CENTER, sa=4, sb=0)))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            sty("d", 8, TA_CENTER, sa=10, sb=2)))
    story.append(HRFlowable(width="100%", thickness=0.8, spaceAfter=10))
    story.append(Paragraph("Query", sty("h", 11, sa=6, sb=4)))
    for ln in question.split("\n"):
        if ln.strip():
            story.append(Paragraph(safe(ln), sty("b", 9, sa=3, lm=8)))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, spaceAfter=8))
    story.append(Paragraph("Answer", sty("h", 11, sa=6, sb=4)))
    for ln in answer.split("\n"):
        if ln.strip():
            story.append(Paragraph(safe(ln), sty("b", 9, sa=3, lm=8)))
    story.append(Spacer(1, 8))
    if sources:
        story.append(HRFlowable(width="100%", thickness=0.5, spaceAfter=6))
        story.append(Paragraph("References", sty("h", 10, sa=4, sb=4)))
        seen: set = set()
        for src in sources:
            s = src.metadata.get("source", "unknown")
            if s not in seen:
                seen.add(s)
                story.append(Paragraph(f"• {safe(s)}", sty("c", 8, sa=2, lm=8)))
    doc.build(story)
    return buf.getvalue()


# =============================================================================
# Native file dialog
# =============================================================================

def _pick_file_dialog() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", 1)
        exts = ("*.txt *.md *.csv *.pdf *.png *.jpg *.jpeg *.bmp *.tiff *.gif "
                "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.mp4 *.avi *.mov *.mkv *.webm *.flv")
        path = filedialog.askopenfilename(
            title="Select a document",
            filetypes=[("Supported files", exts), ("All files", "*.*")],
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""


# =============================================================================
# HTML helpers
# =============================================================================

def ornate_divider(label: str = "") -> None:
    if label:
        html = (
            f'<div style="display:flex;align-items:center;gap:10px;margin:1rem 0 0.7rem;">'
            f'<div style="flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(201,168,76,0.35));"></div>'
            f'<span style="color:rgba(201,168,76,0.65);font-size:0.58rem;letter-spacing:0.22em;white-space:nowrap;">◆&nbsp;{label}&nbsp;◆</span>'
            f'<div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,168,76,0.35),transparent);"></div>'
            f'</div>'
        )
    else:
        html = (
            '<div style="display:flex;align-items:center;gap:8px;margin:0.7rem 0;">'
            '<div style="flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(201,168,76,0.3));"></div>'
            '<span style="color:rgba(201,168,76,0.5);font-size:0.5rem;">◆</span>'
            '<div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,168,76,0.3),transparent);"></div>'
            '</div>'
        )
    st.markdown(html, unsafe_allow_html=True)


def sidebar_section(label: str, margin_top: str = "1.1rem") -> None:
    st.markdown(
        f'<div style="margin:{margin_top} 0 0.7rem;">'
        f'<div style="display:flex;align-items:flex-start;gap:8px;">'
        f'<div style="width:2px;min-height:16px;margin-top:2px;border-radius:1px;'
        f'background:linear-gradient(180deg,#C9A84C,rgba(201,168,76,0.15));"></div>'
        f'<span style="color:#C9A84C;font-size:0.85rem;letter-spacing:0.10em;'
        f'font-weight:500;line-height:1.4;">{label}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_source_item(src: str, idx: int) -> None:
    st.caption(f"📄 {src.split('/')[-1] if '/' in src else src}")


def _render_not_started() -> None:
    st.markdown(
        '<div style="text-align:center;padding:3.5rem 0;border:1px solid rgba(201,168,76,0.12);'
        'border-radius:3px;margin-top:0.5rem;">'
        '<div style="font-size:1.6rem;color:rgba(201,168,76,0.3);margin-bottom:0.6rem;">✦</div>'
        '<div style="font-size:0.8rem;letter-spacing:0.14em;color:#3E5068;">'
        'Press "Start system" in the sidebar to begin.</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# State init
# =============================================================================

def _init_state() -> None:
    IMPORT_BOX_DIR.mkdir(parents=True, exist_ok=True)
    defaults: dict = {
        "rag":                None,
        "rag_model":          None,
        "model_name":         settings.llm_model,
        "system_status":      "stopped",
        "system_error":       "",
        "mode":               "chat",
        "chat_history":       [],
        "last_sources":       [],
        "report_result":      None,
        "current_session_id": "",
        "session_name":       "New chat",
        "session_rename_id":  None,
        "chat_search":        "",
        "editing_msg_idx":    None,
        "pending_resend":     "",
        "processor":          None,
        "debug_logs":         [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state.get("processor") is None or not hasattr(
        st.session_state["processor"], "extract_text"
    ):
        st.session_state["processor"] = DocumentManager(
            documents_dir=str(DOCUMENTS_DIR),
            index_file=str(ROOT / DATA_DIR / "indexed_files.json"),
            whisper_model_size=settings.whisper_model,
        )

    if not st.session_state["current_session_id"]:
        saved = _load_all_sessions()
        if saved:
            _switch_session(saved[0]["id"])
        else:
            _new_session()


def trigger_action(action_name: str, **kwargs) -> None:
    st.session_state["action_error"]   = ""
    st.session_state["action_info"]    = ""
    st.session_state["action_success"] = ""

    rag       = st.session_state.get("rag")
    processor = st.session_state.get("processor")

    if action_name in ("bulk_import", "youtube_import") and not rag:
        st.session_state["action_error"] = "Start the system first."
        return

    if action_name == "youtube_import":
        counter = st.session_state.get("yt_url_counter", 0)
        url_val = st.session_state.get(f"yt_url_input_{counter}", "").strip()
        if not url_val:
            st.session_state["action_error"] = "Please enter a URL."
            return
        if processor and processor.is_indexed(url_val):
            st.session_state["action_info"] = "Already indexed."
            return
        st.session_state["yt_import_url"] = url_val

    st.session_state["is_processing"]  = True
    st.session_state["pending_action"] = action_name
    for k, v in kwargs.items():
        st.session_state[k] = v


# =============================================================================
# Session manager UI
# =============================================================================

def _render_session_item(s: dict) -> None:
    is_current = s["id"] == st.session_state.get("current_session_id", "")
    is_proc    = st.session_state.get("is_processing", False)

    if st.session_state.get("session_rename_id") == s["id"]:
        new_name = st.text_input("Name", value=s["name"],
                                  key=f"ri_{s['id']}", label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save", key=f"rs_{s['id']}", use_container_width=True):
                if new_name.strip():
                    _rename_session(s["id"], new_name.strip())
                    if is_current:
                        st.session_state["session_name"] = new_name.strip()
                st.session_state["session_rename_id"] = None
                st.rerun()
        with c2:
            if st.button("Cancel", key=f"rc_{s['id']}", use_container_width=True):
                st.session_state["session_rename_id"] = None
                st.rerun()
        return

    n     = s["name"]
    label = ("▶ " if is_current else "") + (n[:12] + "…" if len(n) > 12 else n)
    col_n, col_e, col_d = st.columns([6, 1, 1])
    with col_n:
        if st.button(label, key=f"s_{s['id']}", use_container_width=True, disabled=is_proc):
            if not is_current:
                _save_current_session()
                _switch_session(s["id"])
                st.rerun()
    with col_e:
        if st.button("✎", key=f"re_{s['id']}", disabled=is_proc):
            st.session_state["session_rename_id"] = s["id"]
            st.rerun()
    with col_d:
        if st.button("×", key=f"d_{s['id']}", disabled=is_proc):
            _delete_session(s["id"])
            if is_current:
                remaining = _load_all_sessions()
                if remaining:
                    _switch_session(remaining[0]["id"])
                else:
                    _new_session()
            st.rerun()


def _render_session_manager() -> None:
    is_proc = st.session_state.get("is_processing", False)
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    if st.button("＋  New chat", use_container_width=True, key="new_chat_btn", disabled=is_proc):
        _save_current_session()
        _new_session()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    sessions = _load_all_sessions()
    if not sessions:
        st.markdown(
            '<p style="color:rgba(62,80,104,0.8);font-size:0.7rem;text-align:center;padding:0.5rem 0 0;">No conversations yet</p>',
            unsafe_allow_html=True,
        )
        return

    sidebar_section("Chat history", margin_top="0.6rem")
    today  = datetime.now().date()
    groups: dict = {}
    for s in sessions:
        try:
            delta = (today - datetime.fromisoformat(s["updated_at"]).date()).days
        except Exception:
            delta = 999
        g = "Today" if delta == 0 else "Yesterday" if delta == 1 else "Past 7 days" if delta <= 7 else "Older"
        groups.setdefault(g, []).append(s)

    for label in ("Today", "Yesterday", "Past 7 days", "Older"):
        group = groups.get(label, [])
        if not group:
            continue
        st.markdown(f'<div class="session-group-label">{label}</div>', unsafe_allow_html=True)
        for s in group:
            _render_session_item(s)


# =============================================================================
# Sidebar
# =============================================================================

def _get_file_icon(f: dict) -> str:
    name = f.get("name", "").lower()
    kind = f.get("type", "")
    if name.endswith(".pdf") or kind == "PDF":           return "📕"
    if kind == "Image (OCR)":                            return "🖼️"
    if kind == "Audio":                                  return "🎵"
    if kind == "Video":                                  return "🎥"
    return "📝"


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div style="padding:0 0 0.6rem 0;margin-bottom:0.4rem;'
            'border-bottom:1px solid rgba(201,168,76,0.3);">'
            '<div style="display:flex;align-items:center;gap:6px;margin-bottom:0.5rem;">'
            '<div style="flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(201,168,76,0.5));"></div>'
            '<span style="color:rgba(201,168,76,0.6);font-size:0.5rem;">◆</span>'
            '<div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,168,76,0.5),transparent);"></div>'
            '</div>'
            '<div style="font-family:\'Noto Serif JP\',Georgia,serif;font-size:1.05rem;'
            'font-weight:300;letter-spacing:0.12em;color:#EDE8DF;">Local RAG Assistant</div>'
            '<div style="margin-top:0.2rem;font-size:0.52rem;letter-spacing:0.32em;'
            'color:rgba(201,168,76,0.55);">LOCAL · RAG · ASSISTANT</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        is_proc = st.session_state.get("is_processing", False)

        if st.session_state.get("action_error"):
            st.error(st.session_state["action_error"])
        if st.session_state.get("action_info"):
            st.info(st.session_state["action_info"])
        if st.session_state.get("action_success"):
            st.success(st.session_state["action_success"])

        # ── 1. Chat sessions ───────────────────────────────────────────────
        with st.expander("💬 Chat sessions", expanded=True):
            _render_session_manager()

        # ── 2. Document library ────────────────────────────────────────────
        with st.expander("📚 Document library", expanded=True):
            processor: DocumentManager | None = st.session_state.get("processor")
            files_for_select = processor.get_file_list() if processor else []

            if files_for_select:
                st.markdown(
                    "<p style='font-size:0.75rem;color:#8B9EBA;margin-bottom:0.25rem;'>"
                    "Context files for chat</p>", unsafe_allow_html=True
                )
                st.multiselect(
                    "Context files",
                    options=[f["rel_path"] for f in files_for_select],
                    format_func=lambda x: x.split("/")[-1],
                    key="chat_context_files",
                    label_visibility="collapsed",
                    disabled=is_proc,
                )
                st.markdown("<hr style='margin:0.4rem 0 !important;' />", unsafe_allow_html=True)

            st.markdown(
                "<p style='font-size:0.75rem;color:#8B9EBA;margin-bottom:0.25rem;'>"
                "Search documents</p>", unsafe_allow_html=True
            )
            search_term = st.text_input(
                "search", placeholder="Filter by filename…",
                label_visibility="collapsed", key="file_search", disabled=is_proc,
            )
            if search_term and not st.session_state["show_file_list"]:
                st.session_state["show_file_list"] = True

            arrow = "▾" if st.session_state["show_file_list"] else "▸"
            if st.button(f"{arrow}  Document list", use_container_width=True,
                         key="toggle_file_list", disabled=is_proc):
                st.session_state["show_file_list"] = not st.session_state["show_file_list"]
                st.rerun()

            if st.session_state["show_file_list"] and processor:
                files = processor.get_file_list()
                if not files:
                    st.caption("No documents indexed yet.")
                else:
                    filtered = [f for f in files
                                if not search_term or search_term.lower() in f["name"].lower()]
                    if not filtered:
                        st.caption("No matches.")
                    else:
                        rows = "".join(
                            f'<div style="display:flex;align-items:center;gap:6px;margin:0.25rem 0;">'
                            f'<span style="color:{"#2EA870" if f["indexed"] else "rgba(237,232,223,0.3)"};font-size:0.65rem;">●</span>'
                            f'<span style="font-size:0.78rem;">{_get_file_icon(f)}</span>'
                            f'<span style="font-size:0.78rem;color:#EDE8DF;" title="{f["name"]}">'
                            f'{f["name"][:22] + "…" if len(f["name"]) > 24 else f["name"]}'
                            f'</span></div>'
                            for f in filtered
                        )
                        st.markdown(
                            f'<div class="lr-tree-container">{rows}</div>',
                            unsafe_allow_html=True,
                        )

            st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

            # YouTube ingestion
            st.markdown(
                "<p style='font-size:0.75rem;color:#8B9EBA;margin-bottom:0.25rem;'>"
                "YouTube ingest</p>", unsafe_allow_html=True
            )
            yt_counter = st.session_state.get("yt_url_counter", 0)
            st.text_input("URL", placeholder="https://www.youtube.com/watch?v=…",
                          label_visibility="collapsed",
                          key=f"yt_url_input_{yt_counter}",
                          disabled=is_proc, autocomplete="new-password")
            st.button("Ingest subtitles / audio", use_container_width=True,
                      disabled=is_proc, on_click=trigger_action, args=("youtube_import",))

            st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

            # Document management
            st.markdown(
                "<p style='font-size:0.75rem;color:#8B9EBA;margin-bottom:0.25rem;'>"
                "Document management</p>", unsafe_allow_html=True
            )
            st.button("Import folder", use_container_width=True,
                      disabled=is_proc, on_click=trigger_action, args=("bulk_import",))
            st.button("Add single file", use_container_width=True,
                      disabled=is_proc, on_click=trigger_action, args=("file_pick",))
            st.button("Rebuild index", use_container_width=True,
                      disabled=is_proc, on_click=trigger_action, args=("rebuild",))

        # ── 3. System settings ─────────────────────────────────────────────
        with st.expander("⚙️ System settings", expanded=False):
            if settings.use_cloud_llm:
                st.markdown(
                    '<div style="background:rgba(180,40,40,0.12);border:1px solid rgba(200,60,60,0.55);'
                    'border-left:3px solid #C04040;border-radius:3px;padding:0.45rem 0.7rem;margin-bottom:0.6rem;">'
                    '<div style="color:#E87070;font-size:0.8rem;font-weight:600;">🌐 Mode: Cloud LLM</div>'
                    '<div style="color:#C08080;font-size:0.68rem;margin-top:0.2rem;">Sending queries to Anthropic API — avoid sensitive data</div>'
                    '</div>', unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="background:rgba(30,90,60,0.15);border:1px solid rgba(50,160,100,0.40);'
                    'border-left:3px solid #2EA870;border-radius:3px;padding:0.45rem 0.7rem;margin-bottom:0.6rem;">'
                    '<div style="color:#4EC494;font-size:0.8rem;font-weight:600;">🔒 Mode: Fully local</div>'
                    '<div style="color:#7BB89A;font-size:0.68rem;margin-top:0.2rem;">Offline · no data leaves your machine</div>'
                    '</div>', unsafe_allow_html=True
                )

            rag    = st.session_state["rag"]
            status = st.session_state["system_status"]
            if status == "running" and rag:
                count = rag.get_document_count()
                model = st.session_state.get("rag_model", "—")
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#0E1C2F,#132640);border:1px solid rgba(201,168,76,0.22);'
                    f'border-top:2px solid #C9A84C;border-radius:3px;padding:0.5rem 0.8rem;margin-bottom:0.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span style="color:#3E5068;font-size:0.62rem;letter-spacing:0.1em;">INDEXED CHUNKS</span>'
                    f'<span style="color:#C9A84C;font-size:1.1rem;font-weight:600;">{count}</span>'
                    f'</div><div style="color:#3E5068;font-size:0.58rem;margin-top:0.2rem;">{model}</div>'
                    f'</div>', unsafe_allow_html=True
                )
            elif status == "error":
                short = st.session_state["system_error"][:120]
                st.markdown(
                    f'<div style="background:rgba(180,50,50,0.08);border:1px solid rgba(180,50,50,0.3);'
                    f'border-left:2px solid #C04040;border-radius:2px;padding:0.4rem 0.6rem;margin-bottom:0.5rem;'
                    f'font-size:0.68rem;color:#C08080;white-space:pre-line;">{short}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="text-align:center;color:rgba(201,168,76,0.35);font-size:0.68rem;'
                    'letter-spacing:0.12em;padding:0.4rem;border:1px dashed rgba(201,168,76,0.12);'
                    'border-radius:2px;margin-bottom:0.5rem;">— stopped —</div>',
                    unsafe_allow_html=True
                )

            st.markdown(
                "<p style='font-size:0.75rem;color:#8B9EBA;margin-bottom:0.25rem;'>LLM model</p>",
                unsafe_allow_html=True
            )
            model_options = ["qwen2.5:7b", "qwen2.5:14b", "gemma3:4b", "llama3.2:3b", "elyza:jp8b"]
            current = st.session_state["model_name"]
            idx = model_options.index(current) if current in model_options else 0
            model = st.selectbox("Model", model_options, index=idx,
                                  label_visibility="collapsed", disabled=is_proc)
            st.session_state["model_name"] = model

            st.button("Start / Restart system", use_container_width=True, type="primary",
                      disabled=is_proc, on_click=trigger_action, args=("system_start",))

        # ── Action execution ───────────────────────────────────────────────
        pending = st.session_state.get("pending_action")
        if pending:
            rag       = st.session_state.get("rag")
            processor = st.session_state.get("processor")
            try:
                if pending == "system_start":
                    st.session_state["system_status"] = "starting"
                    st.session_state["system_error"]  = ""
                    ph = st.empty()
                    ph.markdown("<p style='color:var(--gold);font-size:0.75rem;'><span class='lr-spin'></span> Connecting to Ollama…</p>", unsafe_allow_html=True)
                    rag, err = connect_ollama(st.session_state["model_name"])
                    ph.empty()
                    if rag:
                        st.session_state["rag"]           = rag
                        st.session_state["rag_model"]     = st.session_state["model_name"]
                        st.session_state["system_status"] = "running"
                        st.session_state["action_success"] = "System started."
                    else:
                        st.session_state["rag"]            = None
                        st.session_state["rag_model"]      = None
                        st.session_state["system_status"]  = "error"
                        st.session_state["system_error"]   = err
                        st.session_state["action_error"]   = err

                elif pending == "rebuild":
                    if rag:
                        rag.clear_database()
                        processor.reset_index()
                        prog  = st.progress(0.0)
                        msg_h = st.empty()
                        docs  = processor.load_all_documents(
                            progress_callback=lambda p, m: (prog.progress(p), msg_h.caption(m)),
                            skip_indexed=False,
                        )
                        prog.empty(); msg_h.empty()
                        if docs:
                            n = rag.add_documents(docs)
                            st.session_state["action_success"] = f"Rebuilt: {n} chunks indexed."
                        else:
                            st.session_state["action_info"] = "No documents found."
                    else:
                        import shutil
                        db = ROOT / DATA_DIR / "chroma_db"
                        if db.exists():
                            try:
                                shutil.rmtree(db)
                            except Exception as exc:
                                _log(f"rmtree failed: {exc}", "ERROR")
                        processor.reset_index()
                        st.session_state["action_success"] = "Database cleared. Start the system to re-index."

                elif pending == "file_pick":
                    fp_str = _pick_file_dialog()
                    if fp_str:
                        fp   = Path(fp_str)
                        docs = processor.load_file(fp)
                        if docs:
                            full_text = "\n\n".join(d.page_content for d in docs)
                            saved     = processor.save_document(fp.stem, full_text, fp.name)
                            if rag:
                                saved_docs = processor.load_file(saved)
                                if saved_docs:
                                    processor.mark_indexed(str(saved))
                                    n = rag.add_documents(saved_docs)
                                    st.session_state["action_success"] = f"Added {saved.name} ({n} chunks)."
                                else:
                                    st.session_state["action_error"] = "Could not re-read saved file."
                            else:
                                st.session_state["action_success"] = f"Saved {saved.name}. Start the system to index."
                        else:
                            st.session_state["action_error"] = "Could not extract text from file."

                elif pending == "youtube_import":
                    url_val = st.session_state.get("yt_import_url", "")
                    if url_val:
                        ph = st.empty()
                        ph.markdown("<p style='color:var(--gold);font-size:0.75rem;'><span class='lr-spin'></span> Fetching…</p>", unsafe_allow_html=True)
                        docs, status_msg = processor.load_youtube(url_val)
                        ph.empty()
                        if docs:
                            title     = docs[0].metadata.get("title", "YouTube_Transcript")
                            full_text = "\n\n".join(d.page_content for d in docs)
                            saved     = processor.save_document(title, full_text, url_val)
                            saved_docs = processor.load_file(saved)
                            if saved_docs:
                                processor.mark_indexed(url_val, is_youtube=True)
                                processor.mark_indexed(str(saved))
                                n = rag.add_documents(saved_docs)
                                st.session_state["action_success"] = f"{status_msg} — saved, {n} chunks indexed."
                                st.session_state["yt_url_counter"] = yt_counter + 1
                            else:
                                st.session_state["action_error"] = "Could not re-read saved file."
                        else:
                            st.session_state["action_error"] = status_msg

                elif pending == "bulk_import":
                    IMPORT_BOX_DIR.mkdir(parents=True, exist_ok=True)
                    ph = st.empty()
                    ok, fail = processor.import_from_folder(
                        import_dir=IMPORT_BOX_DIR,
                        rag=rag,
                        progress_callback=lambda p, m: ph.markdown(
                            f"<p style='color:var(--gold);font-size:0.75rem;'><span class='lr-spin'></span> {m}</p>",
                            unsafe_allow_html=True,
                        ),
                    )
                    ph.empty()
                    if ok > 0 or fail > 0:
                        st.session_state["action_success"] = f"Import done: {ok} ok, {fail} failed."
                    else:
                        st.session_state["action_info"] = "No new files to import."

            except Exception as exc:
                _log(traceback.format_exc(), "ERROR")
                st.session_state["action_error"] = f"Error: {exc}"
            finally:
                st.session_state["is_processing"]  = False
                st.session_state["pending_action"] = None
                st.rerun()


# =============================================================================
# CHAT mode
# =============================================================================

def render_chat() -> None:
    rag = st.session_state["rag"]
    if not rag:
        _render_not_started()
        return

    history = _validate_history(st.session_state["chat_history"])
    st.session_state["chat_history"] = history

    search_term = st.session_state.get("chat_search", "").strip()
    if history:
        st.markdown('<div class="chat-search-wrap">', unsafe_allow_html=True)
        st.text_input("Search", placeholder="🔍  Search messages…",
                      key="chat_search", label_visibility="collapsed")
        if search_term:
            count = sum(1 for m in history if search_term.lower() in m["content"].lower())
            st.markdown(
                f'<div style="text-align:right;margin-top:-0.5rem;">'
                f'<span class="search-match-label" style="display:inline-block;">'
                f'🔍 {count} match{"es" if count != 1 else ""}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
    with st.container():
        for idx, msg in enumerate(history):
            icon = "👤" if msg["role"] == "user" else "📚"
            with st.chat_message(msg["role"], avatar=icon):
                st.markdown(msg["content"])

    pending_resend = st.session_state.get("pending_resend", "")
    if pending_resend:
        st.session_state["pending_resend"] = ""
        with st.chat_message("assistant", avatar="📚"):
            try:
                direct_context = prepare_direct_context()
                sources  = rag.get_sources(pending_resend)
                response = st.write_stream(rag.stream_query(pending_resend, direct_context=direct_context))
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                st.session_state["last_sources"] = sources
                _save_current_session()
                if sources:
                    with st.expander("References"):
                        seen: set = set()
                        for i, s in enumerate(sources):
                            src = s.metadata.get("source", "unknown")
                            if src not in seen:
                                seen.add(src)
                                render_source_item(src, i)
            except Exception as exc:
                _log(traceback.format_exc(), "ERROR")
                st.error(f"Response error: {exc}")
                st.session_state["chat_history"].append({"role": "assistant", "content": f"[Error] {exc}"})
                _save_current_session()

    is_proc = st.session_state.get("is_processing", False)
    if prompt := st.chat_input("Ask a question about your documents…", disabled=is_proc):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        is_new = not _session_exists(st.session_state.get("current_session_id", ""))
        with st.chat_message("assistant", avatar="📚"):
            try:
                direct_context = prepare_direct_context()
                sources  = rag.get_sources(prompt)
                response = st.write_stream(rag.stream_query(prompt, direct_context=direct_context))
                st.session_state["chat_history"].append({"role": "assistant", "content": response})
                st.session_state["last_sources"] = sources
                _save_current_session()
                if sources:
                    with st.expander("References"):
                        seen: set = set()
                        for i, s in enumerate(sources):
                            src = s.metadata.get("source", "unknown")
                            if src not in seen:
                                seen.add(src)
                                render_source_item(src, i)
            except Exception as exc:
                _log(traceback.format_exc(), "ERROR")
                st.error(f"Response error: {exc}")
                st.session_state["chat_history"].append({"role": "assistant", "content": f"[Error] {exc}"})
                _save_current_session()

        if is_new:
            st.rerun()

    if st.session_state["chat_history"]:
        if st.button("Clear conversation", key="clear_chat", disabled=is_proc):
            _delete_session(st.session_state.get("current_session_id", ""))
            _new_session()
            st.rerun()


# =============================================================================
# REPORT mode
# =============================================================================

def render_report() -> None:
    rag = st.session_state["rag"]
    if not rag:
        _render_not_started()
        return

    st.markdown("<style>section[data-testid='stMain']{padding-bottom:1rem !important;}</style>",
                unsafe_allow_html=True)

    is_proc = st.session_state.get("is_processing", False)
    with st.form("report_form"):
        question = st.text_area(
            "Your question or analysis topic",
            height=160,
            placeholder=(
                "Examples:\n"
                "· Summarise the key points from the uploaded documents\n"
                "· Compare the approaches described in the two papers\n"
                "· What does the manual say about installation?"
            ),
            disabled=is_proc,
        )
        context_info = st.text_area(
            "Additional context (optional)",
            height=80,
            placeholder="Background information, constraints, or focus areas…",
            disabled=is_proc,
        )
        submitted = st.form_submit_button("Run analysis", use_container_width=True, disabled=is_proc)

    if submitted and question.strip():
        query = question + (f"\n\n[Additional context]\n{context_info}" if context_info.strip() else "")
        ph = st.empty()
        ph.markdown("<p style='color:var(--gold);font-size:0.75rem;'><span class='lr-spin'></span> Analysing…</p>",
                    unsafe_allow_html=True)
        try:
            result = rag.query(query)
            st.session_state["report_result"] = {
                "query":   query,
                "answer":  result["answer"],
                "sources": result["sources"],
            }
        except Exception as exc:
            _log(traceback.format_exc(), "ERROR")
            st.error(f"Analysis error: {exc}")
        finally:
            ph.empty()

    r = st.session_state.get("report_result")
    if r:
        ornate_divider("Result")
        st.markdown(r["answer"])
        if r["sources"]:
            with st.expander("References"):
                seen: set = set()
                for i, s in enumerate(r["sources"]):
                    src = s.metadata.get("source", "unknown")
                    if src not in seen:
                        seen.add(src)
                        render_source_item(src, i)

        ornate_divider()
        c1, c2 = st.columns([4, 1])
        with c1:
            if st.button("Generate PDF report", use_container_width=True, disabled=is_proc):
                ph = st.empty()
                ph.markdown("<p style='color:var(--gold);font-size:0.75rem;'><span class='lr-spin'></span> Generating…</p>",
                            unsafe_allow_html=True)
                try:
                    pdf_bytes = generate_pdf(r["query"], r["answer"], r["sources"])
                    fname     = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    st.download_button("Download PDF", data=pdf_bytes, file_name=fname,
                                       mime="application/pdf", use_container_width=True)
                except Exception as exc:
                    _log(traceback.format_exc(), "ERROR")
                    st.error(f"PDF error: {exc}")
                finally:
                    ph.empty()
        with c2:
            if st.button("Clear", use_container_width=True, key="clear_report", disabled=is_proc):
                st.session_state["report_result"] = None
                st.rerun()


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    _init_state()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    bg = _bg_image_b64()
    if bg:
        st.markdown(
            f'<style>body,.stApp{{background-image:linear-gradient(rgba(8,15,26,0.65),rgba(8,15,26,0.65)),'
            f'url(\'data:image/png;base64,{bg}\') !important;background-size:cover !important;'
            f'background-position:center center !important;}}</style>',
            unsafe_allow_html=True,
        )

    render_sidebar()

    # ── Mode toggle ────────────────────────────────────────────────────────
    is_proc = st.session_state.get("is_processing", False)
    c1, c2  = st.columns(2)
    with c1:
        if st.button("Chat", use_container_width=True,
                     type="primary" if st.session_state["mode"] == "chat" else "secondary",
                     key="btn_chat", disabled=is_proc):
            st.session_state["mode"] = "chat"
            st.rerun()
    with c2:
        if st.button("Report", use_container_width=True,
                     type="primary" if st.session_state["mode"] == "report" else "secondary",
                     key="btn_report", disabled=is_proc):
            st.session_state["mode"] = "report"
            st.rerun()

    mode_label = "CHAT MODE" if st.session_state["mode"] == "chat" else "REPORT MODE"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:0.2rem 0 0;padding:0.4rem 0.7rem;'
        f'border-left:2px solid #C9A84C;background:rgba(201,168,76,0.05);">'
        f'<span style="width:5px;height:5px;border-radius:50%;background:#C9A84C;'
        f'box-shadow:0 0 6px rgba(201,168,76,0.7);flex-shrink:0;display:inline-block;"></span>'
        f'<span style="color:rgba(201,168,76,0.7);font-size:0.6rem;letter-spacing:0.22em;">{mode_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.session_state["mode"] == "chat":
        render_chat()
    else:
        render_report()


if __name__ == "__main__":
    main()
