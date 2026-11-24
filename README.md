# Blog Automation for 21DEGREES

Picks trending Google searches in India and turns the best ones into blog posts in the 21DEGREES
voice. The posts are built to rank on Google and to be quoted by ChatGPT, Gemini and Perplexity.
The rules come from the analysis of the existing blog in
[`analysis/blog-pattern-analysis.md`](analysis/blog-pattern-analysis.md).

## How it works

1. **Trends.** The pipeline reads Google Trends' daily trending searches for India from the public RSS feed. This step needs no API key.
2. **Pick.** Claude scores each trend. It decides the angle type (direct finance news, or a sport / celebrity / culture metaphor), how naturally the trend leads to an SME-finance lesson (0–10), the topic cluster, the target keyword and a working title.
   - Score = search volume (log scale) × fit × angle weight.
   - News gets a small 1.15× boost. Metaphors count at full weight.
   - Tragedies, and trends with no sensible business angle, score 0.
3. **Research.** Claude searches the web for facts, figures and the questions people ask, and keeps the source URLs.
4. **Write.** Claude writes a structured post: title tag, meta description, slug, H1, quick answer, hook, question-style sections, a table, a worked ₹ example, a short 21DEGREES pitch, FAQ, P.S. and CTA. The house style is in `blog_automation/prompts/style_guide.md`.
5. **Validate and revise.** The post is checked against the blueprint rules (below). Failing posts go back for up to two revision passes.

### What the validator checks
- Length and title / meta / slug limits.
- Quick-answer size and FAQ count.
- At least 50% of section headings are questions.
- Every external link appeared in the web research, so no invented sources.
- Every internal link points to a real 21DEGREES post or page.
- The booking link is present.
- Brand-mention count, and banned phrases from the old posts.

## Setup

```bash
pip install -r requirements.txt
```

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

```bash
python -m blog_automation trends
```

Shows today's trends. No key needed.

```bash
python -m blog_automation pick
```

Scores the trends and saves `output/topics-*.json` and `.md`.

```bash
python -m blog_automation generate output/topics-YYYYMMDD-HHMM.json --rank 1
```

Writes the post ranked #1 in that list.

```bash
python -m blog_automation run --count 2 --min-fit 6
```

Picks, then writes the top 2 topics.

Each post is written to `output/<date>-<slug>/`:

| File | Use |
|---|---|
| `post.html` | Paste into a WordPress *Custom HTML* block. It includes FAQPage schema. The title tag, meta description and slug are in comments at the top, for Rank Math. |
| `post.md` | Markdown with front matter (SEO fields, category, image alt text and an image prompt) |
| `post.json` | Structured post fields |
| `research.md` | Research notes and every source found |
| `checks.txt` | Validator results (PASS / WARN / FAIL) |

Review every post before publishing. Check the facts against `research.md`, and add a featured image.

### Refreshing the internal-link inventory

```bash
scripts/scrape_blogs.sh /tmp/scrape
```

```bash
cp /tmp/scrape/posts.json analysis/data/all_posts_metadata.json
```

## Daily automation (no API key)

A scheduled Claude Code session follows [`automation/DAILY_RUN.md`](automation/DAILY_RUN.md) every
morning. It:
- picks 10 topics (Google Trends first, then the evergreen backlog in `data/backlog.json`),
- researches and writes each post,
- runs the checks,
- schedules each passing post on WordPress between 11:00 and 20:00 IST, at least 4 hours after
  the run, which leaves a review window,
- emails a digest with edit links.

The WordPress login is an application password saved as a network secret on the cloud
environment. To run the scripts elsewhere, set `WP_USER` and `WP_APP_PASSWORD`.

## Featured images

Every scheduled post gets a featured image, uploaded with alt text. The house style comes from a
review of the existing blog images (`blog_automation/prompts/image_style.md`): flat editorial
illustration, navy, teal and beige with a saffron accent, Indian people and settings, rupees only,
no text, 3:2 landscape.

- **Nano Banana** (`gemini-nano-banana-2.1`, about $0.034 per image) is used when a Google AI
  Studio API key is saved for `generativelanguage.googleapis.com`. Google offers no free API tier
  for its image models.
- **Free fallback:** a branded title card in the same palette, drawn locally.

To make the image again, or attach it to an existing post:

```bash
python -m blog_automation image output/<folder> --post-id <id>
```

## Configuration
Everything is in `blog_automation/config.py`:
- model (`claude-opus-5-5`)
- country (`--geo`)
- angle weights
- topic clusters and seed keywords
- length / SEO targets
- banned phrases

Claude calls use a server-side refusal fallback, structured outputs, and prompt caching on the style guide.

## Tests

```bash
python -m pytest tests -q
```

The tests run offline. They cover Trends parsing, ranking weights, the validator, HTML rendering, and the exact API request shape.
