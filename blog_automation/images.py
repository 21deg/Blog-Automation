"""Featured images: Nano Banana (Gemini image API) when a key is available, otherwise a branded
title card drawn locally. Style rules live in prompts/image_style.md."""
from __future__ import annotations

import base64
import io
import json
import os
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import IMAGES

FONTS = Path(__file__).resolve().parent / "assets" / "fonts"
NAVY, TEAL, BEIGE, SAFFRON, OFFWHITE = "#1F3A5F", "#3E8E8B", "#F3E6D3", "#E8A33D", "#FBF7F0"
SIZE = (1536, 1024)

STYLE = ("Flat editorial illustration with clean vector shapes, soft shading and subtle paper grain. "
         "Palette: deep navy #1F3A5F, muted teal #3E8E8B, warm beige background #F3E6D3, one saffron accent "
         "#E8A33D. Indian people and settings. Money shown only as Indian rupee notes or the ₹ sign, never "
         "dollars. One clear focal scene, generous empty space, subject centred so it crops well. "
         "No text, letters or numbers in the image. No logos, watermarks, real people's likenesses or "
         "copyrighted characters. Landscape 3:2.")


def build_prompt(post) -> str:
    return (f"Featured image for an Indian business-finance blog post titled \"{post.h1}\". "
            f"Scene: {post.image_prompt.rstrip('.')}. {STYLE}")


# ---------------------------------------------------------------- Nano Banana (Gemini API)

class ImageAPIUnavailable(RuntimeError):
    pass


def _find_image(obj):
    """Return (bytes, mime) for the last base64 image anywhere in the API response."""
    found = None
    if isinstance(obj, dict):
        mime = obj.get("mime_type") or obj.get("mimeType") or ""
        data = obj.get("data")
        if isinstance(data, str) and mime.startswith("image/") and len(data) > 1000:
            found = (base64.b64decode(data), mime)
        for v in obj.values():
            found = _find_image(v) or found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_image(v) or found
    return found


def generate_nano_banana(prompt: str) -> tuple[bytes, str]:
    # In the cloud environment the proxy replaces this header with the saved key; elsewhere set
    # GEMINI_API_KEY.
    key = os.environ.get("GEMINI_API_KEY") or "proxy-injected"
    body = {"model": IMAGES["model"], "input": [{"type": "text", "text": prompt}],
            "response_format": {"type": "image", "mime_type": "image/jpeg",
                                "aspect_ratio": IMAGES["aspect_ratio"], "image_size": IMAGES["image_size"]}}
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions", data=json.dumps(body).encode(),
        method="POST", headers={"x-goog-api-key": key, "Content-Type": "application/json",
                                "Api-Revision": IMAGES["api_revision"]})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")[:300]
        if e.code in (400, 401, 403, 429):
            raise ImageAPIUnavailable(f"Gemini image API {e.code}: {detail}") from e
        raise
    except urllib.error.URLError as e:
        raise ImageAPIUnavailable(f"Gemini image API unreachable: {e}") from e
    found = _find_image(payload)
    if not found:
        raise ImageAPIUnavailable("Gemini returned no image (it may have declined the prompt).")
    return found


# ---------------------------------------------------------------- free fallback: branded card

def _font(weight: str, size: int):
    return ImageFont.truetype(str(FONTS / f"Inter-{weight}.otf"), size)


