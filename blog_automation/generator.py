"""Research a chosen topic on the web, then write a post that follows the blueprint."""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from . import llm, render, validate
from .config import BOOKING_URL, OUTPUT_DIR, PILLARS, POST_INVENTORY, PROMPTS_DIR, SERVICE_PAGES


class Section(BaseModel):
    heading: str
    body_markdown: str  # may contain ### subheadings, lists, a table, inline [links](url)


class FAQ(BaseModel):
    question: str
    answer: str


class InlineImage(BaseModel):
    after_heading: str  # exact text of the section heading the image goes under
    alt: str
    caption: str
    prompt: str  # what the image shows (scene, chart or diagram), for Canva or for drawing it


class BlogPost(BaseModel):
    focus_keyword: str
    secondary_keywords: list[str]
    pillar: Literal[tuple(PILLARS)]  # type: ignore[valid-type]
    title_tag: str
    meta_description: str
    slug: str
    h1: str
    quick_answer: str
    hook: str
    sections: list[Section]
    bottom_line: str
    faqs: list[FAQ]
    ps: str
    cta: str
    image_alt: str
    image_prompt: str
    inline_images: list[InlineImage] = []


def style_guide() -> str:
    return (PROMPTS_DIR / "style_guide.md").read_text()


def link_inventory() -> tuple[str, set[str]]:
    """Existing posts and pages the writer may link to, grouped as a compact list."""
    posts = json.loads(POST_INVENTORY.read_text()) if POST_INVENTORY.exists() else []
    lines, urls = [], set()
    for name, url in SERVICE_PAGES.items():
        lines.append(f"- {name}: {url}")
        urls.add(validate._norm(url))
    for p in posts:
        if p.get("url"):
            title = (p.get("title") or "").replace(" - 21DEGREES", "")
            lines.append(f"- {title}: {p['url']}")
            urls.add(validate._norm(p["url"]))
    return "\n".join(lines), urls


RESEARCH_SYSTEM = """You are a research assistant for an Indian finance blog. Use web search to
gather verifiable facts. Prefer primary sources (RBI, CBIC, PIB, Supreme Court / High Court orders,
MCA, SEBI, company filings) and major Indian publications (The Hindu, Economic Times, Mint,
Business Standard, Indian Express, ESPNcricinfo for cricket). Never invent a number or a URL."""


def research(topic: dict) -> tuple[str, dict[str, str]]:
    prompt = f"""Topic for a 21DEGREES blog post:
Trending search: {topic['trend_query']} ({topic.get('traffic_label', '')} searches in India)
Headlines: {json.dumps([n['title'] for n in topic.get('news', [])], ensure_ascii=False)}
Finance angle: {topic['finance_angle']}
Target keyword: {topic['target_keyword']}

Research and return notes with:
1. What happened: key facts, dates, names and numbers about the trend, each with its source URL.
2. Data for the finance angle that applies to Indian SMEs (rates, rules, thresholds, market
   figures), each with its source URL.
3. 6-8 questions Indians actually search about '{topic['target_keyword']}' and this trend.
4. Anything time-sensitive the writer must get right (deadlines, effective dates).
Format every fact as: fact — source title — URL."""
    return llm.text_with_web_search(system=RESEARCH_SYSTEM, prompt=prompt)


def _system_blocks(inventory: str) -> list[dict]:
    # Stable content first and cached: style guide + link inventory are identical across posts.
    return [{"type": "text", "text": style_guide() + "\n\n## Link inventory (internal links must come from here)\n" + inventory,
             "cache_control": {"type": "ephemeral"}}]


