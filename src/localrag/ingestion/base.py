"""
Shared types and loader interface for all ingestion modules.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Protocol, Tuple

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── Supported extensions ────────────────────────────────────────────────────

SUPPORTED_TEXT  = {".txt", ".md", ".csv", ".text"}
SUPPORTED_PDF   = {".pdf"}
SUPPORTED_IMAGE = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"}
SUPPORTED_AUDIO = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus"}
SUPPORTED_VIDEO = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}

ALL_SUPPORTED = (
    SUPPORTED_TEXT | SUPPORTED_PDF | SUPPORTED_IMAGE | SUPPORTED_AUDIO | SUPPORTED_VIDEO
)


# ── Loader Protocol ─────────────────────────────────────────────────────────

class Loader(Protocol):
    def load(self, file_path: Path) -> List[Document]:
        """Load a single file and return a list of Documents."""
        ...


# ── Index management ────────────────────────────────────────────────────────

class FileIndex:
    """Tracks which files and YouTube URLs have already been indexed."""

    def __init__(self, index_path: Path) -> None:
        self._path = index_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"files": [], "youtube": []}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def is_indexed(self, key: str) -> bool:
        return key in self._data["files"] or key in self._data["youtube"]

    def mark_indexed(self, key: str, is_youtube: bool = False) -> None:
        bucket = "youtube" if is_youtube else "files"
        if key not in self._data[bucket]:
            self._data[bucket].append(key)
        self._save()

    def reset(self) -> None:
        self._data = {"files": [], "youtube": []}
        self._save()


# ── Text file loader (encoding-resilient) ──────────────────────────────────

def load_text_file(file_path: Path) -> List[Document]:
    for enc in ["utf-8", "utf-8-sig", "shift_jis", "cp932", "euc-jp"]:
        try:
            text = file_path.read_text(encoding=enc)
            if text.strip():
                return [Document(
                    page_content=text,
                    metadata={"source": str(file_path), "type": "text",
                               "filename": file_path.name},
                )]
        except (UnicodeDecodeError, UnicodeError):
            continue
    return []


# ── Markdown save helper ────────────────────────────────────────────────────

def save_as_markdown(
    title: str,
    text: str,
    source: str,
    dest_dir: Path,
) -> Path:
    """Serialise extracted text as a Markdown file and return its path."""
    import re
    from datetime import datetime

    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)[:100]
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / f"{safe_title}.md"

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"# {title}\n\n- **Date**: {today}\n- **Source**: {source}\n\n---\n\n{text}\n"
    file_path.write_text(content, encoding="utf-8")
    logger.info("Saved markdown: %s", file_path)
    return file_path
