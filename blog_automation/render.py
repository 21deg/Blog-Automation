"""Turn a BlogPost into Markdown (with front matter) and WordPress-ready HTML."""
from __future__ import annotations

import html
import json

import markdown as md_lib


def to_markdown(post, front_matter: bool = False) -> str:
    parts = []
    if front_matter:
        fm = {
            "title_tag": post.title_tag, "meta_description": post.meta_description, "slug": post.slug,
            "focus_keyword": post.focus_keyword, "secondary_keywords": post.secondary_keywords,
            "category": post.pillar, "image_alt": post.image_alt, "image_prompt": post.image_prompt,
        }
        parts.append("---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()) + "\n---\n")
    parts.append(f"# {post.h1}\n")
    parts.append(f"> **Quick answer:** {post.quick_answer}\n")
    parts.append(post.hook.strip() + "\n")
    for s in post.sections:
        parts.append(f"## {s.heading.lstrip('# ').strip()}\n\n{s.body_markdown.strip()}\n")
    parts.append(f"## The bottom line\n\n{post.bottom_line.strip()}\n")
    parts.append("## Frequently asked questions\n")
    for f in post.faqs:
        parts.append(f"### {f.question.strip()}\n\n{f.answer.strip()}\n")
    parts.append(f"**P.S.** {post.ps.strip()}\n")
    parts.append(post.cta.strip() + "\n")
    return "\n".join(parts)


def faq_jsonld(post) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": f.question,
                        "acceptedAnswer": {"@type": "Answer", "text": f.answer}} for f in post.faqs],
    }
    return json.dumps(data, ensure_ascii=False, indent=1)


def to_html(post) -> str:
    """Post body for the WordPress editor (Custom HTML block). The theme renders the H1 from the
    post title, so the H1 is left out here. Rank Math already emits BlogPosting schema, so only
    FAQPage schema is added."""
    body = to_markdown(post).split("\n", 2)[2]  # drop the "# H1" line
    content = md_lib.markdown(body, extensions=["tables", "sane_lists"])
    content = content.replace('<a href="http', '<a target="_blank" rel="noopener" href="http')
    return (f"<!-- Title tag: {html.escape(post.title_tag)} -->\n"
            f"<!-- Meta description: {html.escape(post.meta_description)} -->\n"
            f"<!-- Slug: {post.slug} | Focus keyword: {html.escape(post.focus_keyword)} -->\n"
            f"<!-- SEO: robots=index,follow | index-after-publish=true -->\n"
            f"{content}\n<script type=\"application/ld+json\">\n{faq_jsonld(post)}\n</script>\n")
