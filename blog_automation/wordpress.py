"""Minimal WordPress REST client for 21degrees.in.

Authentication: the cloud environment's network proxy adds the saved WordPress application
password to every request to 21degrees.in, so no credentials are handled here. To run elsewhere,
set WP_USER and WP_APP_PASSWORD and they are sent as HTTP Basic auth.
"""
from __future__ import annotations

import base64
import functools
import json
import time
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .config import SITE

API = f"{SITE}/wp-json"
IST = timezone(timedelta(hours=5, minutes=30))


class WordPressError(RuntimeError):
    pass


def _request(method: str, path: str, body: dict | None = None, params: dict | None = None):
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "21degrees-blog-automation"})
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if user and pw:
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode() or "null"
                return json.loads(payload), dict(resp.headers)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504) and attempt < 5:
                wait = int(e.headers.get("Retry-After") or 0) or 15 * 2 ** attempt  # 15s .. 4 min
                time.sleep(min(wait, 300))
                continue
            _raise(e, method, path)


def _raise(e, method, path):
    detail = e.read().decode(errors="ignore")[:300]
    if e.code in (401, 403):
        raise WordPressError(f"WordPress refused the login ({e.code}). Check the saved application password. {detail}") from e
    raise WordPressError(f"{method} {path} failed with {e.code}: {detail}") from e


def whoami() -> dict:
    me, _ = _request("GET", "/wp/v2/users/me", params={"context": "edit"})
    return {"id": me["id"], "name": me["name"], "roles": me.get("roles"),
            "can_publish": bool((me.get("capabilities") or {}).get("publish_posts"))}


@functools.lru_cache(maxsize=4)
def list_posts(statuses: str = "publish,future,draft,pending") -> list[dict]:
    """All posts with id, slug, title, status and date (for de-duplication)."""
    out, page = [], 1
    while True:
        rows, headers = _request("GET", "/wp/v2/posts", params={
            "status": statuses, "per_page": 100, "page": page, "context": "edit",
            "_fields": "id,slug,title,status,date,link"})
        for r in rows:
            out.append({"id": r["id"], "slug": r["slug"], "status": r["status"], "date": r["date"],
                        "link": r.get("link"), "title": (r.get("title") or {}).get("raw") or ""})
        total_pages = next((v for k, v in headers.items() if k.lower() == "x-wp-totalpages"), "1")
        if page >= int(total_pages):
            return out
        page += 1


def create_post(*, title: str, content: str, slug: str, excerpt: str, categories: list[int],
                publish_at: datetime | None, status: str | None = None) -> dict:
    """Create a post. With publish_at in the future, WordPress schedules it (status 'future')."""
    body = {"title": title, "content": content, "slug": slug, "excerpt": excerpt, "categories": categories,
            "comment_status": "open"}
    if status:
        body["status"] = status
    elif publish_at:
        body["status"] = "future"
    else:
        body["status"] = "draft"
    if publish_at:
        body["date_gmt"] = publish_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    post, _ = _request("POST", "/wp/v2/posts", body)
    return {"id": post["id"], "status": post["status"], "link": post.get("link"), "slug": post.get("slug"),
            "date": post.get("date"), "edit_link": f"{SITE}/wp-admin/post.php?post={post['id']}&action=edit"}


def set_seo(post_id: int, *, title_tag: str, meta_description: str, focus_keyword: str) -> None:
    """Rank Math SEO title, description and focus keyword."""
    _request("POST", "/rankmath/v1/updateMeta", {
        "objectType": "post", "objectID": post_id,
        "meta": {"rank_math_title": title_tag, "rank_math_description": meta_description,
                 "rank_math_focus_keyword": focus_keyword}})


def submit_for_indexing(urls: list[str]) -> dict:
    """Rank Math Instant Indexing (IndexNow: Bing, Yandex and others). Only for live URLs."""
    res, _ = _request("POST", "/rankmath/v1/in/submitUrls", {"urls": "\n".join(urls)})
    return res if isinstance(res, dict) else {"result": res}


def trash_post(post_id: int) -> None:
    _request("DELETE", f"/wp/v2/posts/{post_id}")


def slot_times(day: datetime, count: int, start_hour: int, end_hour: int) -> list[datetime]:
    """Spread `count` publish times evenly between start_hour and end_hour IST on `day`."""
    base = day.astimezone(IST).replace(hour=start_hour, minute=0, second=0, microsecond=0)
    span = (end_hour - start_hour) * 60
    step = span / max(1, count - 1) if count > 1 else 0
    return [base + timedelta(minutes=round(i * step)) for i in range(count)]


def tokens(text: str) -> set[str]:
    stop = {"a", "an", "the", "of", "for", "in", "to", "and", "is", "your", "you", "what", "how", "why",
            "does", "do", "on", "with", "my", "can", "should", "india", "vs"}
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in stop and len(w) > 1}


def similar_existing(keyword: str, posts: list[dict], threshold: float = 0.6) -> dict | None:
    """Return an existing post whose slug/title covers the same keyword, if any."""
    kw = tokens(keyword)
    if not kw:
        return None
    for p in posts:
        words = tokens(p["slug"].replace("-", " ") + " " + p["title"])
        if len(kw & words) / len(kw) >= threshold:
            return p
    return None
