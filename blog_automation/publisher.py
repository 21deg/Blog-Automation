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


def _inline_file(folder: Path, i: int):
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".svg"):
        f = folder / f"inline-{i}{ext}"
        if f.exists():
            return f
    return None


def ensure_inline_images(post: dict, folder: Path, minimum: int = 2, log=print) -> dict:
    """Guarantee at least `minimum` in-article images. Missing entries are added under section
    headings that have none; missing files are filled from Openverse (free, commercial-use photos,
    credited in the caption) and, failing that, a branded key-point card. Never raises."""
    from . import images
    post = dict(post)
    entries = [dict(e) for e in (post.get("inline_images") or [])]
    headings = [s["heading"] for s in post.get("sections", [])]
    # re-place entries whose heading doesn't exist
    for e in entries:
        if e.get("after_heading", "").strip().lower() not in {h.strip().lower() for h in headings}:
            used = {x["after_heading"] for x in entries}
            e["after_heading"] = next((h for h in headings if h not in used), headings[0] if headings else "")
    while len(entries) < minimum and headings:
        used = {x["after_heading"] for x in entries}
        h = next((h for h in headings[1:] + headings[:1] if h not in used), headings[0])
        entries.append({"after_heading": h, "alt": f"Illustration for: {h}", "caption": h, "prompt": "",
                        "search_query": post.get("focus_keyword", "")})
    faqs = post.get("faqs") or []
    for i, e in enumerate(entries, 1):
        if _inline_file(folder, i):
            continue
        made = False
        queries = [q for q in (e.get("search_query"), post.get("focus_keyword"), "india business office") if q]
        for q in queries:
            try:
                for cand in images.openverse_search(q):
                    try:
                        data = images._normalise(images.download_image(cand["url"]))
                    except Exception:  # noqa: BLE001
                        continue
                    (folder / f"inline-{i}.jpg").write_bytes(data)
                    e["caption"] = f"{e.get('caption', '').rstrip('.')}. {cand['credit']} via Openverse".strip(". ")
                    e["alt"] = e.get("alt") or cand["title"]
                    e["backup"] = "openverse"
                    made = True
                    break
            except Exception as ex:  # noqa: BLE001
                log(f"  Openverse search failed for '{q}': {ex}")
            if made:
                break
        if not made:
            if i - 1 < len(faqs):
                label, text = "Quick answer", f"{faqs[i - 1]['question']} {faqs[i - 1]['answer']}"
            else:
                label, text = "Key takeaway", post.get("quick_answer", post.get("h1", ""))
            (folder / f"inline-{i}.jpg").write_bytes(images.key_point_card(label, text))
            e["alt"] = e.get("alt") or f"{label}: {text[:100]}"
            e["backup"] = "key-point-card"
    post["inline_images"] = entries
    return post


def insert_inline_images(html_text: str, post: dict, folder: Path, log=print) -> tuple[str, list]:
    """Upload each inline image and place it under its section heading, after the first paragraph.
    An image that fails is skipped (and reported) rather than blocking the post."""
    import html as htmlmod
    import re
    from . import images
    placed = []
    for i, img in enumerate(post.get("inline_images") or [], 1):
        f = _inline_file(folder, i)
        if not f:
            placed.append({"n": i, "error": "file missing"})
            continue
        try:
            if f.suffix == ".svg":
                data = images.render_svg(f, folder / f"inline-{i}.rendered.jpg")
            else:
                data = images._normalise(f.read_bytes())
            media = wp.upload_media(data, f"{post['slug']}-{i}.jpg", "image/jpeg", alt_text=img["alt"], title=img["caption"])
            figure = (f'<figure class="wp-block-image size-large"><img src="{media["url"]}" alt="{htmlmod.escape(img["alt"], quote=True)}" '
                      f'class="wp-image-{media["id"]}" loading="lazy" width="1536" height="1024"/>'
                      f'<figcaption>{htmlmod.escape(img["caption"])}</figcaption></figure>')
            heading = re.escape(htmlmod.escape(img["after_heading"].strip(), quote=False))
            m = re.search(rf"<h2[^>]*>\s*{heading}\s*</h2>", html_text, re.I)
            if not m:
                m = re.search(rf"<h2[^>]*>\s*{re.escape(img['after_heading'].strip())}\s*</h2>", html_text, re.I)
            if not m:
                placed.append({"n": i, "error": f"heading not found: {img['after_heading']}"})
                continue
            p_end = html_text.find("</p>", m.end())
            nxt = html_text.find("<h2", m.end())
            pos = p_end + 4 if p_end != -1 and (nxt == -1 or p_end < nxt) else m.end()
            html_text = html_text[:pos] + "\n" + figure + "\n" + html_text[pos:]
            placed.append({"n": i, "media_id": media["id"], "url": media["url"]})
        except Exception as e:  # noqa: BLE001
            placed.append({"n": i, "error": str(e)[:150]})
    return html_text, placed


