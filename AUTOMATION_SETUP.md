# Automatic Sitemap and Google Indexing Setup

This guide explains how to set up automatic indexing so that every blog post is immediately added to the sitemap and indexed on Google when it goes live.

## Overview

The system now provides **complete automatic indexing**:

1. **Post Published** → Automatically indexed on Bing/Yandex via IndexNow
2. **Sitemap Updated** → Post appears in sitemap within seconds
3. **Google Pick-up** → Google crawls the sitemap and indexes within 24-48 hours

## Key Features

✅ **Automatic submission** - IndexNow submits to Bing, Yandex, and others  
✅ **Instant indexing signals** - Meta tags tell crawlers to index immediately  
✅ **Sitemap auto-update** - Published posts automatically added  
✅ **Status tracking** - Log of all indexed posts  
✅ **CLI commands** - Manual control when needed  
✅ **Daily automation** - Runs with existing daily blog posting  

## How It Works

### 1. Post Publication → Automatic Indexing

When a post is published (not draft):

```python
# From blog_automation/publisher.py
published = publish_folder(folder, publish_at)
if not draft and published.get("link"):
    # Automatically submit to search engines
    auto_index_post(published["link"], published["h1"])
```

Each newly published post is:
- ✓ Submitted to IndexNow (Bing, Yandex, etc.) via Rank Math
- ✓ Added to sitemap on next regeneration
- ✓ Tagged with indexing meta tags

### 2. IndexNow Submission (Immediate)

**What happens:**
- Post URL is sent to IndexNow API
- Bing and Yandex are notified immediately
- Crawl priority is raised
- Other search engines notified through IndexNow

**Response time:** Seconds to minutes

### 3. Sitemap Updates (Automatic)

The sitemap is automatically regenerated:
- After each batch publishing (via `auto-sitemap` command)
- Rank Math updates its sitemap on each post
- Google's crawler picks it up and indexes posts

**Response time:** Minutes to hours

### 4. Google Indexing (Automatic)

Google:
- Reads the sitemap regularly
- Discovers new posts from the sitemap
- Crawls and indexes them
- Shows in search results

**Response time:** 24-48 hours (usually faster)

## CLI Commands

### Automatic Indexing

Index posts published in the last hour (runs automatically after publishing):

```bash
python -m blog_automation auto-index --hours 1
```

Output: JSON report with indexed URLs and response

### Manual Sitemap Regeneration

Regenerate sitemap with all current posts:

```bash
python -m blog_automation auto-sitemap
```

Output: JSON report with entry count and status

### Check Indexing Status

Check if a specific post has been indexed:

```bash
python -m blog_automation indexing-status --post-id 2097
```

Check all posts:

```bash
python -m blog_automation indexing-status
```

## Integration with Daily Automation

### Current Daily Workflow

The existing daily automation in `automation/DAILY_RUN.md`:

```
1. Pick trends (10 topics)
2. Research and write posts
3. Run validation checks
4. Publish to WordPress
5. Email digest
```

### Enhanced Workflow with Auto-Indexing

```
1. Pick trends (10 topics)
2. Research and write posts
3. Run validation checks
4. Publish to WordPress
   ↓ (triggers)
5. ✨ AUTOMATIC: Submit to search engines via IndexNow
6. ✨ AUTOMATIC: Update sitemap
7. Email digest
8. ✨ Optional: Run `auto-index --hours 24` to verify all posts
```

The automatic indexing happens **in the background** as posts are published. No additional manual steps required.

## Configuration for Production

### For Claude Code Scheduled Sessions

If using scheduled Claude sessions (as in `automation/DAILY_RUN.md`):

Add these lines to your daily run script:

```bash
# After publishing posts
python -m blog_automation auto-index --hours 1

# Or after batch publishing
python -m blog_automation auto-sitemap
```

### For Manual Publishing

After publishing posts manually:

```bash
# Index the posts just published
python -m blog_automation auto-index --hours 1
```

### For Weekly Maintenance

Schedule a weekly sitemap regeneration:

```bash
# Every Sunday at 2 AM IST
0 2 * * 0 cd /home/user/Blog-Automation && python -m blog_automation auto-sitemap
```

Or set up a cron job:

```bash
crontab -e

# Add:
0 2 * * 0 cd /path/to/Blog-Automation && python -m blog_automation auto-sitemap >> /var/log/blog-automation/sitemap.log 2>&1
```

## Monitoring and Logging

### Indexing Log

All indexing actions are logged to:
```
output/indexing-log.json
```

This tracks:
- Each post's first indexing time
- Number of times re-indexed
- Indexing timestamps
- IndexNow responses

### Daily Reports

After publishing, check the daily log:

```bash
# View today's published posts
python -m blog_automation digest

# Check if newly indexed
python -m blog_automation auto-index --hours 1
```

### Google Search Console

Monitor indexing in real-time:

1. Go to: https://search.google.com/search-console
2. Property: https://21degrees.in
3. Coverage: See indexed vs. not indexed
4. Indexing report: See recent indexing activity

## Troubleshooting

### Posts not indexing?

**Check 1: Was the post published (not draft)?**
```bash
python -m blog_automation wp-check
# Then check status in WordPress admin
```

**Check 2: Is robots.txt allowing the path?**
```bash
curl https://21degrees.in/robots.txt | grep -v "^#"
```

**Check 3: Does the post have noindex tag?**
- Go to WordPress Admin → Edit Post
- Rank Math → Indexing → Check "index" is selected

**Check 4: Is IndexNow working?**
```bash
python -m blog_automation auto-index --hours 1
# Check the response status
```

**Check 5: Google Search Console**
- Submit URL manually
- Check for crawl errors
- Review robots.txt issues

### Indexing appears to fail?

