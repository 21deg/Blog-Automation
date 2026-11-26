# Search Engine Indexing Setup for 21DEGREES

This guide covers the setup and management of sitemaps and Google/Bing indexing for all blog posts on 21degrees.in.

## Overview

The blog automation system now includes complete SEO indexing support:

- **XML Sitemap**: Automatically generated from all published WordPress posts
- **robots.txt**: Guides search engine crawlers with proper allow/disallow rules
- **Meta Tags**: Added to all generated posts for indexing signals
- **IndexNow Submission**: Automatic submission to Bing and other search engines via Rank Math
- **Google Indexing**: Posts are picked up from the sitemap by Google's crawler

## Quick Start

### Generate Sitemap and Robots.txt

```bash
# Generate both files in one go
bash scripts/setup_indexing.sh

# Or generate individually
python -m blog_automation sitemap --output sitemap.xml
python -m blog_automation robots --output robots.txt
```

### Generate Sitemap to Specific Location

```bash
# Output to web root or any location
python -m blog_automation sitemap --output /var/www/html/sitemap.xml
```

## Files and Configuration

### 1. `blog_automation/indexing.py`

Core indexing module with the following functions:

#### `generate_sitemap(output_path=None) -> str`
Generates XML sitemap with:
- All published WordPress posts from the site
- Posts from the inventory metadata
- Static pages (home, accounts, blog index)
- Last modified dates
- Priority and changefreq settings

**Usage:**
```python
from blog_automation.indexing import generate_sitemap

# Generate and return XML string
xml = generate_sitemap()

# Generate and save to file
xml = generate_sitemap("/var/www/html/sitemap.xml")
```

#### `get_indexing_meta_tags() -> dict`
Returns standard SEO meta tags for search engines:
```python
{
    "robots": "index, follow, max-snippet:-1, ...",
    "googlebot": "index, follow, max-snippet:-1, ...",
    "bingbot": "index, follow, max-snippet:-1, ...",
    "revisit-after": "7 days"
}
```

#### `add_indexing_headers_to_html(html, meta_tags=None) -> str`
Adds indexing meta tags to HTML document head.

#### `get_robots_txt() -> str`
Generates standard robots.txt content with:
- Allow rules for public content
- Disallow rules for admin and plugin directories
- Crawl delay settings
- Sitemap reference

#### `get_xml_sitemap_index(post_count=0) -> str`
Generates sitemap index for large sites (100,000+ posts).

### 2. Updated CLI Commands

Add these commands to your workflow:

```bash
# Generate sitemap with 163+ blog post entries
python -m blog_automation sitemap

# Generate robots.txt with crawl rules
python -m blog_automation robots

# Submit today's posts for indexing (via Rank Math)
python -m blog_automation index
```

### 3. Meta Tags in Generated Posts

Updated `render.py` now adds SEO indexing comment to all generated posts:
```html
<!-- SEO: robots=index,follow | index-after-publish=true -->
```

This signals to plugins like Rank Math that the post should be indexed immediately.

## WordPress Configuration (Rank Math)

The system integrates with Rank Math SEO plugin already configured on the site:

1. **Go to**: Settings > Rank Math > Sitemap
2. **Enable**: XML Sitemap
3. **Configure**:
   - Enable for Posts: ✓
   - Enable for Pages: ✓
   - Enable for Categories: ✓
4. **Sitemap URL**: `https://21degrees.in/sitemap.xml`

### Automatic Indexing Workflow

When a post is published:

1. **Created in WordPress** via `wordpress.py`
2. **SEO Set** via `wordpress.set_seo()` with title, description, and focus keyword
3. **Indexed**: Rank Math automatically submits via IndexNow (Bing, Yandex, etc.)
4. **Added to Sitemap**: Post appears in sitemap on next generation
5. **Google Pick-up**: Google's crawler reads the sitemap and indexes the post

## Setup Steps

### Step 1: Copy Files to Web Root

```bash
# Generate the files
python -m blog_automation sitemap --output /tmp/sitemap.xml
python -m blog_automation robots --output /tmp/robots.txt

# Upload to 21degrees.in web root
# Using FTP/SFTP or WordPress file manager:
# - /tmp/sitemap.xml → /var/www/html/sitemap.xml
# - /tmp/robots.txt → /var/www/html/robots.txt
```

### Step 2: Verify Files Are Accessible

```bash
curl https://21degrees.in/robots.txt
curl https://21degrees.in/sitemap.xml | head -20
```

### Step 3: Register with Google Search Console

1. Go to: https://search.google.com/search-console
2. Click "Add Property"
3. Enter: `https://21degrees.in`
4. Verify ownership (choose DNS, HTML file, or other method)
5. Go to Sitemaps section
6. Add: `https://21degrees.in/sitemap.xml`
7. Monitor indexing status and coverage

### Step 4: Register with Bing Webmaster Tools

