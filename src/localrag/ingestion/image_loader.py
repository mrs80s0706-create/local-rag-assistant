"""Image loader using Tesseract OCR via pytesseract.

If pytesseract or Pillow is not installed the loader returns an empty list
so the rest of the ingestion pipeline continues unaffected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def load_image_file(file_path: Path) -> List[Document]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning(
            "[image_loader] pytesseract / Pillow not installed — skipping %s. "
            "Install with: pip install pytesseract Pillow  (Tesseract binary also required)",
            file_path.name,
        )
        return []

    try:
        img = Image.open(str(file_path))
        for lang in ["jpn", "jpn+eng", "eng"]:
            try:
                text = pytesseract.image_to_string(img, lang=lang)
                if text.strip():
                    return [Document(
                        page_content=text,
                        metadata={
                            "source": str(file_path),
                            "type": "image_ocr",
                            "filename": file_path.name,
                        },
                    )]
            except Exception:
                continue
    except Exception as exc:
        logger.error("[image_loader] %s: %s", file_path.name, exc)
    return []
