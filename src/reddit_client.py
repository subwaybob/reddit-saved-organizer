"""
Reddit API client wrapper for Reddit Saved Organizer.
Wraps PRAW with rate-limit awareness and proper User-Agent handling.
"""

import time
import logging
import uuid

import praw

from config import Config

logger = logging.getLogger(__name__)


class RedditClient:
    """
    Thin wrapper around PRAW that enforces rate-limit awareness
    and provides methods scoped to only what this app needs.
    """

    def __init__(self):
        Config.validate()
        self._reddit = praw.Reddit(
            client_id=Config.REDDIT_CLIENT_ID,
            client_secret=Config.REDDIT_CLIENT_SECRET,
            user_agent=Config.USER_AGENT,
            redirect_uri=Config.REDDIT_REDIRECT_URI,
        )
        self._request_count = 0
        self._window_start = time.monotonic()

    @property
    def auth_url(self) -> str:
        """Generate the OAuth2 authorization URL for the user."""
        state = str(uuid.uuid4())
        return self._reddit.auth.url(
            scopes=Config.SCOPES,
            state=state,
            duration="permanent",
        ), state

    def authorize(self, code: str):
        """Complete the OAuth2 flow with the authorization code."""
        refresh_token = self._reddit.auth.authorize(code)
        logger.info("Successfully authorized with Reddit")
        return refresh_token

    def get_username(self) -> str:
        """Return the authenticated user's username."""
        return self._reddit.user.me().name

    def get_saved_items(self, limit: int = None):
        """
        Generator that yields saved items for the authenticated user.
        Automatically handles pagination and rate limiting.

        Each yielded item is a dict with normalized fields regardless
        of whether the source was a post (Submission) or comment.
        """
        user = self._reddit.user.me()
        saved = user.saved(limit=limit)

        for item in saved:
            self._respect_rate_limit()

            if isinstance(item, praw.models.Submission):
                yield self._normalize_submission(item)
            elif isinstance(item, praw.models.Comment):
                yield self._normalize_comment(item)
            else:
                logger.warning(f"Unknown saved item type: {type(item)}")

    def _normalize_submission(self, submission) -> dict:
        """Convert a PRAW Submission to our internal format."""
        return {
            "id": str(uuid.uuid4()),
            "reddit_id": submission.name,  # fullname like t3_xxxxx
            "item_type": "post",
            "title": submission.title,
            "body": submission.selftext or None,
            "subreddit": str(submission.subreddit),
            "author": str(submission.author) if submission.author else "[deleted]",
            "permalink": f"https://reddit.com{submission.permalink}",
            "url": submission.url if submission.url != submission.permalink else None,
            "score": submission.score,
            "saved_at": self._epoch_to_iso(submission.created_utc),
        }

    def _normalize_comment(self, comment) -> dict:
        """Convert a PRAW Comment to our internal format."""
        return {
            "id": str(uuid.uuid4()),
            "reddit_id": comment.name,  # fullname like t1_xxxxx
            "item_type": "comment",
            "title": getattr(comment, "link_title", None),
            "body": comment.body,
            "subreddit": str(comment.subreddit),
            "author": str(comment.author) if comment.author else "[deleted]",
            "permalink": f"https://reddit.com{comment.permalink}",
            "url": None,
            "score": comment.score,
            "saved_at": self._epoch_to_iso(comment.created_utc),
        }

    def _respect_rate_limit(self):
        """
        Simple rate limiter: ensures we stay well under
        Reddit's 60 requests/minute for OAuth clients.
        We target 30 req/min to be a good citizen.
        """
        self._request_count += 1
        elapsed = time.monotonic() - self._window_start

        if elapsed < 60 and self._request_count >= 30:
            sleep_time = 60 - elapsed + 1
            logger.info(f"Rate limit: pausing {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self._request_count = 0
            self._window_start = time.monotonic()
        elif elapsed >= 60:
            self._request_count = 0
            self._window_start = time.monotonic()

    @staticmethod
    def _epoch_to_iso(epoch: float) -> str:
        """Convert Unix epoch to ISO 8601 string."""
        from datetime import datetime, timezone
        return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