def write(topic: dict, notes: str, sources: dict[str, str], inventory: str) -> BlogPost:
    source_list = "\n".join(f"- {t}: {u}" for u, t in sources.items())
    user = f"""Write a blog post for this topic.

Trending search: {topic['trend_query']}
Angle type: {topic['angle_type']}
Finance angle: {topic['finance_angle']}
Pillar: {topic['pillar']}
Target keyword: {topic['target_keyword']}
Working title: {topic['working_title']}
Today's date: {datetime.now():%d %B %Y}
Booking link for the CTA: {BOOKING_URL}

Research notes:
{notes}

Source URLs you may cite (external links must come only from this list):
{source_list}

Section headings go in `heading` without '#'. Do not repeat the H1, quick answer, hook,
bottom line, FAQ or P.S. inside `sections`; they are separate fields. Total length of all fields
together: 1,500-1,900 words."""
    post, _ = llm.parse(system=_system_blocks(inventory), messages=[{"role": "user", "content": user}],
                        output_format=BlogPost, effort="high")
    return post


def revise(post: BlogPost, failed: list[validate.Check], inventory: str, sources: dict[str, str]) -> BlogPost:
    problems = "\n".join(f"- {c.name}: {c.detail}" for c in failed)
    source_list = "\n".join(f"- {u}" for u in sources)
    user = f"""This draft failed some checks. Fix only what is needed and return the full post.

Failed checks:
{problems}

Allowed external source URLs:
{source_list}

Draft:
{post.model_dump_json(indent=1)}"""
    fixed, _ = llm.parse(system=_system_blocks(inventory), messages=[{"role": "user", "content": user}],
                         output_format=BlogPost, effort="high")
    return fixed


def generate(topic: dict, max_revisions: int = 2, log=print) -> dict:
    inventory, inventory_urls = link_inventory()
    log(f"Researching '{topic['trend_query']}' ...")
    notes, sources = research(topic)
    log(f"  {len(sources)} sources found")
    log("Writing draft ...")
    post = write(topic, notes, sources, inventory)
    checks = validate.run(post, render.to_markdown(post), set(sources), inventory_urls)
    for attempt in range(max_revisions):
        failed = validate.failures(checks)
        if not failed:
            break
        log(f"Revision {attempt + 1}: fixing {', '.join(c.name for c in failed)}")
        post = revise(post, failed, inventory, sources)
        checks = validate.run(post, render.to_markdown(post), set(sources), inventory_urls)

    return save(post, notes, sources, checks, log=log)


def save(post: BlogPost, notes: str, sources: dict[str, str], checks, log=print, work_dir: str | None = None) -> dict:
    """Write the post files to output/<date>-<slug>/. Image files in work_dir (featured.svg/.jpg/.png
    and inline-N.*) are copied alongside."""
    import shutil
    OUTPUT_DIR.mkdir(exist_ok=True)
    folder = OUTPUT_DIR / f"{datetime.now():%Y%m%d}-{post.slug}"
    folder.mkdir(exist_ok=True)
    (folder / "post.md").write_text(render.to_markdown(post, front_matter=True))
    (folder / "post.html").write_text(render.to_html(post))
    (folder / "post.json").write_text(post.model_dump_json(indent=1))
    (folder / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1))
    (folder / "research.md").write_text(notes + "\n\n## Sources\n" + "\n".join(f"- [{t}]({u})" for u, t in sources.items()))
    (folder / "checks.txt").write_text(validate.report(checks) + "\n")
    if work_dir:
        src = Path(work_dir)
        for pattern in ("featured.svg", "featured-canva.*", "inline-*"):
            for f in src.glob(pattern):
                shutil.copy(f, folder / f.name)
    log(validate.report(checks))
    return {"folder": str(folder), "passed": not validate.failures(checks), "checks": [c.__dict__ for c in checks]}


def finalize(post_path: str, sources_path: str, research_path: str | None = None, log=print) -> dict:
    """Validate and render a post written outside the API (for example by Claude in a Claude Code
    session). sources_path is a JSON object {url: title} of every source found during research."""
    post = BlogPost.model_validate_json(open(post_path).read())
    sources = json.loads(open(sources_path).read())
    notes = open(research_path).read() if research_path else ""
    _, inventory_urls = link_inventory()
    checks = validate.run(post, render.to_markdown(post), set(sources), inventory_urls)
    work = Path(post_path).parent
    checks += validate.image_checks(post, work)
    return save(post, notes, sources, checks, log=log, work_dir=str(work))
