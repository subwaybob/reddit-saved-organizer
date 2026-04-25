"""
Database layer for Reddit Saved Organizer.
Handles local SQLite storage of saved items and user-created tags.
"""

import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

from config import Config


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS saved_items (
                id TEXT PRIMARY KEY,
                reddit_id TEXT UNIQUE NOT NULL,
                item_type TEXT NOT NULL CHECK(item_type IN ('post', 'comment')),
                title TEXT,
                body TEXT,
                subreddit TEXT NOT NULL,
                author TEXT,
                permalink TEXT NOT NULL,
                url TEXT,
                score INTEGER DEFAULT 0,
                saved_at TEXT,
                synced_at TEXT NOT NULL,
                is_deleted INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                color TEXT DEFAULT '#6b7280',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_tags (
                item_id TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (item_id, tag_id),
                FOREIGN KEY (item_id) REFERENCES saved_items(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                items_added INTEGER DEFAULT 0,
                items_updated INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            );

            -- Full-text search index for fast lookups
            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                title, body, subreddit, author,
                content='saved_items',
                content_rowid='rowid'
            );

            -- Index for common queries
            CREATE INDEX IF NOT EXISTS idx_items_subreddit ON saved_items(subreddit);
            CREATE INDEX IF NOT EXISTS idx_items_type ON saved_items(item_type);
            CREATE INDEX IF NOT EXISTS idx_items_saved_at ON saved_items(saved_at);
        """)


def upsert_saved_item(item: dict) -> bool:
    """
    Insert or update a saved item. Returns True if a new item was added.
    """
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM saved_items WHERE reddit_id = ?",
            (item["reddit_id"],)
        ).fetchone()

        now = datetime.now(timezone.utc).isoformat()

        if existing:
            conn.execute("""
                UPDATE saved_items
                SET score = ?, is_deleted = 0, synced_at = ?
                WHERE reddit_id = ?
            """, (item.get("score", 0), now, item["reddit_id"]))
            return False
        else:
            conn.execute("""
                INSERT INTO saved_items
                (id, reddit_id, item_type, title, body, subreddit,
                 author, permalink, url, score, saved_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["id"],
                item["reddit_id"],
                item["item_type"],
                item.get("title"),
                item.get("body"),
                item["subreddit"],
                item.get("author"),
                item["permalink"],
                item.get("url"),
                item.get("score", 0),
                item.get("saved_at"),
                now,
            ))

            # Update full-text search index
            conn.execute("""
                INSERT INTO items_fts(rowid, title, body, subreddit, author)
                SELECT rowid, title, body, subreddit, author
                FROM saved_items WHERE reddit_id = ?
            """, (item["reddit_id"],))

            return True


def search_items(query: str, subreddit: str = None, tag: str = None, limit: int = 50):
    """
    Search saved items using full-text search with optional filters.
    """
    with get_connection() as conn:
        conditions = []
        params = []

        if query:
            conditions.append("""
                s.rowid IN (SELECT rowid FROM items_fts WHERE items_fts MATCH ?)
            """)
            params.append(query)

        if subreddit:
            conditions.append("s.subreddit = ?")
            params.append(subreddit)

        if tag:
            conditions.append("""
                s.id IN (
                    SELECT it.item_id FROM item_tags it
                    JOIN tags t ON t.id = it.tag_id
                    WHERE t.name = ?
                )
            """)
            params.append(tag)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(f"""
            SELECT s.*, GROUP_CONCAT(t.name) as tags
            FROM saved_items s
            LEFT JOIN item_tags it ON s.id = it.item_id
            LEFT JOIN tags t ON t.id = it.tag_id
            WHERE {where} AND s.is_deleted = 0
            GROUP BY s.id
            ORDER BY s.saved_at DESC
            LIMIT ?
        """, params).fetchall()

        return [dict(row) for row in rows]


def get_all_subreddits():
    """Return a list of all subreddits that have saved items."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT subreddit, COUNT(*) as count
            FROM saved_items
            WHERE is_deleted = 0
            GROUP BY subreddit
            ORDER BY count DESC
        """).fetchall()
        return [dict(row) for row in rows]


def get_all_tags():
    """Return all user-created tags."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT t.*, COUNT(it.item_id) as item_count
            FROM tags t
            LEFT JOIN item_tags it ON t.id = it.tag_id
            GROUP BY t.id
            ORDER BY t.name
        """).fetchall()
        return [dict(row) for row in rows]


def create_tag(name: str, color: str = "#6b7280") -> int:
    """Create a new tag. Returns the tag ID."""
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO tags (name, color, created_at) VALUES (?, ?, ?)",
            (name, color, now)
        )
        return cursor.lastrowid


def add_tag_to_item(item_id: str, tag_id: int):
    """Associate a tag with a saved item."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO item_tags (item_id, tag_id) VALUES (?, ?)",
            (item_id, tag_id)
        )


def remove_tag_from_item(item_id: str, tag_id: int):
    """Remove a tag from a saved item."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM item_tags WHERE item_id = ? AND tag_id = ?",
            (item_id, tag_id)
        )


def get_stats() -> dict:
    """Return summary statistics about saved items."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM saved_items WHERE is_deleted = 0"
        ).fetchone()[0]

        posts = conn.execute(
            "SELECT COUNT(*) FROM saved_items WHERE item_type = 'post' AND is_deleted = 0"
        ).fetchone()[0]

        comments = conn.execute(
            "SELECT COUNT(*) FROM saved_items WHERE item_type = 'comment' AND is_deleted = 0"
        ).fetchone()[0]

        subreddits = conn.execute(
            "SELECT COUNT(DISTINCT subreddit) FROM saved_items WHERE is_deleted = 0"
        ).fetchone()[0]

        last_sync = conn.execute(
            "SELECT finished_at FROM sync_log WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "total_items": total,
            "posts": posts,
            "comments": comments,
            "subreddits": subreddits,
            "last_sync": last_sync[0] if last_sync else None,
        }
