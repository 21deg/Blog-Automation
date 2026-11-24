"""Score Google Trends searches for how well they can carry a 21DEGREES post."""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from . import llm
from .config import ANGLE_WEIGHTS, OUTPUT_DIR, PILLARS, SEED_KEYWORDS
from .trends import Trend

PillarId = Literal[tuple(PILLARS)]  # type: ignore[valid-type]


class TopicIdea(BaseModel):
    trend_query: str
    angle_type: Literal["direct", "metaphor", "none"]
    fit: int  # 0-10: how naturally the trend bridges to SME finance for Indian founders
    finance_angle: str
    pillar: PillarId
    target_keyword: str
    working_title: str
    shelf_life: Literal["days", "weeks", "evergreen"]
    why: str


class TopicScores(BaseModel):
    ideas: list[TopicIdea]


SYSTEM = f"""You are the content strategist for 21DEGREES Advisory Services, a Virtual CFO and
accounting firm for Indian founders and SMEs (Delhi, Noida, Goa).

For each Google Trends search you receive, decide whether it can carry a blog post that ranks on
Google and earns a recommendation from AI assistants, while selling Virtual CFO services.

angle_type:
- "direct": the trend itself is about money, tax, policy, markets, companies or the economy
  (RBI, GST, budget, court rulings, IPOs, startup news, layoffs, fuel prices).
- "metaphor": sport, celebrity, film, politics, science or culture that can carry a sharp
  business-finance lesson (an IPL auction as budgeting, an upset win as capital efficiency).
  These are first-class ideas: they reliably drive traffic for this blog. Score them on how
  natural and specific the lesson is, not lower because they are not finance news.
- "none": no credible bridge, or the topic is a tragedy, death, crime or disaster where a sales
  angle would be in poor taste.

fit is 0-10. 8+ means the angle is specific, timely and leads straight into a Virtual CFO pitch.
pillar is one of: {json.dumps(PILLARS)}
target_keyword: the searchable finance phrase the post should rank for after the news fades.
Prefer phrases people in India actually type, such as: {", ".join(SEED_KEYWORDS)}.
working_title: under 60 characters, keyword first, the trending name included.
Return one idea per trend, in the same order as given."""


def score(trends: list[Trend]) -> list[dict]:
    if not trends:
        return []
    payload = [{"query": t.query, "approx_traffic": t.traffic_label,
                "headlines": [n.title for n in t.news[:3]]} for t in trends]
    result, _ = llm.parse(
        system=SYSTEM,
        messages=[{"role": "user", "content": "Trending searches in India right now:\n" + json.dumps(payload, ensure_ascii=False, indent=1)}],
        output_format=TopicScores,
        effort="medium",
        max_tokens=16000,
    )
    return rank(trends, result.ideas)


def rank(trends: list[Trend], ideas: list[TopicIdea]) -> list[dict]:
    by_query = {t.query.lower(): t for t in trends}
    max_traffic = max((t.traffic for t in trends), default=1) or 1
    rows = []
    for idea in ideas:
        trend = by_query.get(idea.trend_query.lower())
        if trend is None:
            continue
        fit = max(0, min(10, idea.fit))
        # Traffic on a log scale so one viral trend doesn't swamp everything.
        demand = math.log10(trend.traffic + 10) / math.log10(max_traffic + 10)
        total = round(100 * demand * (fit / 10) * ANGLE_WEIGHTS[idea.angle_type], 1)
        rows.append({**idea.model_dump(), "score": total, "traffic": trend.traffic,
                     "traffic_label": trend.traffic_label, "explore_url": trend.explore_url,
                     "news": [n.__dict__ for n in trend.news]})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def save(rows: list[dict]) -> tuple[str, str]:
    OUTPUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    jpath = OUTPUT_DIR / f"topics-{stamp}.json"
    jpath.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    lines = ["| # | Score | Trend | Traffic | Angle | Fit | Working title | Keyword |",
             "|---|---:|---|---|---|---:|---|---|"]
    for i, r in enumerate(rows, 1):
        lines.append(f"| {i} | {r['score']} | {r['trend_query']} | {r['traffic_label']} | {r['angle_type']} | "
                     f"{r['fit']} | {r['working_title']} | {r['target_keyword']} |")
    mpath = OUTPUT_DIR / f"topics-{stamp}.md"
    mpath.write_text("\n".join(lines) + "\n")
    return str(jpath), str(mpath)
