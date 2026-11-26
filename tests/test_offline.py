"""Tests that run without a Claude API key. Run: python -m pytest tests -q"""
import json
from pathlib import Path

import httpx2 as httpx
import pytest

from blog_automation import llm, picker, render, validate
from blog_automation.config import BOOKING_URL
from blog_automation.generator import FAQ, BlogPost, Section
from blog_automation.trends import parse_rss, parse_traffic

FIX = Path(__file__).parent / "fixtures"


def test_parse_traffic():
    assert parse_traffic("20000+") == 20000
    assert parse_traffic("") == 0


def test_parse_rss_fixture():
    trends = parse_rss((FIX / "trends_in.xml").read_text())
    assert trends and all(t.query for t in trends)
    assert any(t.news and t.news[0].url.startswith("http") for t in trends)


def _trend(q, traffic):
    from blog_automation.trends import Trend
    return Trend(query=q, traffic=traffic, traffic_label=f"{traffic}+", published="", geo="IN")


def _idea(q, angle, fit):
    return picker.TopicIdea(trend_query=q, angle_type=angle, fit=fit, finance_angle="x", pillar="cash-flow",
                            target_keyword="cash flow management", working_title="t", shelf_life="weeks", why="y")


def test_rank_news_slightly_ahead_but_sport_kept():
    trends = [_trend("rbi policy", 5000), _trend("ind vs sa", 5000), _trend("actor death", 5000)]
    rows = picker.rank(trends, [_idea("ind vs sa", "metaphor", 8), _idea("rbi policy", "direct", 8),
                                _idea("actor death", "none", 9)])
    by = {r["trend_query"]: r["score"] for r in rows}
    assert by["rbi policy"] > by["ind vs sa"] > 0          # small news boost, sport still scores
    assert by["ind vs sa"] / by["rbi policy"] > 0.8          # ...and only slightly behind
    assert by["actor death"] == 0


def test_rank_strong_sport_beats_weak_news():
    trends = [_trend("rbi policy", 2000), _trend("ipl auction", 50000)]
    rows = picker.rank(trends, [_idea("rbi policy", "direct", 5), _idea("ipl auction", "metaphor", 9)])
    assert rows[0]["trend_query"] == "ipl auction"


SRC1 = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=1"
SRC2 = "https://economictimes.indiatimes.com/news/economy/policy/repo-rate.cms"
INTERNAL = ["https://21degrees.in/accounts/", "https://21degrees.in/",
            "https://21degrees.in/what-financial-metrics-should-a-cfo-track-monthly/"]


