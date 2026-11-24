"""Schedule finished posts on WordPress and build the daily digest."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import wordpress as wp
from .config import BACKLOG, CATEGORY_IDS, OUTPUT_DIR, SCHEDULE

USED_FILE = OUTPUT_DIR / "backlog-used.json"


def daily_log_path(day: datetime) -> Path:
    return OUTPUT_DIR / f"daily-{day:%Y%m%d}.json"


def _load(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def publish_folder(folder: str, publish_at: datetime | None, force: bool = False, draft: bool = False) -> dict:
    folder_p = Path(folder)
    post = json.loads((folder_p / "post.json").read_text())
    checks = (folder_p / "checks.txt").read_text()
    if "FAIL" in checks and not force:
        raise SystemExit(f"{folder}: checks are failing; fix the post or pass --force.\n{checks}")
    existing = wp.list_posts()
    clash = [p for p in existing if p["slug"] == post["slug"]]
    if clash:
        raise SystemExit(f"A post with slug '{post['slug']}' already exists: {clash[0]['link']}")
    created = wp.create_post(
        title=post["h1"], content=(folder_p / "post.html").read_text(), slug=post["slug"],
        excerpt=post["meta_description"], categories=CATEGORY_IDS.get(post["pillar"], CATEGORY_IDS["default"]),
        publish_at=None if draft else publish_at, status="draft" if draft else None)
    wp.set_seo(created["id"], title_tag=post["title_tag"], meta_description=post["meta_description"],
               focus_keyword=post["focus_keyword"])
    entry = {**created, "title": post["h1"], "title_tag": post["title_tag"], "folder": str(folder_p),
             "publish_at_ist": publish_at.astimezone(wp.IST).strftime("%d %b %Y, %I:%M %p IST") if publish_at and not draft else "draft",
             "warnings": [l for l in checks.splitlines() if l.startswith(("WARN", "FAIL"))]}
    log_path = daily_log_path(datetime.now(wp.IST))
    log = _load(log_path, [])
    log.append(entry)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    return entry


def next_slots(count: int, now: datetime | None = None) -> list[datetime]:
    """Publish times for today's posts, spread across the configured IST window and starting
    no earlier than min_review_hours from now. If today's window is (nearly) over, use tomorrow's."""
    from datetime import timedelta
    now = (now or datetime.now(wp.IST)).astimezone(wp.IST)
    first, last = SCHEDULE["first_hour_ist"], SCHEDULE["last_hour_ist"]
    earliest = now + timedelta(hours=SCHEDULE["min_review_hours"])
    day = now
    for _ in range(2):
        start = day.replace(hour=first, minute=0, second=0, microsecond=0)
        end = day.replace(hour=last, minute=0, second=0, microsecond=0)
        start = max(start, earliest)
        if end - start >= timedelta(hours=1):
            step = (end - start) / max(1, count - 1) if count > 1 else timedelta(0)
            return [(start + i * step).replace(second=0, microsecond=0) for i in range(count)]
        day = (day + timedelta(days=1)).replace(hour=0, minute=0)
    raise RuntimeError("Could not find a publishing window; check SCHEDULE in config.py")


def backlog_next(count: int) -> list[dict]:
    """Unused evergreen topics, skipping any whose keyword an existing post already covers."""
    items = json.loads(BACKLOG.read_text())
    used = set(_load(USED_FILE, []))
    existing = wp.list_posts()
    out = []
    for item in items:
        if item["id"] in used:
            continue
        if wp.similar_existing(item["target_keyword"], existing):
            used.add(item["id"])  # already covered on the site
            continue
        out.append(item)
        if len(out) >= count:
            break
    OUTPUT_DIR.mkdir(exist_ok=True)
    USED_FILE.write_text(json.dumps(sorted(used)))
    return out


def backlog_mark(ids: list[str]) -> None:
    used = set(_load(USED_FILE, []))
    used.update(ids)
    OUTPUT_DIR.mkdir(exist_ok=True)
    USED_FILE.write_text(json.dumps(sorted(used)))


def digest(day: datetime | None = None) -> tuple[str, str]:
    """Subject and plain-text body for the daily review email."""
    day = day or datetime.now(wp.IST)
    log = _load(daily_log_path(day), [])
    subject = f"21DEGREES blog: {len(log)} posts scheduled for {day:%d %b}"
    lines = [f"{len(log)} posts are scheduled to go live today. Review each one before its publish time.",
             "To stop a post, open it and switch it to Draft, or move it to Trash.", ""]
    for i, e in enumerate(log, 1):
        lines += [f"{i}. {e['title']}", f"   Goes live: {e['publish_at_ist']}", f"   Edit: {e['edit_link']}",
                  f"   Preview: {e['link']}"]
        lines += [f"   Check: {w}" for w in e.get("warnings", [])]
        lines.append("")
    lines.append("Indexing: Rank Math submits each post to Bing and IndexNow when it goes live; Google picks it up from the sitemap.")
    return subject, "\n".join(lines)
