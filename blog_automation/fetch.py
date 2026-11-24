"""Download a web page and return its readable text (title, date, main paragraphs).

Used for research in Claude Code sessions, where requests must go through the environment's proxy.
"""
from __future__ import annotations

import json
import re
import urllib.request

from bs4 import BeautifulSoup


def fetch_text(url: str, max_chars: int = 12000) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; 21degrees-research)"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        html = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    title = (soup.find("meta", property="og:title") or {}).get("content") or (soup.title.string if soup.title else "")
    date = None
    for sel in ['meta[property="article:published_time"]', 'meta[name="date"]', 'meta[name="publish-date"]', "time[datetime]"]:
        el = soup.select_one(sel)
        if el:
            date = el.get("content") or el.get("datetime")
            break
    if not date:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
        date = m.group(1) if m else None
    for bad in soup.select("script,style,nav,header,footer,aside,form,noscript,figure"):
        bad.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    def collect(node):
        paras = [p.get_text(" ", strip=True) for p in node.find_all(["p", "li", "h2", "h3"])]
        return "\n".join(p for p in paras if len(p) > 40)
    text = collect(root)
    if len(text) < 800 and soup.body is not None:  # article tag held only a teaser; use the whole page
        text = collect(soup.body)
    return {"url": url, "title": (title or "").strip(), "date": date, "text": text[:max_chars]}


if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        print(json.dumps(fetch_text(u), ensure_ascii=False, indent=1))