If `auto-index` returns errors:

1. Check WordPress credentials:
   ```bash
   python -m blog_automation wp-check
   ```

2. Check network connectivity:
   ```bash
   curl -I https://21degrees.in/robots.txt
   ```

3. Check Rank Math is active:
   - WordPress Admin → Settings > Rank Math
   - Verify settings are saved

4. Check log file:
   ```bash
   cat output/indexing-log.json | python3 -m json.tool
   ```

### Sitemap not updating?

The sitemap is automatically updated by Rank Math when:
- A post is published
- A post is modified
- Settings are changed

Manual update:
```bash
python -m blog_automation auto-sitemap
```

Verify it's live:
```bash
curl https://21degrees.in/sitemap.xml | head -20
```

## Performance Notes

### How Fast is Indexing?

**IndexNow (Bing, Yandex, etc.):**
- **Submission:** Immediate (seconds)
- **Crawl:** Minutes to hours
- **Indexing:** Minutes to hours

**Google:**
- **Sitemap:** Fetched every day
- **Crawl:** 24-48 hours average
- **Indexing:** 24-48 hours average

**Real-time:** Rank Math provides instant indexing signals

### Load Impact

Automatic indexing has minimal impact:
- One API call per published post
- Sitemap generation: < 1 second
- Background submission: Non-blocking
- No impact on page load times

## Advanced Usage

### Batch Indexing

Index multiple posts at once:

```bash
# Check posts from last 24 hours
python -m blog_automation auto-index --hours 24

# Or index from last 7 days
python -m blog_automation auto-index --hours 168
```

### Status Tracking

Get detailed status:

```python
from blog_automation import auto_indexing

# Get status for specific post
status = auto_indexing.get_indexing_status(post_id=2097)
print(status)

# Get indexing report for last 24 hours
report = auto_indexing.daily_indexing_report(hours=24)
print(f"Indexed today: {report['total_indexed']}")
```

### Integration with Custom Scripts

In your own scripts:

```python
from blog_automation import auto_indexing

# After publishing a batch of posts
result = auto_indexing.index_new_posts(hours=1)
if result["status"] == "success":
    print(f"Indexed {result['indexed_count']} posts")
else:
    print(f"Error: {result['error']}")

# Regenerate sitemap
sitemap_result = auto_indexing.regenerate_sitemap()
print(f"Sitemap: {sitemap_result['entries_count']} entries")
```

## Best Practices

### 1. Run After Publishing

After publishing posts via CLI or API:

```bash
python -m blog_automation auto-index --hours 1
```

### 2. Daily Regeneration

Schedule daily sitemap regeneration:

```bash
# 2 AM IST daily
0 2 * * * python -m blog_automation auto-sitemap
```

### 3. Weekly Verification

Check indexing status weekly:

```bash
python -m blog_automation indexing-status
```

### 4. Monitor Google Search Console

Check the Coverage report weekly:
- Indexed pages should increase
- Errors should stay at 0
- Crawl stats should show activity

### 5. Keep logs clean

Archive old indexing logs monthly:

```bash
# Backup
cp output/indexing-log.json "backups/indexing-log-$(date +%Y%m%d).json"

# Reset if too large
echo '{}' > output/indexing-log.json
```

## Files and Code Changes

### New Files

- **`blog_automation/auto_indexing.py`** (220+ lines)
  - `index_new_posts()` - Automatic indexing
  - `regenerate_sitemap()` - Sitemap generation
  - `daily_indexing_report()` - Reporting
  - `get_indexing_status()` - Status tracking

### Modified Files

- **`blog_automation/publisher.py`**
  - Added `auto_index_post()` function
  - Added import of `auto_indexing` module
  - Automatic indexing on post publication

- **`blog_automation/__main__.py`**
  - Added `auto-index` CLI command
  - Added `auto-sitemap` CLI command
  - Added `indexing-status` CLI command

## Testing

Verify the automation:

```bash
# Test auto-indexing
python -m blog_automation auto-index --hours 1

# Test sitemap generation
python -m blog_automation auto-sitemap

# Test status tracking
python -m blog_automation indexing-status

# Test CLI help
python -m blog_automation --help | grep -i index
```

## Support and Debugging

### Common Issues

**Q: Posts aren't showing in Google?**
A: Check Google Search Console → Coverage. Submit URL manually if urgent.

**Q: IndexNow returning errors?**
A: Check WordPress connection with `wp-check`. Verify Rank Math settings.

**Q: Sitemap not updating?**
A: Run `auto-sitemap` manually. Verify it's accessible at `/sitemap.xml`.

**Q: Too many indexing requests?**
A: IndexNow has rate limits. The system respects them automatically.

### Getting Help

For issues:

1. Check `output/indexing-log.json`
2. Run `python -m blog_automation wp-check`
3. Check Google Search Console for errors
4. Review `INDEXING.md` for detailed docs

## Next Steps

1. ✅ Automatic indexing is now enabled
2. ✅ Posts are automatically submitted to Bing/Yandex
3. ✅ Sitemap is automatically updated
4. ⬜ Register with Google Search Console (if not done)
5. ⬜ Register with Bing Webmaster Tools (if not done)
6. ⬜ Monitor first batch of posts for indexing
7. ⬜ Set up weekly monitoring cron job

## Summary

The blog automation system now provides **complete automatic SEO indexing**:

- ✅ Every post published → Automatically submitted to search engines
- ✅ Sitemap automatically updated → Google discovers new posts
- ✅ Meta tags signal indexing priority → Faster crawling
- ✅ Status tracking → Know which posts are indexed
- ✅ CLI tools → Manual control when needed
- ✅ Zero manual work → Fully automated

**New posts are now automatically indexed on Google within 24-48 hours of publication.**
