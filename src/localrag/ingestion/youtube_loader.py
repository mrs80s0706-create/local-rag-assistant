"""YouTube loader — transcript API first, yt-dlp + Whisper as fallback."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from .audio_loader import load_audio_file
from .base import SUPPORTED_AUDIO, SUPPORTED_VIDEO

logger = logging.getLogger(__name__)


def _get_video_title(url: str) -> str:
    try:
        oembed = (
            f"https://www.youtube.com/oembed"
            f"?url={urllib.parse.quote(url)}&format=json"
        )
        req = urllib.request.Request(oembed, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode()).get("title", "")
    except Exception as exc:
        logger.debug("[youtube] title fetch failed: %s", exc)
        return ""


def load_youtube_url(
    url: str,
    whisper_model_size: str = "small",
) -> Tuple[List[Document], str]:
    """Return (documents, status_message).

    Tries youtube-transcript-api first; falls back to yt-dlp + Whisper.
    """
    video_id_match = re.search(r"(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})", url)
    if not video_id_match:
        return [], "Invalid YouTube URL"
    video_id = video_id_match.group(1)

    # ── Strategy 1: subtitle download ──────────────────────────────────────
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript = None
        for langs in [["ja"], ["ja", "en"], None]:
            try:
                if langs:
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=langs
                    )
                else:
                    t_list = YouTubeTranscriptApi.list_transcripts(video_id)
                    transcript = next(iter(t_list)).fetch()
                break
            except Exception:
                continue

        if transcript:
            text = " ".join(e["text"] for e in transcript)
            if text.strip():
                title = _get_video_title(url) or f"YouTube Transcript {video_id}"
                return [Document(
                    page_content=text,
                    metadata={"source": url, "type": "youtube_transcript", "title": title},
                )], "Transcript downloaded"

    except ImportError:
        logger.debug("[youtube] youtube-transcript-api not installed")
    except Exception as exc:
        logger.error("[youtube] transcript error: %s", exc)

    # ── Strategy 2: yt-dlp audio download → Whisper ─────────────────────
    try:
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
                "quiet": True,
                "fixup": "never",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for f in Path(tmpdir).iterdir():
                if f.suffix.lower() in (SUPPORTED_AUDIO | SUPPORTED_VIDEO):
                    docs = load_audio_file(f, whisper_model_size=whisper_model_size)
                    if docs:
                        title = _get_video_title(url) or f"YouTube Whisper {f.stem}"
                        docs[0].metadata.update(
                            {"source": url, "type": "youtube_whisper", "title": title}
                        )
                        return docs, "Transcribed from audio"

        return [], "Audio download failed"

    except ImportError:
        return [], "yt-dlp not installed — run: pip install yt-dlp"
    except Exception as exc:
        return [], f"Error: {exc}"
