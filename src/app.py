"""
Local web UI for Reddit Saved Organizer.
Provides search, browse, and tag management in a browser interface.

Usage:
    python src/app.py
    Then open http://localhost:5000
"""

import logging

from flask import Flask, render_template, request, jsonify

import database
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static",
)


@app.route("/")
def index():
    """Main page - search and browse saved items."""
    database.init_db()
    stats = database.get_stats()
    subreddits = database.get_all_subreddits()
    tags = database.get_all_tags()
    return render_template(
        "index.html",
        stats=stats,
        subreddits=subreddits,
        tags=tags,
    )


@app.route("/search")
def search():
    """Search endpoint - returns matching saved items."""
    query = request.args.get("q", "").strip()
    subreddit = request.args.get("subreddit", "").strip() or None
    tag = request.args.get("tag", "").strip() or None
    limit = min(int(request.args.get("limit", 50)), 200)

    results = database.search_items(
        query=query,
        subreddit=subreddit,
        tag=tag,
        limit=limit,
    )
    return jsonify(results)


@app.route("/tags", methods=["GET"])
def list_tags():
    """List all tags."""
    tags = database.get_all_tags()
    return jsonify(tags)


@app.route("/tags", methods=["POST"])
def create_tag():
    """Create a new tag."""
    data = request.get_json()
    name = data.get("name", "").strip()
    color = data.get("color", "#6b7280")

    if not name:
        return jsonify({"error": "Tag name is required"}), 400

    try:
        tag_id = database.create_tag(name, color)
        return jsonify({"id": tag_id, "name": name, "color": color}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 409


@app.route("/items/<item_id>/tags/<int:tag_id>", methods=["PUT"])
def tag_item(item_id, tag_id):
    """Add a tag to a saved item."""
    database.add_tag_to_item(item_id, tag_id)
    return jsonify({"status": "ok"})


@app.route("/items/<item_id>/tags/<int:tag_id>", methods=["DELETE"])
def untag_item(item_id, tag_id):
    """Remove a tag from a saved item."""
    database.remove_tag_from_item(item_id, tag_id)
    return jsonify({"status": "ok"})


@app.route("/stats")
def stats():
    """Return summary statistics."""
    return jsonify(database.get_stats())


if __name__ == "__main__":
    logger.info(f"Starting Reddit Saved Organizer on http://localhost:{Config.FLASK_PORT}")
    app.run(
        host="127.0.0.1",
        port=Config.FLASK_PORT,
        debug=True,
    )
