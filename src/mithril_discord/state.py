"""Small operational store. Never store message content, usernames, or credentials."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


class State:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS messages (key TEXT PRIMARY KEY, id TEXT NOT NULL)"
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key):
        with self.connect() as db:
            row = db.execute("SELECT id FROM messages WHERE key = ?", (key,)).fetchone()
            return int(row[0]) if row else None

    def put(self, key, message_id):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO messages VALUES (?, ?)", (key, str(message_id)))

    def remove(self, key):
        with self.connect() as db:
            db.execute("DELETE FROM messages WHERE key = ?", (key,))
