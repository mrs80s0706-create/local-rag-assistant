"""Chat session persistence — each session is a JSON file."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class SessionStore:
    def __init__(self, sessions_dir: str | Path = "data/chat_sessions") -> None:
        self._dir = Path(sessions_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"chat_{session_id}.json"

    # ── Read ─────────────────────────────────────────────────────────────

    def list_sessions(self) -> List[dict]:
        sessions = []
        for p in self._dir.glob("chat_*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                sessions.append({
                    "id":         data["id"],
                    "name":       data.get("name", "New chat"),
                    "updated_at": data.get("updated_at", ""),
                    "msg_count":  len(data.get("messages", [])),
                })
            except Exception:
                pass
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def load(self, session_id: str) -> Optional[dict]:
        p = self._path(session_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    # ── Write ─────────────────────────────────────────────────────────────

    def save(self, session_id: str, name: str, messages: List[dict]) -> None:
        p = self._path(session_id)
        now = datetime.now().isoformat()
        created_at = now
        if p.exists():
            try:
                created_at = json.loads(p.read_text(encoding="utf-8")).get("created_at", now)
            except Exception:
                pass
        p.write_text(
            json.dumps(
                {
                    "id":         session_id,
                    "name":       name,
                    "created_at": created_at,
                    "updated_at": now,
                    "messages":   messages,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def rename(self, session_id: str, new_name: str) -> None:
        p = self._path(session_id)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["name"] = new_name
            data["updated_at"] = datetime.now().isoformat()
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def delete(self, session_id: str) -> None:
        p = self._path(session_id)
        if p.exists():
            p.unlink()

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def auto_name(messages: List[dict], fallback: str = "New chat") -> str:
        for m in messages:
            if m.get("role") == "user" and m.get("content", "").strip():
                t = m["content"].strip()
                return t[:20] + ("…" if len(t) > 20 else "")
        return fallback
