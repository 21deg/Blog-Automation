"""Automatic indexing for newly published posts.

This module handles:
1. Automatic submission to Google/Bing when posts go live
2. Periodic sitemap regeneration
3. Indexing status monitoring
4. Error logging and recovery
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from . import wordpress as wp, indexing
from .config import OUTPUT_DIR

logger = logging.getLogger(__name__)

# Track indexing state
INDEX_LOG = OUTPUT_DIR / "indexing-log.json"


def _load_index_log() -> dict:
    """Load indexing status log."""
    if INDEX_LOG.exists():
        try:
            return json.loads(INDEX_LOG.read_text())
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_index_log(data: dict) -> None:
    """Save indexing status log."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=1, default=str))


def index_new_posts(hours: int = 1, log=print) -> dict:
    """Find and index posts published in the last N hours.

    This runs automatically after posts go live. It:
    1. Finds recently published posts
    2. Submits to IndexNow (Bing, Yandex, etc.)
    3. Logs the indexing action
    4. Updates the sitemap status

    Args:
        hours: Look back this many hours for new posts
        log: Function to call for logging

    Returns:
        Dict with indexing results and statistics
    """
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "lookback_hours": hours,
        "new_posts": [],
        "submitted_urls": [],
        "failed_urls": [],
        "indexnow_response": None,
        "sitemap_status": None,
    }

    try:
        now = datetime.now(wp.IST)
        cutoff = now - timedelta(hours=hours)

        # Get recently published posts
        log(f"🔍 Looking for posts published in last {hours} hour(s)...")
        wp.list_posts.cache_clear()
        all_posts = wp.list_posts("publish")

        for post in all_posts:
            try:
                when = datetime.fromisoformat(post["date"]).replace(tzinfo=wp.IST)
                if cutoff <= when <= now:
                    result["new_posts"].append({
                        "id": post["id"],
                        "title": post.get("title", "Untitled"),
                        "url": post.get("link"),
                        "published": post["date"]
                    })
            except (ValueError, TypeError):
                continue

        if not result["new_posts"]:
            log(f"✓ No new posts in last {hours} hour(s)")
            result["status"] = "no_new_posts"
            return result

        # Submit URLs for indexing
        urls = [p["url"] for p in result["new_posts"] if p.get("url")]
        log(f"📤 Submitting {len(urls)} new post(s) for indexing...")

        try:
            indexnow_result = wp.submit_for_indexing(urls)
            result["indexnow_response"] = indexnow_result
            result["submitted_urls"] = urls
            log(f"✓ Submitted {len(urls)} URLs to search engines")
            if isinstance(indexnow_result, dict):
                log(f"  Response: {indexnow_result}")
        except Exception as e:
            result["failed_urls"] = urls
            log(f"⚠ Indexing failed for {len(urls)} URLs: {str(e)[:100]}")

        # Log the indexing action
        index_log = _load_index_log()
        for post in result["new_posts"]:
            post_key = f"post_{post['id']}"
            if post_key not in index_log:
                index_log[post_key] = {
                    "id": post["id"],
                    "title": post["title"],
                    "url": post["url"],
                    "first_indexed": result["timestamp"],
                    "last_indexed": result["timestamp"],
                    "index_count": 1
                }
            else:
                index_log[post_key]["last_indexed"] = result["timestamp"]
                index_log[post_key]["index_count"] = index_log[post_key].get("index_count", 1) + 1

        _save_index_log(index_log)

        result["status"] = "success" if result["submitted_urls"] else "partial"
        result["indexed_count"] = len(result["submitted_urls"])

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        log(f"❌ Error during indexing: {str(e)}")

    return result


def regenerate_sitemap(output_path: str | None = None, log=print) -> dict:
    """Regenerate the sitemap with all published posts.

    This should be run:
    1. After batch publishing posts
    2. Weekly for maintenance
    3. When inventory changes

    Args:
        output_path: Where to save sitemap (optional)
        log: Function to call for logging

    Returns:
        Dict with sitemap generation status
    """
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending",
        "sitemap_path": output_path,
        "entries_count": 0,
        "error": None
    }

    try:
        log("🔄 Regenerating sitemap...")
        xml = indexing.generate_sitemap(output_path)
        result["entries_count"] = xml.count("<url>")
        result["status"] = "success"
        log(f"✓ Sitemap regenerated with {result['entries_count']} entries")

        if output_path:
            log(f"  Saved to: {output_path}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:200]
        log(f"❌ Sitemap regeneration failed: {str(e)}")

    return result


def daily_indexing_report(hours: int = 24) -> dict:
    """Get indexing report for posts published in the last N hours.

    Returns statistics on recently indexed posts.
    """
    index_log = _load_index_log()
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    report = {
        "period": f"last {hours} hours",
        "lookback": cutoff.isoformat(),
        "total_indexed": 0,
        "reindexed": 0,
        "posts": []
    }

    for post_key, post_data in index_log.items():
        try:
            last_indexed = datetime.fromisoformat(post_data.get("last_indexed", ""))
            if last_indexed >= cutoff:
                report["posts"].append(post_data)
                report["total_indexed"] += 1
                if post_data.get("index_count", 1) > 1:
                    report["reindexed"] += 1
        except (ValueError, TypeError):
            continue

    return report


def setup_auto_indexing_logs() -> None:
    """Initialize logging directory and files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize empty log if not present
    if not INDEX_LOG.exists():
        _save_index_log({})
        logger.info(f"Created indexing log at {INDEX_LOG}")


def get_indexing_status(post_id: int | None = None) -> dict:
    """Get indexing status for a specific post or all posts.

    Args:
        post_id: Specific post ID to check, or None for all

    Returns:
        Dict with indexing status
    """
    index_log = _load_index_log()

    if post_id:
        post_key = f"post_{post_id}"
        if post_key in index_log:
            return {
                "found": True,
                "data": index_log[post_key],
                "status": "indexed" if index_log[post_key].get("last_indexed") else "pending"
            }
        return {"found": False, "post_id": post_id}

    # Return summary for all posts
    return {
        "total_posts_tracked": len(index_log),
        "posts": index_log,
        "last_update": max([p.get("last_indexed") for p in index_log.values()], default=None)
    }
