"""Sitemap generation and Google search indexing for 21degrees.in blogs.

Generates XML sitemaps, submits URLs for indexing, and provides meta tags
for search engine optimization.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from .config import SITE, POST_INVENTORY
from .wordpress import list_posts


def generate_sitemap(output_path: Path | None = None) -> str:
    """Generate sitemap.xml for all published blog posts.

    Returns XML string. If output_path given, writes to file.
    """
    root = ET.Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root.set("xmlns:image", "http://www.google.com/schemas/sitemap-image/1.1")
    root.set("xmlns:news", "http://www.google.com/schemas/sitemap-news/0.9")

    # Add static pages
    static_pages = [
        {"loc": SITE, "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{SITE}/accounts/", "priority": "0.8", "changefreq": "monthly"},
        {"loc": f"{SITE}/blog/", "priority": "0.9", "changefreq": "daily"},
    ]

    for page in static_pages:
        url_elem = ET.SubElement(root, "url")
        ET.SubElement(url_elem, "loc").text = page["loc"]
        ET.SubElement(url_elem, "priority").text = page["priority"]
        ET.SubElement(url_elem, "changefreq").text = page["changefreq"]
        ET.SubElement(url_elem, "lastmod").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Add blog posts from WordPress
    try:
        posts = list_posts(statuses="publish")
        for post in posts:
            url_elem = ET.SubElement(root, "url")
            ET.SubElement(url_elem, "loc").text = post.get("link") or f"{SITE}/{post['slug']}/"

            # Parse and format modified date
            if post.get("date"):
                try:
                    dt = datetime.fromisoformat(post["date"].replace("Z", "+00:00"))
                    lastmod = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, AttributeError):
                    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            ET.SubElement(url_elem, "lastmod").text = lastmod
            ET.SubElement(url_elem, "changefreq").text = "monthly"
            ET.SubElement(url_elem, "priority").text = "0.7"
    except Exception as e:
        print(f"Warning: Could not fetch posts from WordPress: {e}")

    # Add posts from inventory if available
    if POST_INVENTORY.exists():
        try:
            with open(POST_INVENTORY) as f:
                inventory = json.load(f)
                added_urls = {post.get("link") or f"{SITE}/{post['slug']}/" for post in posts}

                for post in inventory:
                    url = post.get("url", "")
                    if url and url not in added_urls:
                        url_elem = ET.SubElement(root, "url")
                        ET.SubElement(url_elem, "loc").text = url

                        if post.get("modified"):
                            try:
                                dt = datetime.fromisoformat(post["modified"].replace("Z", "+00:00"))
                                lastmod = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                            except (ValueError, AttributeError):
                                lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        else:
                            lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                        ET.SubElement(url_elem, "lastmod").text = lastmod
                        ET.SubElement(url_elem, "changefreq").text = "monthly"
                        ET.SubElement(url_elem, "priority").text = "0.7"
        except Exception as e:
            print(f"Warning: Could not read post inventory: {e}")

    xml_str = ET.tostring(root, encoding="unicode")
    xml_with_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(xml_with_declaration)
        print(f"Sitemap written to {output_path}")

    return xml_with_declaration


def get_indexing_meta_tags() -> dict:
    """Get meta tags for search engine indexing.

    Returns dict with standard SEO/indexing meta tags.
    """
    return {
        "robots": "index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large",
        "googlebot": "index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large",
        "bingbot": "index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large",
        "revisit-after": "7 days",
    }


def add_indexing_headers_to_html(html: str, meta_tags: dict | None = None) -> str:
    """Add indexing meta tags to HTML document head.

    Args:
        html: HTML string to modify
        meta_tags: Dict of meta tag name -> content. Uses defaults if None.

    Returns:
        HTML string with meta tags added to head.
    """
    if meta_tags is None:
        meta_tags = get_indexing_meta_tags()

    if "<head>" not in html and "<HEAD>" not in html:
        # No head tag, return as-is
        return html

    # Build meta tag HTML
    meta_lines = []
    for name, content in meta_tags.items():
        meta_lines.append(f'  <meta name="{name}" content="{content}" />')

    meta_html = "\n".join(meta_lines) + "\n"

    # Insert after head tag
    if "<head>" in html:
        html = html.replace("<head>", "<head>\n" + meta_html, 1)
    elif "<HEAD>" in html:
        html = html.replace("<HEAD>", "<HEAD>\n" + meta_html, 1)

    return html


def get_robots_txt() -> str:
    """Generate robots.txt content for the site.

    Allows search engine crawlers and disallows wp-admin and other admin paths.
    """
    return """User-agent: *
Allow: /
Disallow: /wp-admin/
Disallow: /wp-login.php
Disallow: /wp-includes/
Disallow: /wp-content/plugins/
Disallow: /wp-content/themes/
Disallow: /*.json$
Disallow: /?s=
Crawl-delay: 1

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

Sitemap: https://21degrees.in/sitemap.xml
"""


def get_xml_sitemap_index(post_count: int = 0) -> str:
    """Generate sitemap index for large sites with multiple sitemaps.

    Args:
        post_count: Number of posts. If > 50000, generates index for split sitemaps.

    Returns:
        XML string for sitemap index.
    """
    root = ET.Element("sitemapindex")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Main sitemap
    sitemap_elem = ET.SubElement(root, "sitemap")
    ET.SubElement(sitemap_elem, "loc").text = f"{SITE}/sitemap.xml"
    ET.SubElement(sitemap_elem, "lastmod").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # For large sites, add separate sitemaps
    if post_count > 50000:
        sitemap_elem = ET.SubElement(root, "sitemap")
        ET.SubElement(sitemap_elem, "loc").text = f"{SITE}/sitemap-news.xml"
        ET.SubElement(sitemap_elem, "lastmod").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    xml_str = ET.tostring(root, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
