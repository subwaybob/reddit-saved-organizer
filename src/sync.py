"""
Sync script for Reddit Saved Organizer.
Fetches the authenticated user's saved items and stores them locally.

Usage:
    python src/sync.py              # Incremental sync (new items only)
    python src/sync.py --full       # Full sync (re-fetch everything)
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

import database
from reddit_client import RedditClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_sync(full: bool = False):
    """
    Main sync function.

    Args:
        full: If True, re-fetch all saved items. Otherwise, only fetch
              items newer than the last successful sync.
    """
    database.init_db()

    logger.info("Connecting to Reddit...")
    client = RedditClient()
    username = client.get_username()
    logger.info(f"Authenticated as /u/{username}")

    # Log the sync attempt
    sync_id = _start_sync_log()

    added = 0
    updated = 0
    errors = 0

    try:
        limit = None if full else 200  # Incremental: check last 200 saves
        logger.info(f"Starting {'full' if full else 'incremental'} sync...")

        for item in client.get_saved_items(limit=limit):
            try:
                is_new = database.upsert_saved_item(item)
                if is_new:
                    added += 1
                    logger.debug(f"  + {item['item_type']}: {item.get('title', '(comment)')[:60]}")
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                logger.error(f"  Error saving item {item.get('reddit_id')}: {e}")

        _finish_sync_log(sync_id, added, updated, "completed")
        logger.info(
            f"Sync complete: {added} new, {updated} updated, {errors} errors"
        )

    except Exception as e:
        _finish_sync_log(sync_id, added, updated, "failed")
        logger.error(f"Sync failed: {e}")
        sys.exit(1)

    # Print summary
    stats = database.get_stats()
    logger.info(f"Total saved items in database: {stats['total_items']}")
    logger.info(f"  Posts: {stats['posts']} | Comments: {stats['comments']}")
    logger.info(f"  Across {stats['subreddits']} subreddits")


def _start_sync_log() -> int:
    """Record sync start in the log table."""
    now = datetime.now(timezone.utc).isoformat()
    with database.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO sync_log (started_at) VALUES (?)", (now,)
        )
        return cursor.lastrowid


def _finish_sync_log(sync_id: int, added: int, updated: int, status: str):
    """Record sync completion in the log table."""
    now = datetime.now(timezone.utc).isoformat()
    with database.get_connection() as conn:
        conn.execute("""
            UPDATE sync_log
            SET finished_at = ?, items_added = ?, items_updated = ?, status = ?
            WHERE id = ?
        """, (now, added, updated, status, sync_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Reddit saved items")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full sync instead of incremental",
    )
    args = parser.parse_args()
    run_sync(full=args.full)
