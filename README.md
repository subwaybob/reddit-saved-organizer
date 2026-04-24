# Reddit Saved Organizer

A lightweight, open-source personal tool that helps Reddit users organize, tag, and search their saved posts and comments.

## Why?

Reddit's built-in "Saved" feature has no search, no tags, no categories, and is capped at 1,000 items. Once you hit the limit, older saves silently disappear. This tool solves that by giving you a local, searchable archive of your own saved content.

## What It Does

- Authenticates via OAuth2 (read-only scope) to access your saved items
- Stores your saved posts/comments locally in a SQLite database
- Lets you tag, categorize, and full-text search your saved content
- Runs entirely on your own machine - no server, no data sharing

## What It Does NOT Do

- Does not scrape, crawl, or bulk-download subreddit content
- Does not access other users' data
- Does not post, vote, or modify anything on Reddit
- Does not use Reddit data for AI/ML training
- Does not commercialize or redistribute any Reddit content

## Tech Stack

- Python 3.10+
- PRAW (Python Reddit API Wrapper)
- SQLite for local storage
- Flask for local web UI

## Setup

### Prerequisites

- Python 3.10 or higher
- Reddit API credentials ([request access here](https://support.reddithelp.com/hc/en-us/requests/new?ticket_form_id=14868593862164))

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/reddit-saved-organizer.git
cd reddit-saved-organizer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy the example config and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Reddit OAuth credentials:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_REDIRECT_URI=http://localhost:8080/callback
```

### Usage

**Sync your saved items:**

```bash
python src/sync.py
```

**Launch the local web UI:**

```bash
python src/app.py
```

Then open `http://localhost:5000` in your browser.

## API Usage & Rate Limits

This tool is designed to be a good citizen of the Reddit API:

- Uses OAuth2 authentication with minimal scopes (`identity`, `history`)
- Descriptive User-Agent string per Reddit guidelines
- Respects the 60 requests/minute rate limit and monitors `X-Ratelimit-Remaining` headers
- Incremental sync after initial import (only fetches new saves)
- Expected volume: ~10-20 API calls per sync session

## Project Structure

```
reddit-saved-organizer/
├── src/
│   ├── app.py           # Flask web UI
│   ├── sync.py          # Reddit API sync logic
│   ├── database.py      # SQLite database layer
│   ├── reddit_client.py # PRAW wrapper with rate limiting
│   └── config.py        # Configuration loader
├── templates/           # HTML templates for web UI
├── static/css/          # Stylesheets
├── tests/               # Unit tests
├── requirements.txt
├── .env.example
└── README.md
```

## Privacy

All data stays on your machine. There is no analytics, no telemetry, no external server communication beyond the Reddit API itself.

## License

MIT
