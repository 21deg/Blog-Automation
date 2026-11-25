"""Fetch Google Trends daily trending searches from the public RSS feed."""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field

from .config import DEFAULT_GEO, TRENDS_RSS

HT = "{https://trends.google.com/trending/rss}"


@dataclass
class NewsItem:
    title: str
    url: str
    source: str


@dataclass
class Trend:
    query: str
    traffic: int  # lower bound from "20000+"
    traffic_label: str
    published: str
    geo: str
    news: list[NewsItem] = field(default_factory=list)

    @property
    def explore_url(self) -> str:
        from urllib.parse import quote
        return f"https://trends.google.com/trends/explore?geo={self.geo}&q={quote(self.query)}&date=now%207-d"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["explore_url"] = self.explore_url
        return d


def parse_traffic(label: str) -> int:
    digits = re.sub(r"[^\d]", "", label or "")
    return int(digits) if digits else 0


def parse_rss(xml_text: str, geo: str = DEFAULT_GEO) -> list[Trend]:
    root = ET.fromstring(xml_text)
    trends = []
    for item in root.iter("item"):
        label = item.findtext(f"{HT}approx_traffic", "")
        news = [
            NewsItem(
                title=n.findtext(f"{HT}news_item_title", "").strip(),
                url=n.findtext(f"{HT}news_item_url", "").strip(),
                source=n.findtext(f"{HT}news_item_source", "").strip(),
            )
            for n in item.findall(f"{HT}news_item")
        ]
        trends.append(Trend(
            query=(item.findtext("title") or "").strip(),
            traffic=parse_traffic(label),
            traffic_label=label,
            published=item.findtext("pubDate", ""),
            geo=geo,
            news=news,
        ))
    return trends


def fetch_trends(geo: str = DEFAULT_GEO, timeout: int = 30) -> list[Trend]:
    req = urllib.request.Request(TRENDS_RSS.format(geo=geo), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_rss(resp.read().decode("utf-8"), geo)


# ------------------------------------------------------------------ Trending Now (with categories)
# The public page https://trends.google.com/trending embeds the full list of current trending
# searches (several hundred, with categories and related queries) as page data. The RSS feed only
# carries the top 10 with no categories.

CATEGORIES = {
    1: "Autos and Vehicles", 2: "Beauty and Fashion", 3: "Business and Finance", 4: "Entertainment",
    5: "Food and Drink", 6: "Games", 7: "Health", 8: "Hobbies and Leisure", 9: "Jobs and Education",
    10: "Law and Government", 11: "Other", 13: "Pets and Animals", 14: "Politics", 15: "Science",
    16: "Shopping", 17: "Sports", 18: "Technology", 19: "Travel and Transportation", 20: "Climate",
}

# Daily quota (see automation/DAILY_RUN.md). Order matters: a trend counts for the first bucket
# whose categories it has.
BUCKETS = [
    {"name": "law-government", "categories": [10], "target": 5, "min": 4},
    {"name": "entertainment-games", "categories": [4, 6], "target": 3, "min": 3},
    {"name": "rest", "categories": None, "target": 2, "min": 2},
]


@dataclass
class TrendingNow:
    query: str
    volume: int
    categories: list[int]
    related: list[str]
    started: int | None
    active: bool
    geo: str

    @property
    def category_names(self) -> list[str]:
        return [CATEGORIES.get(c, str(c)) for c in self.categories]

    @property
    def explore_url(self) -> str:
        from urllib.parse import quote
        return f"https://trends.google.com/trends/explore?geo={self.geo}&q={quote(self.query)}&date=now%201-d"


def parse_trending_page(html: str, geo: str = DEFAULT_GEO) -> list[TrendingNow]:
    import json as _json
    i = html.find("AF_initDataCallback({key: 'ds:0'")
    if i < 0:
        raise ValueError("Trending data block not found on the page; Google may have changed the page.")
    j = html.find("data:", i)
    k = html.find(", sideChannel", j)
    data = _json.loads(html[j + 5:k])
    out = []
    for t in data[1] or []:
        try:
            out.append(TrendingNow(
                query=t[0], volume=int(t[6] or 0), categories=list(t[10] or []), related=list(t[9] or [])[:12],
                started=(t[3] or [None])[0], active=t[4] is None, geo=geo))
        except (IndexError, TypeError, ValueError):
            continue
    return out


def fetch_trending_now(geo: str = DEFAULT_GEO, hours: int = 24, timeout: int = 40) -> list[TrendingNow]:
    url = f"https://trends.google.com/trending?geo={geo}&hl=en-US&hours={hours}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return parse_trending_page(resp.read().decode("utf-8", errors="ignore"), geo)


def bucketed(trends: list[TrendingNow], per_bucket: int = 15) -> dict[str, list[dict]]:
    """Candidate pools per daily bucket, highest search volume first."""
    pools: dict[str, list[dict]] = {b["name"]: [] for b in BUCKETS}
    for t in sorted(trends, key=lambda t: t.volume, reverse=True):
        for b in BUCKETS:
            if b["categories"] is None or set(t.categories) & set(b["categories"]):
                if len(pools[b["name"]]) < per_bucket:
                    pools[b["name"]].append({"query": t.query, "volume": t.volume, "categories": t.category_names,
                                             "related": t.related, "active": t.active, "explore_url": t.explore_url})
                break
    return pools