def _wrap(draw, text, font, max_width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            lines.append(line)
            line = w
    lines.append(line)
    return lines


CARD_LABELS = {
    "virtual-cfo": "VIRTUAL CFO", "gst-compliance": "GST & COMPLIANCE", "cash-flow": "CASH FLOW",
    "funding-banking": "FUNDING & BANKING", "industry-playbooks": "INDUSTRY PLAYBOOK",
    "tax-planning": "TAX PLANNING", "business-growth": "BUSINESS GROWTH",
}


def branded_card(title: str, pillar: str) -> bytes:
    """A clean title card in the house palette: eyebrow, big title, brand footer, degree-ring motif."""
    img = Image.new("RGB", SIZE, BEIGE)
    d = ImageDraw.Draw(img)
    W, H = SIZE
    # degree-ring motif echoing the 21° mark, bleeding off the right edge
    cx, cy, r = W - 150, 380, 290
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=TEAL, width=44)
    dx, dy, dr = cx - r - 40, cy - r - 10, 44
    d.ellipse([dx - dr, dy - dr, dx + dr, dy + dr], outline=SAFFRON, width=18)
    # left content panel
    x, maxw = 110, 840
    eyebrow = CARD_LABELS.get(pillar, "FINANCE")
    d.rectangle([x, 150, x + 90, 162], fill=SAFFRON)
    d.text((x, 190), eyebrow, font=_font("SemiBold", 34), fill=TEAL)
    size = 92
    while size > 56:
        font = _font("Bold", size)
        lines = _wrap(d, title, font, maxw)
        if len(lines) <= 4:
            break
        size -= 6
    y = 260
    for line in lines[:5]:
        d.text((x, y), line, font=font, fill=NAVY)
        y += int(size * 1.16)
    # footer band
    d.rectangle([0, H - 140, W, H], fill=NAVY)
    d.text((x, H - 103), "21DEGREES", font=_font("Bold", 44), fill=OFFWHITE)
    d.text((x + 290, H - 95), "Virtual CFO  ·  Accounting  ·  Compliance", font=_font("Medium", 32), fill="#C9D6E3")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- orchestration

