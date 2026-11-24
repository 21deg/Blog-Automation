#!/usr/bin/env bash
# Download every post listed in the 21degrees.in post sitemap, then extract metrics.
# Usage: scripts/scrape_blogs.sh <out_dir>
set -euo pipefail
OUT=${1:-./scrape}; mkdir -p "$OUT/posts"
curl -s https://21degrees.in/post-sitemap.xml -o "$OUT/post-sitemap.xml"
grep -oE '<loc>[^<]+' "$OUT/post-sitemap.xml" | sed 's/<loc>//' | grep -v wp-content > "$OUT/urls.txt"
while read -r u; do
  f="$OUT/posts/$(echo "$u" | sed 's#https://21degrees.in/##; s#/$##' | tr -c 'a-zA-Z0-9-\n' '_' | cut -c1-120).html"
  [ -s "$f" ] || curl -s -A "Mozilla/5.0" "$u" -o "$f"; sleep 0.2
done < "$OUT/urls.txt"
python3 -I "$(dirname "$0")/extract_posts.py" "$OUT/posts" "$OUT/posts.json"
