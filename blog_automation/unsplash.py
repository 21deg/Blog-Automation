"""Unsplash photos (free, commercial use allowed under the Unsplash License).

Needs a free developer Access Key in UNSPLASH_ACCESS_KEY (demo apps allow 50 requests an hour).
API guidelines followed here: credit the photographer and Unsplash, and call each photo's
download_location endpoint when a photo is used.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.unsplash.com"
UTM = "utm_source=21degrees_blog_automation&utm_medium=referral"


class UnsplashUnavailable(RuntimeError):
    pass


def _key() -> str:
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if not key:
        raise UnsplashUnavailable("UNSPLASH_ACCESS_KEY is not set")
    return key


def _get(path: str, params: dict | None = None) -> dict | list:
    url = f"{API}{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Client-ID {_key()}", "Accept-Version": "v1",
                                               "User-Agent": "21degrees-blog-automation"})
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise UnsplashUnavailable(f"Unsplash {e.code}: {e.read().decode(errors='ignore')[:200]}") from e


def search(query: str, n: int = 10, orientation: str = "landscape") -> list[dict]:
    data = _get("/search/photos", {"query": query, "per_page": n, "orientation": orientation,
                                   "content_filter": "high"})
    out = []
    for p in data.get("results", []):
        user = p.get("user") or {}
        out.append({
            "id": p["id"],
            "url": p["urls"]["raw"] + "&w=1600&q=85&fm=jpg&fit=max",
            "description": p.get("alt_description") or p.get("description") or "",
            "photographer": user.get("name", "Unknown"),
            "photographer_url": f"{(user.get('links') or {}).get('html', 'https://unsplash.com')}?{UTM}",
            "download_location": (p.get("links") or {}).get("download_location", ""),
            "width": p.get("width"), "height": p.get("height"),
        })
    return out


def credit_html(photo: dict) -> str:
    return (f'Photo by <a href="{photo["photographer_url"]}" rel="nofollow noopener" target="_blank">'
            f'{photo["photographer"]}</a> on <a href="https://unsplash.com/?{UTM}" rel="nofollow noopener" '
            f'target="_blank">Unsplash</a>')


def credit_text(photo: dict) -> str:
    return f"Photo by {photo['photographer']} on Unsplash"


def mark_downloaded(photo: dict) -> None:
    """Required by the API guidelines whenever a photo is used."""
    if photo.get("download_location"):
        try:
            req = urllib.request.Request(photo["download_location"], headers={
                "Authorization": f"Client-ID {_key()}", "User-Agent": "21degrees-blog-automation"})
            urllib.request.urlopen(req, timeout=30).read()
        except Exception:  # noqa: BLE001 - tracking ping only
            pass


def fetch(photo: dict) -> bytes:
    req = urllib.request.Request(photo["url"], headers={"User-Agent": "21degrees-blog-automation"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    mark_downloaded(photo)
    return data


def first_photo(queries: list[str], skip_ids: set[str] | None = None) -> dict | None:
    """First usable photo across the queries, skipping photos already used today."""
    skip_ids = skip_ids or set()
    for q in [q for q in queries if q]:
        for p in search(q):
            if p["id"] not in skip_ids and (p.get("width") or 0) >= 1200:
                return p
    return None