1. Go to: https://www.bing.com/webmasters
2. Add site: `https://21degrees.in`
3. Verify ownership
4. Submit sitemap: `https://21degrees.in/sitemap.xml`

### Step 5: Monitor Indexing

**Google Search Console:**
- Coverage report shows indexed, excluded, and error pages
- IndexNow submission status
- Mobile usability issues
- Core Web Vitals

**Bing Webmaster Tools:**
- Index status
- Crawl information
- Crawl stats
- Keywords

## Maintenance

### Weekly Updates

```bash
# Update sitemap with new posts
python -m blog_automation sitemap --output /var/www/html/sitemap.xml

# Or set up cron job
0 2 * * * cd /home/user/Blog-Automation && python -m blog_automation sitemap --output /var/www/html/sitemap.xml
```

### Monitor Indexing Status

```bash
# Check which posts were submitted today
python -m blog_automation index

# Output includes:
# - URLs submitted
# - IndexNow response
# - Posts missing from sitemap (if any)
```

### Handle Indexing Issues

**Post not in sitemap:**
```bash
# Regenerate sitemap
python -m blog_automation sitemap --output /var/www/html/sitemap.xml

# Manual resubmission via Rank Math in WordPress admin
```

**Indexing not happening:**
1. Check robots.txt allows the path
2. Verify no noindex meta tag in WordPress
3. Check Rank Math indexing is enabled
4. Review Google Search Console for crawl errors

## Technical Details

### Sitemap Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://21degrees.in/blog-post-url/</loc>
    <lastmod>2026-11-26T12:00:00Z</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <!-- More entries... -->
</urlset>
```

### robots.txt Structure

```
User-agent: *           # Rules for all bots
Allow: /                # Allow public content
Disallow: /wp-admin/    # Disallow admin paths

User-agent: Googlebot   # Specific rules for Googlebot
Allow: /

Crawl-delay: 1          # Crawl delay in seconds
Sitemap: ...            # Reference to sitemap
```

### Meta Tags Added to Posts

```html
<!-- Meta tags for search engine indexing -->
<meta name="robots" content="index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large" />
<meta name="googlebot" content="index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large" />
<meta name="bingbot" content="index, follow, max-snippet:-1, max-video-preview:-1, max-image-preview:large" />
<meta name="revisit-after" content="7 days" />
```

## Troubleshooting

### Sitemap Generation Errors

**Issue**: "Could not fetch posts from WordPress"
- **Cause**: WordPress REST API not accessible
- **Fix**: Check WordPress login and network proxy settings

**Issue**: "Could not read post inventory"
- **Cause**: Missing `analysis/data/all_posts_metadata.json`
- **Fix**: Run `scripts/scrape_blogs.sh /tmp/scrape` to regenerate

### Posts Not Indexing

1. Check robots.txt is accessible: `curl https://21degrees.in/robots.txt`
2. Check sitemap is valid: `curl https://21degrees.in/sitemap.xml`
3. Verify no noindex tag in WordPress post settings
4. Check Google Search Console for crawl errors
5. Submit URL directly in Google Search Console for immediate crawl

### Sitemap Too Large

If sitemap exceeds 50,000 URLs or 50MB:
```bash
# Generate sitemap index for splitting
python -m blog_automation sitemap-index
```

## API Reference

### Functions in `indexing.py`

```python
# Generate XML sitemap
generate_sitemap(output_path: Path | None = None) -> str

# Get SEO meta tags dictionary
get_indexing_meta_tags() -> dict

# Add meta tags to HTML
add_indexing_headers_to_html(html: str, meta_tags: dict | None = None) -> str

# Generate robots.txt content
get_robots_txt() -> str

# Generate sitemap index (for large sites)
get_xml_sitemap_index(post_count: int = 0) -> str
```

### CLI Commands

```bash
# Generate sitemap
python -m blog_automation sitemap [--output PATH]

# Generate robots.txt
python -m blog_automation robots [--output PATH]

# Submit today's posts for indexing
python -m blog_automation index

# Check WordPress connection
python -m blog_automation wp-check
```

## Integration with Daily Automation

The daily automation workflow in `automation/DAILY_RUN.md`:

1. Picks 10 trending topics
2. Researches and writes posts
3. **Publishes to WordPress** (now with indexing meta tags)
4. **Rank Math submits** to IndexNow (Bing, Yandex, etc.)
5. Email digest sent with edit links

Each published post is automatically indexed for Bing immediately via IndexNow, and picked up by Google from the sitemap within 24-48 hours.

## References

- [Google Search Central - Sitemaps](https://developers.google.com/search/docs/beginner/sitemaps)
- [Robots.txt Specification](https://www.robotstxt.org/)
- [IndexNow - Instant Indexing](https://www.indexnow.org/)
- [Rank Math - Sitemap Settings](https://rankmath.com/knowledge-base/sitemap/)
- [Bing Webmaster Tools](https://www.bing.com/webmasters)
