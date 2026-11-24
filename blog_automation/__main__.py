"""Command line entry point.

  python -m blog_automation trends              # show today's Google Trends (no API key needed)
  python -m blog_automation pick                # score trends with Claude, save a ranked list
  python -m blog_automation generate topics.json --rank 1
  python -m blog_automation run --count 2       # pick, then write the top N topics
"""
from __future__ import annotations

import argparse
import json
import sys

from . import generator, picker, trends
from .config import DEFAULT_GEO


def cmd_trends(args):
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


def main(argv=None):
    p = argparse.ArgumentParser(prog="blog_automation")
    p.add_argument("--geo", default=DEFAULT_GEO, help="Google Trends country code (default IN)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("trends").set_defaults(func=cmd_trends)
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
