"""Check a generated post against the blueprint rules (analysis §4)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .config import BANNED_PHRASES, BOOKING_URL, SITE, TARGETS

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.M)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    hard: bool = True  # hard failures trigger a revision pass


def _norm(url: str) -> str:
    p = urlparse(url)
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"


def plain_text(md: str) -> str:
    md = LINK_RE.sub(r"\1", md)
    md = re.sub(r"[#>*_`|]", " ", md)
    return re.sub(r"\s+", " ", md).strip()


def word_count(md: str) -> int:
    return len(plain_text(md).split())


def avg_sentence_words(md: str) -> float:
    text = plain_text(md)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) > 1]
    return round(len(text.split()) / max(1, len(sentences)), 1)


def run(post, markdown_body: str, allowed_sources: set[str], inventory_urls: set[str]) -> list[Check]:
    t = TARGETS
    checks: list[Check] = []

    def add(name, ok, detail, hard=True):
        checks.append(Check(name, bool(ok), detail, hard))

    words = word_count(markdown_body)
    add("length", t["words"][0] <= words <= t["words"][1], f"{words} words (target {t['words'][0]}-{t['words'][1]})")
    add("title_tag", len(post.title_tag) <= t["title_tag_max"], f"{len(post.title_tag)} chars (max {t['title_tag_max']})")
    kw_first = post.focus_keyword.lower().split()[0] in post.title_tag.lower()[: max(25, len(post.focus_keyword) + 5)]
    add("keyword_in_title", kw_first, f"focus keyword '{post.focus_keyword}' near the start of the title", hard=False)
    md_len = len(post.meta_description)
    add("meta_description", t["meta_desc"][0] <= md_len <= t["meta_desc"][1], f"{md_len} chars (target {t['meta_desc'][0]}-{t['meta_desc'][1]})")
    slug_ok = re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", post.slug) and len(post.slug.split("-")) <= t["slug_max_words"]
    add("slug", slug_ok, f"'{post.slug}' (lowercase, ≤{t['slug_max_words']} words)")
    qa = len(post.quick_answer.split())
    add("quick_answer", t["quick_answer_words"][0] <= qa <= t["quick_answer_words"][1], f"{qa} words (target {t['quick_answer_words'][0]}-{t['quick_answer_words'][1]})")
    asw = avg_sentence_words(markdown_body)
    add("sentence_length", asw <= t["avg_sentence_words_max"], f"average {asw} words per sentence", hard=False)
    n_faq = len(post.faqs)
    add("faq_count", t["faq_count"][0] <= n_faq <= t["faq_count"][1], f"{n_faq} FAQs (target {t['faq_count'][0]}-{t['faq_count'][1]})")

    links = [u for _, u in LINK_RE.findall(markdown_body)]
    site_host = urlparse(SITE).netloc
    internal = [u for u in links if urlparse(u).netloc.removeprefix("www.") == site_host]
    external = [u for u in links if u not in internal and _norm(u) != _norm(BOOKING_URL)]
    add("internal_links", t["internal_links"][0] <= len(set(internal)) <= t["internal_links"][1], f"{len(set(internal))} internal links")
    unknown_internal = [u for u in internal if _norm(u) not in inventory_urls]
    add("internal_links_real", not unknown_internal, "all internal links exist" if not unknown_internal else f"not on the site: {unknown_internal}")
    add("external_links", len(set(external)) >= t["external_links_min"], f"{len(set(external))} external source links")
    allowed = {_norm(u) for u in allowed_sources}
    unsourced = [u for u in external if _norm(u) not in allowed]
    add("sources_verified", not unsourced, "every external link came from web research" if not unsourced else f"links not found in research: {unsourced}")
    add("booking_cta", _norm(BOOKING_URL) in {_norm(u) for u in links}, "booking link present")

    headings = [h for _, h in HEADING_RE.findall(markdown_body)]
    body_heads = [h for h in headings if h.lower() not in ("frequently asked questions",)]
    faq_qs = {f.question.strip() for f in post.faqs}
    body_heads = [h for h in body_heads if h.strip() not in faq_qs]
    share = sum(h.strip().endswith("?") for h in body_heads) / max(1, len(body_heads))
    add("question_headings", share >= t["question_heading_share_min"], f"{share:.0%} of section headings are questions")
    add("has_table", re.search(r"^\|.+\|\s*$", markdown_body, re.M) is not None, "contains a Markdown table", hard=False)

    lower = markdown_body.lower()
    visible = plain_text(markdown_body).lower()  # count brand in visible text, not in URLs
    brand = len(re.findall(r"21\s?degrees", visible))
    add("brand_mentions", t["brand_mentions"][0] <= brand <= t["brand_mentions"][1], f"{brand} brand mentions (target {t['brand_mentions'][0]}-{t['brand_mentions'][1]})", hard=False)
    legal = lower.count("advisory services private limited")
    add("legal_name", legal <= t["legal_name_max"], f"legal name used {legal}x (max {t['legal_name_max']})")
    hits = [p for p in BANNED_PHRASES if p in lower]
    add("banned_phrases", not hits, "none" if not hits else f"found: {hits}")
    return checks


def failures(checks: list[Check], hard_only: bool = True) -> list[Check]:
    return [c for c in checks if not c.ok and (c.hard or not hard_only)]


def report(checks: list[Check]) -> str:
    return "\n".join(f"{'PASS' if c.ok else ('FAIL' if c.hard else 'WARN')}  {c.name}: {c.detail}" for c in checks)


INLINE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".svg")


def image_checks(post, work_dir) -> list[Check]:
    """At least 2 contextual in-article images, each with a file, alt text and a real heading."""
    from pathlib import Path
    work_dir = Path(work_dir)
    out = []
    n = len(post.inline_images)
    # Soft checks: publish fills any gap with a backup image (Openverse photo or key-point card).
    out.append(Check("inline_images", n >= 2, f"{n} in-article images planned (2+ wanted; publish adds backups)", hard=False))
    headings = {s.heading.strip().lower() for s in post.sections}
    missing, bad_heading = [], []
    for i, img in enumerate(post.inline_images, 1):
        if not any((work_dir / f"inline-{i}{ext}").exists() for ext in INLINE_EXT):
            missing.append(i)
        if img.after_heading.strip().lower() not in headings:
            bad_heading.append(img.after_heading)
    out.append(Check("inline_image_files", not missing, "all image files present" if not missing else f"missing inline-N file for: {missing} (publish adds backups)", hard=False))
    out.append(Check("inline_image_placement", not bad_heading, "every image sits under a real section" if not bad_heading else f"unknown headings: {bad_heading} (publish re-places them)", hard=False))
    return out
