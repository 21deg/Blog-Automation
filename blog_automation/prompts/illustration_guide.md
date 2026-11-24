# Drawing the featured illustration (SVG)

Each post gets a flat editorial illustration drawn as SVG by Claude in the daily session, in the
house style from `image_style.md`. Start from `blog_automation/assets/illustration_example.svg`:
reuse its person, desk, laptop, plant, window and coin pieces and rearrange them for the topic.

## Canvas and palette
- `viewBox="0 0 1536 1024"`, width 1536, height 1024. Beige background `#F3E6D3`, soft blobs `#EAD8BF`.
- Navy `#1F3A5F` / `#2B4C75` for outlines and furniture, teal `#3E8E8B` / `#2F6F6C`, saffron
  `#E8A33D` / `#F0B85A` for the one accent, off-white `#FBF7F0`, light grey-blue `#C9D6E3`.
- Skin tones: `#C68560`, `#B9774F`, `#8D5A3B`, `#E0A97E`. Hair `#1E1E2A`.
- Keep the paper-grain filter rect from the example as the last element.

## Composition
- One clear scene that tells the post's idea at a glance (for example: founder checking a
  checklist beside a laptop; a shopkeeper at a counter with a GST receipt; a cricket ball beside a
  cash-flow chart; a bank building with a rupee coin and a calendar for loan EMIs).
- 1–2 people at most, Indian, friendly, simple shapes (no detailed faces). Vary gender, age and
  clothing from post to post.
- Keep the main subject inside the centre 1200×800 area so square and wide crops work.
- Symbols that work well: rupee coin or note (₹), bar chart, pie chart, calendar, clipboard with
  ticks, magnifying glass, shield, scales, bank columns, shop awning, cricket bat and ball, gears,
  arrows up or down, a sparkle for AI.

## Rules
- Only shapes, paths, gradients and filters. No `<image>`, no external links, no `<script>`,
  no fonts other than for a single ₹ sign. No other text, letters or numbers.
- No logos, brand marks, real people's likenesses or copyrighted characters.
- Under 40 KB of SVG.

## Steps
1. Write `work/<n>/featured.svg`.
2. Run `python -m blog_automation finalize ...` (copies it into the output folder), then
   `python -m blog_automation image <output folder>` to render `featured.jpg`.
3. Look at `featured.jpg` once. Fix anything broken (parts overlapping badly, a missing face,
   elements off the canvas). Then publish.