def _normalise(data: bytes) -> bytes:
    """Crop/resize to 1536x1024 JPEG."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    tw, th = SIZE
    scale = max(tw / im.width, th / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    left, top = (im.width - tw) // 2, (im.height - th) // 2
    im = im.crop((left, top, left + tw, top + th))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True)
    return buf.getvalue()


RENDER_JS = Path(__file__).resolve().parent.parent / "scripts" / "render_svg.js"
USED_IDS = Path(__file__).resolve().parent.parent / "output" / "unsplash-used.json"


def used_unsplash_ids() -> set[str]:
    try:
        return set(json.loads(USED_IDS.read_text()))
    except Exception:  # noqa: BLE001
        return set()


def remember_unsplash_id(photo_id: str) -> None:
    USED_IDS.parent.mkdir(exist_ok=True)
    ids = used_unsplash_ids() | {photo_id}
    USED_IDS.write_text(json.dumps(sorted(ids)))


def check_svg(svg: str) -> None:
    import re
    import xml.etree.ElementTree as ET
    ET.fromstring(svg)  # must be well-formed
    if re.search(r"<\s*(script|image|foreignObject)\b|xlink:href=|href=\"http", svg, re.I):
        raise ValueError("SVG may not contain scripts, embedded images or external links")
    if len(svg.encode()) > 80_000:
        raise ValueError("SVG is too large (keep it under 40 KB)")


def render_svg(svg_path: Path, out: Path) -> bytes:
    import subprocess
    check_svg(svg_path.read_text())
    subprocess.run(["node", str(RENDER_JS), str(svg_path), str(out)], check=True, capture_output=True, timeout=120)
    return _normalise(out.read_bytes())


def make_featured_image(post, folder: str, engine: str | None = None, log=print) -> dict:
    """Create featured.jpg in the post folder. Returns {"path", "engine", "note"}.
    Order: Claude-drawn SVG illustration (featured.svg) if present, then Nano Banana when the
    engine allows it, then the branded card."""
    engine = engine or IMAGES["engine"]
    out = Path(folder) / "featured.jpg"
    note = ""
    data = None
    for name in ("featured-canva.jpg", "featured-canva.png", "featured-canva.webp"):
        provided = Path(folder) / name
        if data is None and provided.exists():
            try:
                data, used = _normalise(provided.read_bytes()), "canva"
            except Exception as e:  # noqa: BLE001
                note = f"Canva image unreadable: {e}"[:200]
    credit = None
    if data is None and engine in ("unsplash", "auto"):
        try:
            from . import unsplash
            photo = unsplash.first_photo([getattr(post, "featured_search_query", ""), post.focus_keyword],
                                         skip_ids=used_unsplash_ids())
            if photo:
                data, used = _normalise(unsplash.fetch(photo)), "unsplash"
                credit = {"text": unsplash.credit_text(photo), "html": unsplash.credit_html(photo), "id": photo["id"]}
                remember_unsplash_id(photo["id"])
        except Exception as e:  # noqa: BLE001
            note = f"Unsplash unavailable: {e}"[:200]
            log(f"  {note}")
    svg = Path(folder) / "featured.svg"
    if data is None and svg.exists() and engine != "card-only":
        try:
            data, used = render_svg(svg, out), "illustration"
        except Exception as e:  # noqa: BLE001
            note = f"SVG illustration failed: {e}"[:200]
            log(f"  {note}")
    if data is None and engine in ("auto", "nano-banana"):
        try:
            raw, _ = generate_nano_banana(build_prompt(post))
            data, used = _normalise(raw), "nano-banana"
        except ImageAPIUnavailable as e:
            if engine == "nano-banana":
                raise
            note = str(e)[:200]
            log(f"  Nano Banana unavailable, using branded card ({note[:80]})")
    if data is None:
        data, used = branded_card(post.title_tag, post.pillar), "branded-card"
    out.write_bytes(data)
    meta = {"path": str(out), "engine": used, "note": note, "prompt": build_prompt(post), "alt": post.image_alt,
            "credit": credit}
    (Path(folder) / "featured.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


# ---------------------------------------------------------------- in-article image backups

def openverse_search(query: str, n: int = 8) -> list[dict]:
    """Free, commercial-use images from Openverse (CC0, public domain, CC BY). CC BY needs the
    attribution text in the caption, which the caller adds."""
    from urllib.parse import urlencode
    url = "https://api.openverse.org/v1/images/?" + urlencode({
        "q": query, "license": "cc0,pdm,by", "license_type": "commercial", "page_size": n,
        "mature": "false"})
    req = urllib.request.Request(url, headers={"User-Agent": "21degrees-blog-automation"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.loads(resp.read().decode())
    out = []
    for r in data.get("results", []):
        if (r.get("width") or 0) < 800 or (r.get("height") or 0) < 450:
            continue
        lic = f"{r.get('license', '').upper()} {r.get('license_version') or ''}".strip()
        credit = "Public domain" if r.get("license") in ("cc0", "pdm") else \
            f"Photo: {r.get('creator') or 'unknown'}, CC {lic}"
        out.append({"url": r["url"], "title": r.get("title", ""), "credit": credit,
                    "landing": r.get("foreign_landing_url", "")})
    return out


def download_image(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "21degrees-blog-automation"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def key_point_card(label: str, text: str) -> bytes:
    """Last-resort in-article image: a branded card with one key point from the post."""
    img = Image.new("RGB", SIZE, OFFWHITE)
    d = ImageDraw.Draw(img)
    W, H = SIZE
    d.rectangle([0, 0, 28, H], fill=TEAL)
    d.rectangle([110, 150, 200, 162], fill=SAFFRON)
    d.text((110, 190), label.upper(), font=_font("SemiBold", 34), fill=TEAL)
    size = 64
    while size > 40:
        font = _font("SemiBold", size)
        lines = _wrap(d, text, font, 1300)
        if len(lines) <= 7:
            break
        size -= 4
    y = 270
    for line in lines[:8]:
        d.text((110, y), line, font=font, fill=NAVY)
        y += int(size * 1.3)
    d.text((110, H - 110), "21DEGREES", font=_font("Bold", 40), fill=NAVY)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90, optimize=True)
    return buf.getvalue()
