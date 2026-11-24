# Daily blog run (for the scheduled Claude Code session)

Goal: write and schedule **10** posts on 21degrees.in for today, then email the review digest.
Claude in this session does the topic scoring, research and writing. The repo's scripts do the
checks, rendering, WordPress scheduling and digest. No Anthropic API key is needed.

Hard rules:
- Never give an existing post's keyword to a new post. Link to the older post instead.
- Never schedule a post whose `finalize` checks fail.
- Never edit, unpublish or delete existing posts on the site.
- Only cite URLs you actually opened during research. Never invent figures, quotes or URLs.
- If fewer than 10 posts pass, schedule the ones that passed and say so in the digest.

## 1. Set up
```bash
git fetch origin claude/youthful-lovelace-okbvzj && git checkout -B daily-run FETCH_HEAD
pip install -q -r requirements.txt
python -m blog_automation wp-check
```
If `wp-check` fails or `can_publish` is false, skip to step 5 and send a digest that says the
WordPress login failed, with the error.

## 2. Choose 10 topics
1. Run `python -m blog_automation trends` and score each trend yourself, using the rules in
   `SYSTEM` in `blog_automation/picker.py`:
   - angle type: `direct` finance or business news gets weight 1.15; `metaphor` (sport,
     celebrity, film, politics, science) gets 1.0; `none` (tragedy, disaster, no angle) gets 0.
   - fit from 0 to 10.
   - score = log10(traffic + 10) × fit × weight.
2. Take every trend with fit ≥ 6, best score first, up to 10.
3. Fill the remaining slots with `python -m blog_automation backlog --count <remaining>`.
   That command already skips keywords the site covers.
4. Make sure no two of today's topics target the same keyword.

## 3. Write each post
Work through the topics one at a time. Use a fresh subagent (general-purpose) for each post so
that research for one post doesn't fill the main context. Give the subagent:
- the topic (trend or backlog question, finance angle, target keyword, pillar),
- `blog_automation/prompts/style_guide.md` (house style, structure and banned phrases),
- the `BlogPost` field list from `blog_automation/generator.py`,
- the internal link inventory: `analysis/data/all_posts_metadata.json` (urls and titles) plus the
  pages in `SERVICE_PAGES` in `blog_automation/config.py`.

The subagent must:
1. Research: find pages with web search, then read them with
   `python -m blog_automation fetch <url> [<url> ...]`. The WebFetch tool cannot reach the web in
   this environment; the `fetch` command goes through the environment's proxy and works. Collect
   facts with their source URLs, and prefer primary sources (RBI, CBIC, PIB, courts, MCA) and major
   Indian publications. Only pages that `fetch` actually returned text for go into sources.json.
2. Write `work/<n>/post.json` (matching `BlogPost` exactly), `work/<n>/sources.json`
   (`{"url": "title"}` for every page it actually read) and `work/<n>/research.md` (its notes).
3. Draw the featured illustration as `work/<n>/featured.svg`, following
   `blog_automation/prompts/illustration_guide.md` and starting from
   `blog_automation/assets/illustration_example.svg`. One scene that matches this post's idea;
   vary people and objects from the other posts today.
4. Run `python -m blog_automation finalize work/<n>/post.json work/<n>/sources.json --research work/<n>/research.md`
   and fix the post until the output says PASSED (at most 3 attempts). This copies featured.svg
   into the output folder.
5. Run `python -m blog_automation image <output folder>` and look at the rendered
   `featured.jpg` once. Fix anything broken in the SVG and render again (at most 2 attempts).
6. Report back the output folder and pass or fail.

## 4. Schedule
For each post that passed, in order (n = 1, 2, …):
```bash
python -m blog_automation publish <output folder> --slot <n> --count <number of passed posts>
```
`publish` also uploads the featured image (the drawn illustration; a branded title card if the
drawing is missing or fails to render), uploads it with alt text and sets it as the post's featured image. If the
image step fails, the post is still scheduled and the digest flags the missing image.

Posts are scheduled between 11:00 and 20:00 IST, at least 4 hours after this run, so there is a
review window. Then mark used backlog topics:
`python -m blog_automation backlog --mark <id> <id> ...`

Rank Math submits each URL to Bing and IndexNow when the post goes live, and adds it to the
sitemap Google reads. Nothing else is needed for indexing.

## 5. Send the digest
Run `python -m blog_automation digest` and send its subject and body by email with Gmail to the
recipient named in the scheduled task's prompt. Add a first line that says how many posts came
from Google Trends and how many from the backlog, and list any topics that failed.
