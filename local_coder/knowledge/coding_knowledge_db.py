"""Disk-backed SQLite FTS5 knowledge substrate for canonical modern coding idioms."""

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
from typing import Optional


@dataclass(frozen=True)
class KnowledgeHit:
    """Represents a retrieved canonical coding knowledge hit."""

    topic: str
    category: str
    version: str
    signature: str
    canonical_code: str
    docstring: str
    score: float = 0.0


class CodingKnowledgeDB:
    """Zero-RAM on-disk knowledge substrate storing canonical modern frameworks and patterns."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        if db_path is None:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.db_path = repo_root / "data" / "coding_knowledge.db"
        else:
            self.db_path = Path(db_path).resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns SQLite connection optimized for low-latency memory-mapped reading."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA mmap_size = 67108864")  # 64MB zero-copy mmap
        return conn

    def _init_database(self) -> None:
        """Creates tables and FTS5 inverted search index."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coding_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    version TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    canonical_code TEXT NOT NULL,
                    anti_patterns TEXT DEFAULT '',
                    docstring TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS coding_knowledge_fts USING fts5(
                    topic,
                    category,
                    signature,
                    docstring,
                    tokenize = 'porter trigram'
                )
                """
            )

    def insert_entry(
        self,
        topic: str,
        category: str,
        version: str,
        signature: str,
        canonical_code: str,
        docstring: str,
        anti_patterns: str = "",
    ) -> bool:
        """Inserts or updates a canonical framework/pattern entry."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO coding_knowledge (topic, category, version, signature, canonical_code, anti_patterns, docstring)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(topic) DO UPDATE SET
                    category=excluded.category,
                    version=excluded.version,
                    signature=excluded.signature,
                    canonical_code=excluded.canonical_code,
                    anti_patterns=excluded.anti_patterns,
                    docstring=excluded.docstring
                """,
                (topic, category, version, signature, canonical_code, anti_patterns, docstring),
            )
            # Re-index in FTS5
            conn.execute("DELETE FROM coding_knowledge_fts WHERE topic = ?", (topic,))
            conn.execute(
                "INSERT INTO coding_knowledge_fts (topic, category, signature, docstring) VALUES (?, ?, ?, ?)",
                (topic, category, signature, docstring),
            )
        return True

    def lookup_topic(self, topic: str) -> Optional[KnowledgeHit]:
        """Performs exact indexed B-Tree lookup on topic slug in sub-millisecond."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT topic, category, version, signature, canonical_code, docstring FROM coding_knowledge WHERE topic = ?",
                (topic,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return KnowledgeHit(
                topic=row[0],
                category=row[1],
                version=row[2],
                signature=row[3],
                canonical_code=row[4],
                docstring=row[5],
                score=1.0,
            )

    def search(self, query: str, limit: int = 3) -> list[KnowledgeHit]:
        """Searches inverted index using BM25 full-text matching."""
        sanitized = "".join(c if c.isalnum() else " " for c in query).strip()
        if not sanitized:
            return []

        fts_query = " OR ".join(f"{term}*" for term in sanitized.split()[:5])
        hits: list[KnowledgeHit] = []

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT k.topic, k.category, k.version, k.signature, k.canonical_code, k.docstring, f.rank
                FROM coding_knowledge_fts f
                JOIN coding_knowledge k ON k.topic = f.topic
                WHERE coding_knowledge_fts MATCH ?
                ORDER BY f.rank
                LIMIT ?
                """,
                (fts_query, limit),
            )
            for row in cursor.fetchall():
                hits.append(
                    KnowledgeHit(
                        topic=row[0],
                        category=row[1],
                        version=row[2],
                        signature=row[3],
                        canonical_code=row[4],
                        docstring=row[5],
                        score=float(-row[6]),
                    )
                )

        return hits

    def count_entries(self) -> int:
        """Returns total number of indexed knowledge entries."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM coding_knowledge")
            return int(cursor.fetchone()[0])