def make_post(words_per_section=330, **over):
    filler = ("Your working capital loan resets with the repo rate. Check the spread in your sanction letter. "
              "Ask your bank when the reset happens. ") * (words_per_section // 25)
    sections = [
        Section(heading="What did the RBI announce?", body_markdown=f"The [RBI]({SRC1}) cut the repo rate. "
                f"[Economic Times]({SRC2}) reported the details. " + filler),
        Section(heading="How does the repo rate affect my loan?", body_markdown=filler +
                "\n\n| Loan | Old rate | New rate |\n|---|---|---|\n| ₹50 lakh CC | 10.5% | 10.25% |\n"),
        Section(heading="What should founders do this month?", body_markdown=filler +
                f" Track the [right monthly metrics]({INTERNAL[2]})."),
        Section(heading="A worked example for a Noida manufacturer", body_markdown=filler),
        Section(heading="Where does a Virtual CFO help?", body_markdown=f"21DEGREES reviews your [accounts]({INTERNAL[0]}) "
                f"and renegotiates bank terms. Learn more about [21DEGREES Virtual CFO services]({INTERNAL[1]}). " + filler[:400]),
    ]
    data = dict(
        focus_keyword="repo rate", secondary_keywords=["working capital loan"], pillar="funding-banking",
        title_tag="Repo Rate Cut: What It Means for Your Business Loan",
        meta_description="The RBI repo rate cut changes what you pay on working capital loans. See how it affects SMEs in India and what founders should do this month.",
        slug="repo-rate-cut-business-loan", h1="RBI Just Cut Rates. Your Bank May Not Pass It On.",
        quick_answer=("The RBI cut the repo rate, so loans linked to an external benchmark should get cheaper at the next reset. "
                      "Most SME working capital loans reset within three months, but banks only pass the cut on if your loan is "
                      "linked to the repo rate. Check your sanction letter."),
        hook="The RBI blinked.\nRates are down.\nYour EMI is not. Yet.",
        sections=sections, bottom_line="Rates moved. Make sure your loan moves with them.",
        faqs=[FAQ(question=f"Question {i}?", answer="A short answer. It has two sentences.") for i in range(5)],
        ps="Banks reset rates quarterly. Ask yours this week, with 21DEGREES on the call.",
        cta=f"[Book a 30-minute call with 21DEGREES]({BOOKING_URL}).", image_alt="RBI building", image_prompt="RBI building at dusk",
    )
    data.update(over)
    return BlogPost(**data)


def inv():
    return {validate._norm(u) for u in INTERNAL}


def test_good_post_passes_hard_checks():
    post = make_post()
    body = render.to_markdown(post)
    checks = validate.run(post, body, {SRC1, SRC2}, inv())
    assert not validate.failures(checks), validate.report(checks)


def test_bad_post_is_caught():
    post = make_post(words_per_section=40, title_tag="x" * 80, slug="Bad_Slug",
                     hook="You are an idiot. Pioneers, Not Imitators.")
    body = render.to_markdown(post).replace(SRC2, "https://made-up.example.com/stat")
    names = {c.name for c in validate.failures(validate.run(post, body, {SRC1, SRC2}, inv()))}
    assert {"length", "title_tag", "slug", "banned_phrases", "sources_verified"} <= names


def test_invented_internal_link_is_caught():
    post = make_post()
    body = render.to_markdown(post).replace(INTERNAL[2], "https://21degrees.in/not-a-real-post/")
    names = {c.name for c in validate.failures(validate.run(post, body, {SRC1, SRC2}, inv()))}
    assert "internal_links_real" in names


def test_html_has_faq_schema_and_no_h1():
    html = render.to_html(make_post())
    assert "<h1" not in html and '"@type": "FAQPage"' in html and "<table>" in html


def test_sdk_request_shape(monkeypatch):
    """Capture the HTTP request the SDK builds for a structured-output call (no network)."""
    import anthropic
    captured = {}

    def handler(request: httpx.Request):
        captured["body"] = json.loads(request.content)
        captured["beta"] = request.headers.get("anthropic-beta")
        return httpx.Response(401, json={"type": "error", "error": {"type": "authentication_error", "message": "x"}})

    fake = anthropic.Anthropic(api_key="test", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(llm, "_client", fake)
    with pytest.raises(anthropic.AuthenticationError):
        llm.parse(system="s", messages=[{"role": "user", "content": "hi"}], output_format=picker.TopicScores, effort="medium")
    b = captured["body"]
    assert b["model"] == "claude-opus-5-5" and b["fallbacks"] == "default" and b["stream"] is True
    assert b["output_config"]["effort"] == "medium" and b["output_config"]["format"]["type"] == "json_schema"
    assert "server-side-fallback-2026-07-01" in captured["beta"]


def test_slots_respect_window_and_review_time():
    from datetime import datetime
    from blog_automation import publisher, wordpress as wp
    morning = publisher.next_slots(10, datetime(2026, 11, 25, 6, 0, tzinfo=wp.IST))
    assert morning[0].hour == 11 and morning[-1].hour == 20 and len(morning) == 10
    noon = publisher.next_slots(10, datetime(2026, 11, 25, 9, 30, tzinfo=wp.IST))
    assert noon[0] >= datetime(2026, 11, 25, 13, 30, tzinfo=wp.IST) and noon[-1].hour == 20
    night = publisher.next_slots(10, datetime(2026, 11, 25, 22, 0, tzinfo=wp.IST))
    assert night[0].day == 26 and night[0].hour == 11


def test_svg_safety_checks():
    from blog_automation import images
    images.check_svg(open("blog_automation/assets/illustration_example.svg").read())
    for bad in ['<svg xmlns="http://www.w3.org/2000/svg"><script>x</script></svg>',
                '<svg xmlns="http://www.w3.org/2000/svg"><image href="http://x/y.png"/></svg>',
                '<svg><rect></svg>']:
        with pytest.raises(Exception):
            images.check_svg(bad)


def test_inline_images_inserted_under_heading(monkeypatch, tmp_path):
    from blog_automation import publisher, wordpress as wp
    from PIL import Image
    Image.new("RGB", (800, 600), "white").save(tmp_path / "inline-1.jpg")
    monkeypatch.setattr(wp, "upload_media", lambda *a, **k: {"id": 77, "url": "https://21degrees.in/x.jpg"})
    html = "<h2>What happened?</h2>\n<p>First para.</p>\n<p>Second.</p>\n<h2>Next</h2><p>x</p>"
    post = {"slug": "s", "inline_images": [{"after_heading": "What happened?", "alt": "a", "caption": "c", "prompt": "p"},
                                           {"after_heading": "Next", "alt": "a", "caption": "c", "prompt": "p"}]}
    out, placed = publisher.insert_inline_images(html, post, tmp_path)
    assert out.index("<figure") > out.index("First para.</p>") and out.index("<figure") < out.index("Second.")
    assert placed[0]["media_id"] == 77 and "error" in placed[1]  # second file missing -> reported, not fatal


def test_ensure_inline_images_fills_gaps(monkeypatch, tmp_path):
    from blog_automation import publisher, images
    monkeypatch.setattr(images, "openverse_search", lambda q, n=8: [])  # offline: force the card backup
    post = {"slug": "s", "h1": "H", "quick_answer": "Short answer.", "focus_keyword": "gst",
            "sections": [{"heading": "A?"}, {"heading": "B?"}, {"heading": "C"}],
            "faqs": [{"question": "Q1?", "answer": "A1."}], "inline_images": []}
    out = publisher.ensure_inline_images(post, tmp_path)
    assert len(out["inline_images"]) == 2
    assert (tmp_path / "inline-1.jpg").exists() and (tmp_path / "inline-2.jpg").exists()
    assert {e["backup"] for e in out["inline_images"]} == {"key-point-card"}


def test_morning_and_evening_windows():
    from datetime import datetime
    from blog_automation import publisher, wordpress as wp
    m = publisher.next_slots(5, datetime(2026, 11, 26, 5, 33, tzinfo=wp.IST), first_hour=10, last_hour=12)
    assert [s.strftime("%H:%M") for s in m] == ["10:00", "10:30", "11:00", "11:30", "12:00"]
    e = publisher.next_slots(5, datetime(2026, 11, 26, 11, 33, tzinfo=wp.IST), first_hour=17, last_hour=19)
    assert e[0].strftime("%H:%M") == "17:00" and e[-1].strftime("%H:%M") == "19:00"
    late = publisher.next_slots(5, datetime(2026, 11, 26, 9, 0, tzinfo=wp.IST), first_hour=10, last_hour=12)
    assert late[0].day == 27  # morning window already inside the review period -> next morning
