# Daily blog run (for the scheduled Claude Code session)

Goal: **schedule 10 posts on 21degrees.in today, every one from today's Google Trends, each with a
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

## 2. Pick 10 topics from Google Trends (always)
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

## 4. Images
House style for every image: `blog_automation/prompts/image_style.md` (flat editorial
illustration; navy, teal, beige and saffron; Indian people and settings; ₹ only, never $; no
logos; no real people's likenesses).

**If Canva tools (`mcp__Canva__*`) are available**, use them for the featured image and the scene
image:
1. `generate-image` with the prompt (house style written into the prompt) and
   `aspectRatio: LANDSCAPE_3_2`, then poll `get-generate-image-job` until SUCCESS. Note the
   media id.
2. `create-design` with brief "A single full-bleed landscape image using the supplied picture
   exactly as it is, filling the whole page edge to edge. No text, no logo, no extra elements.",
   format "Blog Banner (Landscape)", `references: [<media id>]`. Poll
   `get-create-design-async-job`.
3. `export-design` as `{"type": "jpg", "quality": 90, "width": 1536}` and download the URL with
   curl to `work/<n>/featured-canva.jpg` (featured) or `work/<n>/inline-<i>.jpg` (in-article).

**If Canva is unavailable or fails** (no tools, quota used up, or an error), draw SVG instead,
following `blog_automation/prompts/illustration_guide.md`: `work/<n>/featured.svg` and
`work/<n>/inline-<i>.svg`. Charts, checklists and diagrams are always drawn as SVG. Then render
and look once: `python -m blog_automation image <output folder>`.

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
