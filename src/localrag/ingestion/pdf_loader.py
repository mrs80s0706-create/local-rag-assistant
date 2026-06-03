"""PDF loader using PyMuPDF (fitz) — one Document per page."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def load_pdf_file(file_path: Path) -> List[Document]:
    docs: List[Document] = []
    try:
        pdf = fitz.open(str(file_path))
        for i, page in enumerate(pdf):
            text = page.get_text("text")
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": str(file_path),
                        "type": "pdf",
                        "page": i + 1,
                        "filename": file_path.name,
                    },
                ))
        pdf.close()
    except Exception as exc:
        logger.error("[PDF] %s: %s", file_path.name, exc)
    return docs
