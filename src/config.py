"""
Configuration loader for Reddit Saved Organizer.
Reads settings from .env file and provides defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Reddit API
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
    REDDIT_REDIRECT_URI = os.getenv("REDDIT_REDIRECT_URI", "http://localhost:8080/callback")

    # User-Agent follows Reddit's required format:
    # <platform>:<app ID>:<version> (by /u/<reddit username>)
    USER_AGENT = f"desktop:reddit-saved-organizer:v0.1.0 (by /u/{REDDIT_USERNAME})"

    # OAuth scopes - minimal permissions needed
    # identity: verify the authenticated user
    # history: read the user's saved posts and comments
    SCOPES = ["identity", "history"]

    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "saved_items.db")

    # Flask
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

    # Sync settings
    SYNC_BATCH_SIZE = int(os.getenv("SYNC_BATCH_SIZE", "100"))

    @classmethod
    def validate(cls):
        """Check that required credentials are set."""
        missing = []
        if not cls.REDDIT_CLIENT_ID or cls.REDDIT_CLIENT_ID == "your_client_id_here":
            missing.append("REDDIT_CLIENT_ID")
        if not cls.REDDIT_CLIENT_SECRET or cls.REDDIT_CLIENT_SECRET == "your_client_secret_here":
            missing.append("REDDIT_CLIENT_SECRET")
        if not cls.REDDIT_USERNAME or cls.REDDIT_USERNAME == "your_reddit_username":
            missing.append("REDDIT_USERNAME")

        if missing:
            raise ValueError(
                f"Missing required config: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in your credentials."
            )
