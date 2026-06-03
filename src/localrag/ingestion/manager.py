"""
DocumentManager — coordinates loaders, file index, and markdown storage.

Replaces the monolithic DocumentProcessor from the original implementation.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from langchain_core.documents import Document

from .audio_loader import load_audio_file
from .base import (
    ALL_SUPPORTED,
    SUPPORTED_AUDIO,
    SUPPORTED_IMAGE,
    SUPPORTED_PDF,
    SUPPORTED_TEXT,
    SUPPORTED_VIDEO,
    FileIndex,
    load_text_file,
    save_as_markdown,
)
from .image_loader import load_image_file
from .pdf_loader import load_pdf_file
from .youtube_loader import load_youtube_url

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


class DocumentManager:
    """High-level document ingestion coordinator."""

    def __init__(
        self,
        documents_dir: str | Path = "data/documents",
        index_file: Optional[str | Path] = None,
        whisper_model_size: str = "small",
    ) -> None:
        self.documents_dir = Path(documents_dir)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        if index_file:
            self._index = FileIndex(Path(index_file))
        else:
            self._index = FileIndex(self.documents_dir.parent / "indexed_files.json")

        self.whisper_model_size = whisper_model_size

    # ── Index passthrough ──────────────────────────────────────────────────

    def is_indexed(self, key: str) -> bool:
        return self._index.is_indexed(key)

    def mark_indexed(self, key: str, is_youtube: bool = False) -> None:
        self._index.mark_indexed(key, is_youtube)

    def reset_index(self) -> None:
        self._index.reset()

    # ── Single-file loaders ────────────────────────────────────────────────

    def load_file(self, file_path: Path) -> List[Document]:
        ext = file_path.suffix.lower()
        if ext in SUPPORTED_TEXT:
            return load_text_file(file_path)
        if ext in SUPPORTED_PDF:
            return load_pdf_file(file_path)
        if ext in SUPPORTED_IMAGE:
            return load_image_file(file_path)
        if ext in SUPPORTED_AUDIO | SUPPORTED_VIDEO:
            return load_audio_file(file_path, whisper_model_size=self.whisper_model_size)
        return []

    def load_youtube(self, url: str) -> Tuple[List[Document], str]:
        return load_youtube_url(url, whisper_model_size=self.whisper_model_size)

    # ── Save to documents dir ──────────────────────────────────────────────

    def save_document(
        self, title: str, text: str, source: str, subfolder: str = ""
    ) -> Path:
        dest = self.documents_dir / subfolder if subfolder else self.documents_dir
        return save_as_markdown(title, text, source, dest)

    # ── Bulk operations ────────────────────────────────────────────────────

    def load_all_documents(
        self,
        progress_callback: Optional[ProgressCallback] = None,
        skip_indexed: bool = True,
    ) -> List[Document]:
        """Load all un-indexed files from documents_dir."""
        all_docs: List[Document] = []
        files = [f for f in self.documents_dir.rglob("*") if f.is_file()]
        total = len(files)

        for i, fp in enumerate(files):
            if progress_callback:
                progress_callback(i / max(total, 1), f"Loading: {fp.name}")

            key = str(fp)
            if skip_indexed and self._index.is_indexed(key):
                continue

            docs = self.load_file(fp)
            if docs:
                all_docs.extend(docs)
                self._index.mark_indexed(key)

        if progress_callback:
            progress_callback(1.0, "Done")
        return all_docs

    def import_from_folder(
        self,
        import_dir: Path,
        rag,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Tuple[int, int]:
        """Recursively import files from import_dir into documents_dir and index them."""
        import_dir = Path(import_dir)
        if not import_dir.exists():
            return 0, 0

        files = [f for f in import_dir.rglob("*") if f.is_file()]
        total = len(files)
        ok = fail = 0

        for i, fp in enumerate(files):
            if progress_callback:
                try:
                    rel = str(fp.relative_to(import_dir))
                except Exception:
                    rel = fp.name
                progress_callback(i / max(total, 1), f"Processing: {rel}")

            ext = fp.suffix.lower()
            if ext not in ALL_SUPPORTED:
                continue

            try:
                rel_parent = fp.parent.relative_to(import_dir)
                subfolder = str(rel_parent) if rel_parent != Path(".") else ""
            except Exception:
                subfolder = ""

            dest_dir = self.documents_dir / subfolder if subfolder else self.documents_dir
            target_md = dest_dir / f"{fp.stem[:100]}.md"

            if target_md.exists() and self._index.is_indexed(str(target_md)):
                continue

            docs = self.load_file(fp)
            if not docs:
                logger.warning("Could not extract text: %s", fp.name)
                fail += 1
                continue

            try:
                full_text = "\n\n".join(d.page_content for d in docs)
                saved = self.save_document(fp.stem, full_text, fp.name, subfolder)
                saved_docs = load_text_file(saved)
                if saved_docs and rag:
                    self._index.mark_indexed(str(saved))
                    self._index.mark_indexed(str(fp))
                    rag.add_documents(saved_docs)
                    ok += 1
                else:
                    fail += 1
            except Exception as exc:
                logger.error("Import error %s: %s", fp.name, exc)
                fail += 1

        if progress_callback:
            progress_callback(1.0, f"Done: {ok} ok, {fail} failed")
        return ok, fail

    # ── File listing ───────────────────────────────────────────────────────

    def get_file_list(self) -> List[dict]:
        result = []
        for fp in self.documents_dir.rglob("*"):
            if not fp.is_file():
                continue
            ext = fp.suffix.lower()
            if ext in SUPPORTED_TEXT:
                kind = "Text"
            elif ext in SUPPORTED_PDF:
                kind = "PDF"
            elif ext in SUPPORTED_IMAGE:
                kind = "Image (OCR)"
            elif ext in SUPPORTED_AUDIO:
                kind = "Audio"
            elif ext in SUPPORTED_VIDEO:
                kind = "Video"
            else:
                continue

            try:
                rel = f"{self.documents_dir.name}/" + str(
                    fp.relative_to(self.documents_dir)
                ).replace("\\", "/")
            except Exception:
                rel = fp.name

            result.append({
                "name":    fp.name,
                "rel_path": rel,
                "type":    kind,
                "size":    f"{fp.stat().st_size / 1024:.1f} KB",
                "indexed": self._index.is_indexed(str(fp)),
            })
        return result

    def extract_text(self, file_path_str: str) -> dict:
        """Extract text from a path (relative or absolute) for use as direct context."""
        fp = Path(file_path_str)
        if not fp.is_absolute():
            prefix = f"{self.documents_dir.name}/"
            clean = file_path_str[len(prefix):] if file_path_str.startswith(prefix) else file_path_str
            fp = self.documents_dir / clean

        if not fp.exists():
            return {"name": fp.name, "path": file_path_str,
                    "content": f"[Error: file not found: {fp}]"}

        docs = self.load_file(fp)
        content = "\n\n".join(d.page_content for d in docs) if docs else ""
        return {"name": fp.name, "path": file_path_str, "content": content}
