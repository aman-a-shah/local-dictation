"""Local-only SQLite history of transcriptions + derived stats.

Everything here stays on disk in the user's app-data dir and never touches the
network — it exists purely to power the dashboard (recent transcriptions, total
words, time saved, streaks). Writes happen on the engine's worker thread after a
successful insert, so they must be cheap and never raise into the pipeline.

A single connection is shared across threads with check_same_thread=False guarded
by a lock; volume is tiny (one row per utterance) so this is plenty.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from typing import Optional

from .paths import db_path

# Average sustained typing speed (wpm). Used only for the playful "time saved"
# stat: words / TYPING_WPM minutes is what typing them would have cost.
TYPING_WPM = 40.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         REAL    NOT NULL,            -- unix epoch seconds
    text       TEXT    NOT NULL,
    words      INTEGER NOT NULL,
    chars      INTEGER NOT NULL,
    duration_s REAL    NOT NULL DEFAULT 0,  -- seconds of audio
    elapsed_s  REAL    NOT NULL DEFAULT 0,  -- seconds to transcribe
    model      TEXT,
    lang       TEXT
);
CREATE INDEX IF NOT EXISTS idx_transcriptions_ts ON transcriptions(ts DESC);
"""


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


class Store:
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = str(path or db_path())
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            # WAL lets the out-of-process dashboard read while the engine writes
            # without either blocking the other; busy_timeout caps any contention
            # so a history write can never stall the transcription worker for long.
            # Both are best-effort (e.g. a read-only filesystem) — ignore failures.
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
                self._conn.execute("PRAGMA busy_timeout=2000")
            except sqlite3.Error:
                pass
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- writes -------------------------------------------------------------
    def add(
        self,
        text: str,
        *,
        duration_s: float = 0.0,
        elapsed_s: float = 0.0,
        model: str = "",
        lang: str = "",
        ts: Optional[float] = None,
    ) -> int:
        text = (text or "").strip()
        if not text:
            return -1
        row = (
            ts if ts is not None else time.time(),
            text,
            _count_words(text),
            len(text),
            float(duration_s),
            float(elapsed_s),
            model,
            lang,
        )
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO transcriptions (ts, text, words, chars, duration_s, elapsed_s, model, lang) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def delete(self, item_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM transcriptions WHERE id = ?", (item_id,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM transcriptions")
            self._conn.commit()

    # -- reads --------------------------------------------------------------
    def recent(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM transcriptions ORDER BY ts DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, query: str, limit: int = 50) -> list[dict]:
        q = f"%{query.strip()}%"
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM transcriptions WHERE text LIKE ? ORDER BY ts DESC LIMIT ?",
                (q, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get(self, item_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM transcriptions WHERE id = ?", (item_id,)
            ).fetchone()
        return dict(row) if row else None

    def stats(self) -> dict:
        with self._lock:
            agg = self._conn.execute(
                "SELECT COUNT(*) AS sessions, "
                "       COALESCE(SUM(words), 0) AS words, "
                "       COALESCE(SUM(chars), 0) AS chars, "
                "       COALESCE(SUM(duration_s), 0) AS audio_s, "
                "       COALESCE(SUM(elapsed_s), 0) AS compute_s, "
                "       MIN(ts) AS first_ts, MAX(ts) AS last_ts "
                "FROM transcriptions"
            ).fetchone()
            # Words per day for the activity chart (last 30 days), local time.
            daily_rows = self._conn.execute(
                "SELECT date(ts, 'unixepoch', 'localtime') AS day, "
                "       SUM(words) AS words, COUNT(*) AS sessions "
                "FROM transcriptions "
                "GROUP BY day ORDER BY day DESC LIMIT 30"
            ).fetchall()
            days = self._conn.execute(
                "SELECT DISTINCT date(ts, 'unixepoch', 'localtime') AS day "
                "FROM transcriptions ORDER BY day DESC"
            ).fetchall()

        words = int(agg["words"] or 0)
        daily = [
            {"day": r["day"], "words": int(r["words"] or 0), "sessions": int(r["sessions"] or 0)}
            for r in reversed(daily_rows)
        ]
        return {
            "sessions": int(agg["sessions"] or 0),
            "words": words,
            "chars": int(agg["chars"] or 0),
            "audio_seconds": float(agg["audio_s"] or 0.0),
            "compute_seconds": float(agg["compute_s"] or 0.0),
            # Time typing those words would have cost, in seconds.
            "time_saved_seconds": (words / TYPING_WPM) * 60.0,
            "first_ts": agg["first_ts"],
            "last_ts": agg["last_ts"],
            "daily": daily,
            "streak_days": _streak([r["day"] for r in days]),
        }


def _streak(sorted_desc_days: list[str]) -> int:
    """Consecutive-day streak ending today or yesterday (string dates YYYY-MM-DD)."""
    if not sorted_desc_days:
        return 0
    import datetime as _dt

    have = {_dt.date.fromisoformat(d) for d in sorted_desc_days if d}
    today = _dt.date.fromtimestamp(time.time())
    # Allow the streak to "count" if the user dictated today or yesterday.
    start = today if today in have else today - _dt.timedelta(days=1)
    if start not in have:
        return 0
    streak = 0
    cur = start
    while cur in have:
        streak += 1
        cur -= _dt.timedelta(days=1)
    return streak


# Lazily-created process-wide singleton (the engine and the dashboard bridge
# both want the same DB without passing handles around).
_STORE: Optional[Store] = None
_STORE_LOCK = threading.Lock()


def get_store() -> Store:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = Store()
        return _STORE
