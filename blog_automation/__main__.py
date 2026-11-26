"""Command line entry point.

  python -m blog_automation trends              # show today's Google Trends (no API key needed)
  python -m blog_automation pick                # score trends with Claude, save a ranked list
  python -m blog_automation generate topics.json --rank 1
  python -m blog_automation run --count 2       # pick, then write the top N topics

Without an API key (Claude in a Claude Code session does the writing):
  python -m blog_automation backlog --count 7   # unused evergreen topics
  python -m blog_automation finalize post.json sources.json [--research notes.md]
  python -m blog_automation slots --count 10    # today's publish times
  python -m blog_automation publish output/<folder> --slot 1 --count 10
  python -m blog_automation digest              # today's review email text
  python -m blog_automation wp-check            # verify the WordPress login
  python -m blog_automation fetch URL [URL...]  # readable text of a page, for research
  python -m blog_automation image output/<folder> [--post-id N]  # featured image (+ attach)
"""
from __future__ import annotations

import argparse
import json
import sys

from . import generator, picker, publisher, trends, wordpress
from .config import DEFAULT_GEO


def cmd_trends(args):
    if args.by_category:
        pools = trends.bucketed(trends.fetch_trending_now(args.geo), per_bucket=args.per_bucket)
        if args.json:
            print(json.dumps(pools, ensure_ascii=False, indent=1))
            return
        for b in trends.BUCKETS:
            print(f"\n== {b['name']} (target {b['target']}) ==")
            for i, t in enumerate(pools[b["name"]], 1):
                print(f"{i:>2}. {t['volume']:>7,}+  {t['query']}  [{', '.join(t['categories'])}]  related: {', '.join(t['related'][:4])}")
        return
    items = trends.fetch_trends(args.geo)
    for t in sorted(items, key=lambda t: t.traffic, reverse=True):
        print(f"{t.traffic_label:>8}  {t.query}")
        for n in t.news[:2]:
            print(f"          - {n.title} ({n.source})")


def cmd_pick(args):
    rows = picker.score(trends.fetch_trends(args.geo))
    jpath, mpath = picker.save(rows)
    print(open(mpath).read())
    print(f"Saved {jpath}")
    return rows


def cmd_generate(args):
    rows = json.load(open(args.topics))
    topic = rows[args.rank - 1]
    result = generator.generate(topic, max_revisions=args.revisions)
    print(f"\nSaved to {result['folder']} ({'all checks passed' if result['passed'] else 'some checks still failing; review checks.txt'})")


def cmd_run(args):
    rows = cmd_pick(args)
    chosen = [r for r in rows if r["angle_type"] != "none" and r["fit"] >= args.min_fit][: args.count]
    if not chosen:
        print("No trend scored high enough today. Lower --min-fit or try again later.")
        return
    for topic in chosen:
        print(f"\n=== {topic['working_title']} (score {topic['score']})")
        result = generator.generate(topic, max_revisions=args.revisions)
        print(f"Saved to {result['folder']}")


def cmd_finalize(args):
    r = generator.finalize(args.post, args.sources, args.research)
    print(f"Saved to {r['folder']} ({'PASSED' if r['passed'] else 'FAILED: fix and re-run finalize'})")
    sys.exit(0 if r["passed"] else 2)


def cmd_backlog(args):
    if args.mark:
        publisher.backlog_mark(args.mark)
        print("Marked used:", ", ".join(args.mark))
        return
    print(json.dumps(publisher.backlog_next(args.count), ensure_ascii=False, indent=1))


def cmd_slots(args):
    for i, s in enumerate(publisher.next_slots(args.count), 1):
        print(i, s.strftime("%Y-%m-%d %H:%M IST"))


def cmd_publish(args):
    if args.window:
        from .config import SCHEDULE
        first, last = SCHEDULE["windows"][args.window]
        at = publisher.next_free_slot(SCHEDULE["batch"], review_hours=args.review_hours, last_hour=last, first_hour=first)
        e = publisher.publish_folder(args.folder, at, force=args.force, draft=args.draft, source=args.source)
        print(json.dumps(e, ensure_ascii=False, indent=1))
        return
    at = (publisher.next_slots(args.count, review_hours=args.review_hours, last_hour=args.last_hour)[args.slot - 1]
          if args.slot else publisher.next_free_slot(args.count, review_hours=args.review_hours, last_hour=args.last_hour))
    e = publisher.publish_folder(args.folder, at, force=args.force, draft=args.draft, source=args.source)
    print(json.dumps(e, ensure_ascii=False, indent=1))


def cmd_digest(args):
    subject, body = publisher.digest()
    print(subject + "\n\n" + body)


def cmd_fetch(args):
    from .fetch import fetch_text
    for u in args.urls:
        try:
            print(json.dumps(fetch_text(u, args.max_chars), ensure_ascii=False, indent=1))
        except Exception as e:
            print(json.dumps({"url": u, "error": str(e)}))


def cmd_image(args):
    from pathlib import Path
    from .generator import BlogPost
    from . import images
    post = BlogPost.model_validate_json((Path(args.folder) / "post.json").read_text())
    print(json.dumps(images.make_featured_image(post, args.folder, engine=args.engine), ensure_ascii=False, indent=1))
    if args.post_id:
        from pathlib import Path as P
        print(json.dumps(publisher.attach_image(args.post_id, P(args.folder)), indent=1))


