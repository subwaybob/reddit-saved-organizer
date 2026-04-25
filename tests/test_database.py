"""
Tests for the database layer.
Run with: python -m pytest tests/
"""

import os
import sys
import uuid
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["DATABASE_PATH"] = ":memory:"

import database


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh in-memory database for each test."""
    database.Config.DATABASE_PATH = ":memory:"
    database.init_db()
    yield


def _make_item(**overrides):
    """Helper to create a test saved item dict."""
    defaults = {
        "id": str(uuid.uuid4()),
        "reddit_id": f"t3_{uuid.uuid4().hex[:7]}",
        "item_type": "post",
        "title": "Test Post Title",
        "body": "This is the body of a test post.",
        "subreddit": "python",
        "author": "testuser",
        "permalink": "https://reddit.com/r/python/comments/abc123/test/",
        "url": None,
        "score": 42,
        "saved_at": "2025-01-15T12:00:00+00:00",
    }
    defaults.update(overrides)
    return defaults


class TestUpsert:
    def test_insert_new_item(self):
        item = _make_item()
        is_new = database.upsert_saved_item(item)
        assert is_new is True

    def test_update_existing_item(self):
        item = _make_item()
        database.upsert_saved_item(item)
        is_new = database.upsert_saved_item(item)
        assert is_new is False


class TestSearch:
    def test_search_by_title(self):
        database.upsert_saved_item(_make_item(title="Python async tutorial"))
        database.upsert_saved_item(_make_item(title="JavaScript basics"))

        results = database.search_items("Python async")
        assert len(results) == 1
        assert "Python" in results[0]["title"]

    def test_filter_by_subreddit(self):
        database.upsert_saved_item(_make_item(subreddit="python"))
        database.upsert_saved_item(_make_item(subreddit="javascript"))

        results = database.search_items("", subreddit="python")
        assert len(results) == 1
        assert results[0]["subreddit"] == "python"


class TestTags:
    def test_create_and_list_tags(self):
        database.create_tag("important", "#ff0000")
        tags = database.get_all_tags()
        assert len(tags) == 1
        assert tags[0]["name"] == "important"

    def test_tag_item(self):
        item = _make_item()
        database.upsert_saved_item(item)
        tag_id = database.create_tag("readlater")
        database.add_tag_to_item(item["id"], tag_id)

        results = database.search_items("", tag="readlater")
        assert len(results) == 1


class TestStats:
    def test_stats_counts(self):
        database.upsert_saved_item(_make_item(item_type="post"))
        database.upsert_saved_item(_make_item(item_type="comment"))

        stats = database.get_stats()
        assert stats["total_items"] == 2
        assert stats["posts"] == 1
        assert stats["comments"] == 1
