"""
discussion_engine.py
Manages community discussions with lightweight JSON file-based storage.
Handles posting, retrieving, and basic moderation of comments.
"""

import os
import json
import uuid
import re
from datetime import datetime

# Storage path for discussion data
DISCUSSIONS_FILE = os.path.join(os.path.dirname(__file__), "discussions_data.json")

# Basic content moderation word list
BANNED_WORDS = {"hate", "kill", "racist", "slur", "abuse"}

COMMUNITY_GUIDELINES = [
    "Be respectful and constructive in all discussions",
    "No hate speech, discrimination, or personal attacks",
    "Base arguments on facts and credible sources",
    "No spam, self-promotion, or off-topic content",
    "Protect privacy — do not share personal information",
]


def _load_discussions() -> dict:
    """Load discussions from JSON file storage."""
    if not os.path.exists(DISCUSSIONS_FILE):
        return {}
    try:
        with open(DISCUSSIONS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_discussions(data: dict) -> bool:
    """Save discussions to JSON file storage."""
    try:
        with open(DISCUSSIONS_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        print(f"[discussion_engine] Save error: {e}")
        return False


def _moderate_content(text: str) -> tuple:
    """
    Basic content moderation.
    Returns: (is_allowed: bool, reason: str)
    """
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))

    if words & BANNED_WORDS:
        return False, "Content violates community guidelines."

    if len(text.strip()) < 5:
        return False, "Comment is too short."

    if len(text.strip()) > 2000:
        return False, "Comment exceeds 2000 character limit."

    return True, ""


def get_discussions(article_url: str) -> dict:
    """
    Get all comments for a specific article.
    Args:
        article_url: URL or identifier of the article
    Returns:
        dict with 'comments' list and 'total'
    """
    all_data = _load_discussions()
    article_key = _url_to_key(article_url)
    comments = all_data.get(article_key, [])

    # Sort by newest first
    comments_sorted = sorted(comments, key=lambda x: x.get("timestamp", ""), reverse=True)

    return {
        "comments": comments_sorted,
        "total": len(comments),
        "guidelines": COMMUNITY_GUIDELINES,
    }


def post_comment(article_url: str, username: str, text: str) -> dict:
    """
    Post a new comment on an article.
    Args:
        article_url: URL or identifier of the article
        username: Display name of the commenter (anonymous-friendly)
        text: Comment content
    Returns:
        dict with success status and comment or error message
    """
    # Moderate content
    is_allowed, reason = _moderate_content(text)
    if not is_allowed:
        return {"success": False, "error": reason}

    # Sanitize username
    username = re.sub(r'[^\w\s-]', '', username.strip())[:50] or "Anonymous"

    # Create comment object
    comment = {
        "id": str(uuid.uuid4())[:8],
        "username": username,
        "text": text.strip(),
        "timestamp": datetime.utcnow().isoformat(),
        "likes": 0,
    }

    # Persist to storage
    all_data = _load_discussions()
    article_key = _url_to_key(article_url)

    if article_key not in all_data:
        all_data[article_key] = []

    all_data[article_key].append(comment)
    _save_discussions(all_data)

    return {"success": True, "comment": comment}


def like_comment(article_url: str, comment_id: str) -> dict:
    """
    Increment like count on a comment.
    """
    all_data = _load_discussions()
    article_key = _url_to_key(article_url)
    comments = all_data.get(article_key, [])

    for comment in comments:
        if comment.get("id") == comment_id:
            comment["likes"] = comment.get("likes", 0) + 1
            _save_discussions(all_data)
            return {"success": True, "likes": comment["likes"]}

    return {"success": False, "error": "Comment not found"}


def get_trending_topics() -> list:
    """
    Get articles with most discussion activity.
    Returns: list of (article_key, comment_count) tuples
    """
    all_data = _load_discussions()
    topics = [
        {"article": key, "comment_count": len(comments)}
        for key, comments in all_data.items()
    ]
    return sorted(topics, key=lambda x: x["comment_count"], reverse=True)[:5]


def _url_to_key(url: str) -> str:
    """Convert URL to a safe storage key."""
    return re.sub(r'[^\w]', '_', url)[:100]