def cmd_index(args):
    print(json.dumps(publisher.index_today(), ensure_ascii=False, indent=1))


def cmd_quota(args):
    print(json.dumps(publisher.quota(args.target, args.batch), ensure_ascii=False, indent=1))


def cmd_reimage(args):
    if args.plan:
        for item in json.load(open(args.plan)):
            try:
                r = publisher.reimage_post(item["id"], item.get("featured", ""), item.get("inline", []))
            except Exception as e:  # noqa: BLE001
                r = {"post": item["id"], "error": str(e)[:200]}
            print(json.dumps(r, ensure_ascii=False))
        return
    print(json.dumps(publisher.reimage_post(args.post_id, args.featured, args.inline), ensure_ascii=False, indent=1))


def cmd_wp_check(args):
    print(json.dumps(wordpress.whoami(), indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(prog="blog_automation")
    p.add_argument("--geo", default=DEFAULT_GEO, help="Google Trends country code (default IN)")
    sub = p.add_subparsers(dest="cmd", required=True)
    tr = sub.add_parser("trends", help="today's Google Trends; --by-category for the daily buckets")
    tr.add_argument("--by-category", action="store_true"); tr.add_argument("--json", action="store_true")
    tr.add_argument("--per-bucket", type=int, default=15)
    tr.set_defaults(func=cmd_trends)
    sub.add_parser("pick").set_defaults(func=cmd_pick)
    g = sub.add_parser("generate")
    g.add_argument("topics", help="topics-*.json written by `pick`")
    g.add_argument("--rank", type=int, default=1)
    g.add_argument("--revisions", type=int, default=2)
    g.set_defaults(func=cmd_generate)
    r = sub.add_parser("run")
    r.add_argument("--count", type=int, default=1)
    r.add_argument("--min-fit", type=int, default=6)
    r.add_argument("--revisions", type=int, default=2)
    r.set_defaults(func=cmd_run)
    f = sub.add_parser("finalize")
    f.add_argument("post"); f.add_argument("sources"); f.add_argument("--research")
    f.set_defaults(func=cmd_finalize)
    b = sub.add_parser("backlog")
    b.add_argument("--count", type=int, default=7); b.add_argument("--mark", nargs="*")
    b.set_defaults(func=cmd_backlog)
    s_ = sub.add_parser("slots"); s_.add_argument("--count", type=int, default=10); s_.set_defaults(func=cmd_slots)
    pb = sub.add_parser("publish")
    pb.add_argument("folder"); pb.add_argument("--slot", type=int, help="force a slot; default: next free slot")
    pb.add_argument("--window", choices=["morning", "evening"], help="publish inside this run's window (config SCHEDULE.windows)")
    pb.add_argument("--review-hours", type=float, help="hours before the first post may go live (default 4)")
    pb.add_argument("--last-hour", type=int, help="latest publish hour IST (default 20)")
    pb.add_argument("--source", default="", help="e.g. trend:law-government, trend:entertainment-games, trend:rest, backlog")
    pb.add_argument("--count", type=int, default=10, help="total posts today (spreads the slots)")
    pb.add_argument("--force", action="store_true"); pb.add_argument("--draft", action="store_true")
    pb.set_defaults(func=cmd_publish)
    sub.add_parser("digest").set_defaults(func=cmd_digest)
    sub.add_parser("wp-check").set_defaults(func=cmd_wp_check)
    ri = sub.add_parser("reimage", help="replace a post's featured and in-article images with Unsplash photos")
    ri.add_argument("post_id", type=int, nargs="?"); ri.add_argument("--featured", default="")
    ri.add_argument("--plan", help="JSON list of {id, featured, inline} to process in one go")
    ri.add_argument("--inline", nargs="+", default=[]); ri.set_defaults(func=cmd_reimage)
    qu = sub.add_parser("quota", help="posts still needed for the publishing day"); qu.add_argument("--target", type=int, default=10)
    qu.add_argument("--batch", type=int, help="max posts this run writes (the day is split into runs)")
    qu.set_defaults(func=cmd_quota)
    sub.add_parser("index", help="submit today's live posts for indexing and check the sitemap").set_defaults(func=cmd_index)
    im = sub.add_parser("image", help="make the featured image; with --post-id also upload and attach it")
    im.add_argument("folder"); im.add_argument("--post-id", type=int)
    im.add_argument("--engine", choices=["auto", "nano-banana", "card", "card-only"], default=None)
    im.set_defaults(func=cmd_image)
    fe = sub.add_parser("fetch"); fe.add_argument("urls", nargs="+"); fe.add_argument("--max-chars", type=int, default=12000)
    fe.set_defaults(func=cmd_fetch)
    args = p.parse_args(argv)
    try:
        args.func(args)
    except Exception as e:  # surface a readable message for missing keys etc.
        import anthropic
        if isinstance(e, anthropic.AuthenticationError) or "api_key" in str(e).lower() or "authentication" in str(e).lower():
            sys.exit("Claude API key missing or invalid: set ANTHROPIC_API_KEY.")
        raise


if __name__ == "__main__":
    main()