def next_free_slot(count: int = 10, review_hours: float | None = None, last_hour: int | None = None) -> datetime:
    """The earliest of today's slots that no scheduled or published post already occupies
    (posts within 20 minutes of a slot count as occupying it). Fixes double-booked times."""
    slots = next_slots(count, review_hours=review_hours, last_hour=last_hour)
    wp.list_posts.cache_clear()
    taken = []
    for p in wp.list_posts("publish,future"):
        try:
            taken.append(datetime.fromisoformat(p["date"]).replace(tzinfo=wp.IST))
        except ValueError:
            continue
    for s in slots:
        if all(abs((s - t).total_seconds()) > 20 * 60 for t in taken):
            return s
    # every slot used (more than `count` posts today): go 20 minutes after the latest one
    from datetime import timedelta
    return max(taken) + timedelta(minutes=20)


def publish_folder(folder: str, publish_at: datetime | None, force: bool = False, draft: bool = False,
                   source: str = "") -> dict:
    folder_p = Path(folder)
    post = json.loads((folder_p / "post.json").read_text())
    checks = (folder_p / "checks.txt").read_text()
    if "FAIL" in checks and not force:
        raise SystemExit(f"{folder}: checks are failing; fix the post or pass --force.\n{checks}")
    existing = wp.list_posts()
    clash = [p for p in existing if p["slug"] == post["slug"]]
    if clash:
        raise SystemExit(f"A post with slug '{post['slug']}' already exists: {clash[0]['link']}")
    post = ensure_inline_images(post, folder_p)
    content, inline = insert_inline_images((folder_p / "post.html").read_text(), post, folder_p)
    for item, entry in zip(inline, post["inline_images"]):
        if entry.get("backup"):
            item["backup"] = entry["backup"]
    created = wp.create_post(
        title=post["h1"], content=content, slug=post["slug"],
        excerpt=post["meta_description"], categories=CATEGORY_IDS.get(post["pillar"], CATEGORY_IDS["default"]),
        publish_at=None if draft else publish_at, status="draft" if draft else None)
    wp.set_seo(created["id"], title_tag=post["title_tag"], meta_description=post["meta_description"],
               focus_keyword=post["focus_keyword"])
    image = attach_image(created["id"], folder_p)
    entry = {**created, "title": post["h1"], "title_tag": post["title_tag"], "folder": str(folder_p),
             "publish_at_ist": publish_at.astimezone(wp.IST).strftime("%d %b %Y, %I:%M %p IST") if publish_at and not draft else "draft",
             "image": image, "inline_images": inline, "source": source,
             "warnings": [l for l in checks.splitlines() if l.startswith(("WARN", "FAIL"))]}
    log_path = daily_log_path(datetime.now(wp.IST))
    log = _load(log_path, [])
    log.append(entry)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=1))
    return entry


