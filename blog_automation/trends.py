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
