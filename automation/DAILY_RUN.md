# Daily blog run (for the scheduled Claude Code session)

Goal: **schedule this run's share (up to 5) of today's 10 posts on 21degrees.in, every one from today's Google Trends, each with a
featured image and at least 2 in-article images, then get them indexed.** Claude in this session
picks topics, researches, writes and makes images. The repo's scripts check, render, schedule,
index and build the digest. No Anthropic API key is needed.

## Hard rules
- **Never stop early and never wait for a person.** If a topic fails a check, cannot be researched,
  or a step errors, drop that topic, take the next candidate from the same bucket and carry on.
  Keep going until 10 posts are scheduled.
- Never schedule a post whose `finalize` checks fail.
- Never edit, unpublish or delete existing posts on the site.
- Only cite pages you actually read with the `fetch` command. Never invent figures, quotes,
  court cases, rulings or URLs. If a fact has no source you read, leave it out.
- Never give an existing post's keyword to a new post. Link to the older post instead.
- Skip trends about deaths, terror attacks, violence, disasters, crimes against people or
  communal conflict, and personal gossip. They are not suitable for a sales-led finance blog.

## 1. Set up
```bash
git fetch origin claude/youthful-lovelace-okbvzj && git checkout -B daily-run FETCH_HEAD
pip install -q -r requirements.txt
python -m blog_automation wp-check
```
If `wp-check` fails, retry once after a minute. If it still fails, skip to step 6 and report it.

Then check how many posts this run should write:
```bash
python -m blog_automation quota --batch 5
```
The day's 10 posts are written in **two runs of 5** (05:33 and 11:33 IST) to stay within the
5-hour usage limit. Posts already scheduled for that day count towards the 10. Write exactly
`to_write` posts (never more), keeping the bucket mix in proportion: the first run of the day
takes about 3 Law & Government, 1 Entertainment/Games and 1 other; the second run fills what is
left of 4–5 / 3 / 2 (check the titles in the `quota` output). If `to_write` is 0, skip to step 6
and report that the day is already full.

## 2. Pick topics from Google Trends (always)
```bash
mkdir -p work && python -m blog_automation trends --by-category --per-bucket 25 --json > work/trends.json
```
This reads the full Trending Now list for India (hundreds of searches with categories). Fill
these buckets, best candidates first:

| Bucket | Google Trends categories | Posts |
|---|---|---|
| `law-government` | Law and Government | 4–5 |
| `entertainment-games` | Entertainment, Games | 3 |
| `rest` | everything else (sport, business, tech, …) | 2 (3 if law-government has only 4) |

For each candidate:
- **Understand it first.** Many queries are in Hindi, Tamil, Telugu, Kannada, Malayalam,
  Marathi or Bengali. Use the related queries and a quick web search to find what the trend is
  about before judging it.
- **Find the business angle.** Ask: what does this mean for an Indian founder's money, tax,
  compliance, cash flow, pricing, hiring or growth? Law and government trends usually have a
  direct angle (new rules, court orders, deadlines, schemes, state policies). Entertainment,
  games and sport use the story as a business lesson (box-office economics, lottery and
  gaming tax, a franchise's budget, a chess champion's preparation as planning).
- Score fit 0–10 and take the highest-fit, highest-volume candidates. Prefer active trends.
- Avoid two posts on the same story or the same target keyword.

Keep the remaining candidates as **replacements**, per bucket. If a bucket runs out of usable
candidates, take the next best from `rest`. Use `python -m blog_automation backlog --count N`
only if all trend buckets are exhausted, and say so in the digest.

Write the plan to `work/plan.json`: for each slot the trend, bucket, finance angle, target keyword
and pillar, plus the replacement list.

## 3. Write each post (one subagent per post)
Work through the plan one post at a time. Use a fresh general-purpose subagent for each, so that
research doesn't fill the main context. Give the subagent the topic, angle, keyword and pillar;
`blog_automation/prompts/style_guide.md`; the `BlogPost` and `InlineImage` field lists in
`blog_automation/generator.py`; and the internal link inventory
(`analysis/data/all_posts_metadata.json` plus `SERVICE_PAGES` in `blog_automation/config.py`).

The subagent must:
1. **Research.** Find pages with web search, read them with
   `python -m blog_automation fetch <url> [<url> ...]` (WebFetch can't reach the web here). Prefer
   primary sources (government sites, gazettes, court orders, RBI, CBIC, PIB, MCA) and major
   Indian publications. Only pages `fetch` returned text for go into `sources.json`.
2. **Write** `work/<n>/post.json`, `work/<n>/sources.json` (`{"url": "title"}`) and
   `work/<n>/research.md`. Include **2 or 3 `inline_images`**, each placed under a real section
   heading: one scene that shows the story, and one that explains a point (a simple chart,
   checklist or process diagram).
3. **Make the images** (step 4) into `work/<n>/`.
4. **Check.** Run
   `python -m blog_automation finalize work/<n>/post.json work/<n>/sources.json --research work/<n>/research.md`
   and fix until it says PASSED (at most 3 attempts).
5. Report the output folder, the bucket, and pass or fail.

If a post still fails after 3 attempts, or research turns up too little to support it, mark the
topic failed and start the next replacement from the same bucket straight away.

## 4. Images (Unsplash photos, free)
All images come from **Unsplash** by default; the scripts fetch them, credit the photographer and
upload them. The writer only chooses good search phrases:
- `featured_search_query`: 2–4 plain English words for a striking, relevant photo
  (for example "indian courtroom", "petrol pump india", "chess tournament", "film set").
- each `inline_images[i].search_query`: a different phrase per image, matched to its section.
- Avoid phrases that would return a specific real person's face.

Do not create `featured.*` or `inline-*` files unless the image must be a chart or diagram that a
photo can't show; then draw it as `work/<n>/inline-<i>.svg` (see `prompts/illustration_guide.md`).
`publish` takes care of the rest: Unsplash first, then Openverse, then drawings, then a branded
card, so a post always goes out with a featured image and at least 2 in-article images.

**Never hold a post back for images.** If a post ends up with fewer than 2 in-article images, or
an image file is missing, publish it anyway: `publish` fills each gap automatically, first with
a free commercial-use photo from Openverse (credited in the caption), then with a branded
key-point card. The digest lists every backup used.

## 5. Schedule and index
For each passed post, as soon as it passes:
```bash
python -m blog_automation publish <output folder> --source trend:<bucket>
```
`publish` picks the next free time slot between 11:00 and 20:00 IST (at least 4 hours after this
run), uploads the featured and in-article images with alt text, sets the Rank Math SEO fields
and schedules the post. Each post is submitted for indexing when it goes live (Rank Math
IndexNow). An evening task runs `python -m blog_automation index` to submit every post that
went live and confirm it is in the sitemap Google reads.

## 6. Digest (last step)
Run `python -m blog_automation digest`. Above it, list the topics that failed and the replacement
used for each. If a Gmail tool is available, email it to the address in the scheduled task's
prompt. Whether or not you emailed it, end the session with the full digest as your final
message.