def attach_image(post_id: int, folder: Path) -> dict:
    """Make (if needed), upload and set the featured image. Never blocks publishing: on failure the
    post keeps going and the digest flags the missing image."""
    from .generator import BlogPost
    from . import images
    try:
        post = BlogPost.model_validate_json((folder / "post.json").read_text())
        meta_path = folder / "featured.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() and (folder / "featured.jpg").exists() \
            else images.make_featured_image(post, str(folder))  # uses featured.svg when present
        media = wp.upload_media((folder / "featured.jpg").read_bytes(), f"{post.slug}.jpg", "image/jpeg",
                                alt_text=post.image_alt, title=post.h1)
        wp.set_featured_image(post_id, media["id"])
        return {"engine": meta["engine"], "media_id": media["id"], "url": media["url"],
                "prompt": meta.get("prompt", "")}
    except Exception as e:  # noqa: BLE001 - an image problem must not stop the post
        return {"engine": "none", "error": str(e)[:200]}


def next_slots(count: int, now: datetime | None = None, review_hours: float | None = None,
               last_hour: int | None = None) -> list[datetime]:
    """Publish times for today's posts, spread across the configured IST window and starting
    no earlier than min_review_hours from now. If today's window is (nearly) over, use tomorrow's."""
    from datetime import timedelta
    now = (now or datetime.now(wp.IST)).astimezone(wp.IST)
    first, last = SCHEDULE["first_hour_ist"], last_hour or SCHEDULE["last_hour_ist"]
    earliest = now + timedelta(hours=SCHEDULE["min_review_hours"] if review_hours is None else review_hours)
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
    trend_n = sum(1 for e in log if str(e.get("source", "")).startswith("trend"))
    backlog_n = sum(1 for e in log if str(e.get("source", "")).startswith("backlog"))
    lines = [f"Sources: {trend_n} from Google Trends, {backlog_n} from the evergreen backlog.",
             f"{len(log)} posts are scheduled to go live today. Review each one before its publish time.",
             "To stop a post, open it and switch it to Draft, or move it to Trash.", ""]
    for i, e in enumerate(log, 1):
        lines += [f"{i}. {e['title']}", f"   Source: {e.get('source') or 'unknown'}",
                  f"   Goes live: {e['publish_at_ist']}", f"   Edit: {e['edit_link']}",
                  f"   Preview: {e['link']}"]
        img = e.get("image") or {}
        if img.get("engine") == "branded-card":
            lines.append("   Image: branded title card (the illustration could not be drawn). For an illustration, paste this into the free Gemini app or ChatGPT,")
            lines.append("   then replace the featured image in WordPress:")
            lines.append(f"   {img.get('prompt', '')}")
        elif img.get("engine") == "none":
            lines.append(f"   Image: MISSING, add one before it goes live ({img.get('error', '')[:80]})")
        bad_inline = [x for x in e.get("inline_images", []) if x.get("error")]
        ok_inline = len(e.get("inline_images", [])) - len(bad_inline)
        backups = [x["backup"] for x in e.get("inline_images", []) if x.get("backup")]
        lines.append(f"   In-article images: {ok_inline} placed" + (f", {len(bad_inline)} failed" if bad_inline else "")
                     + (f" (backups used: {', '.join(backups)})" if backups else ""))
        lines += [f"   Check: {w}" for w in e.get("warnings", [])]
        lines.append("")
    lines.append("Indexing: Rank Math submits each post to Bing and IndexNow when it goes live; Google picks it up from the sitemap.")
    return subject, "\n".join(lines)


def index_today(day: datetime | None = None) -> dict:
    """Submit every post that went live today to IndexNow (Bing, Yandex and others, via Rank Math)
    and check each one is in the sitemap Google reads."""
    import urllib.request
    day = (day or datetime.now(wp.IST)).astimezone(wp.IST)
    wp.list_posts.cache_clear()
    live = [p for p in wp.list_posts("publish") if p["date"][:10] == day.strftime("%Y-%m-%d")]
    urls = [p["link"] for p in live]
    result = wp.submit_for_indexing(urls) if urls else {"message": "nothing published today"}
    req = urllib.request.Request("https://21degrees.in/post-sitemap.xml", headers={"User-Agent": "Mozilla/5.0"})
    sitemap = urllib.request.urlopen(req, timeout=60).read().decode(errors="ignore")
    missing = [u for u in urls if u not in sitemap]
    return {"submitted": urls, "indexnow": result, "missing_from_sitemap": missing}
