"""Audio / video loader using faster-whisper for local transcription.

If faster-whisper is not installed the loader returns an empty list so the
rest of the ingestion pipeline continues unaffected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

_whisper_model = None


def _get_whisper(model_size: str = "small"):
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper_model


def load_audio_file(
    file_path: Path,
    whisper_model_size: str = "small",
    language: Optional[str] = None,
) -> List[Document]:
    try:
        model = _get_whisper(whisper_model_size)
        segments, info = model.transcribe(
            str(file_path),
            language=language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(seg.text for seg in segments)
        if text.strip():
            return [Document(
                page_content=text,
                metadata={
                    "source": str(file_path),
                    "type": "transcription",
                    "filename": file_path.name,
                    "language": info.language,
                },
            )]
    except ImportError:
        logger.warning(
            "[audio_loader] faster-whisper not installed — skipping %s. "
            "Install with: pip install faster-whisper",
            file_path.name,
        )
    except Exception as exc:
        logger.error("[audio_loader] %s: %s", file_path.name, exc)
    return []
