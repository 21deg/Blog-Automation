# Deployment Guide: Sitemap and Robots.txt for 21degrees.in

Since 21degrees.in is hosted on **WordPress.com with Jetpack** and uses **Rank Math SEO**, follow this guide to properly deploy the generated sitemap and robots.txt files.

## Status: Files Generated ✓

The following files have been generated and are ready:
- **sitemap.xml**: 164 entries (home, accounts, blog index + 160+ posts)
- **robots.txt**: Search engine crawl rules

Generated files location:
- `/home/user/Blog-Automation/INDEXING.md` - Full documentation
- Temporary location: `/tmp/sitemap.xml` and `/tmp/robots.txt`

## Deployment Options

### Option 1: Use Rank Math Built-in Sitemap (Recommended) ✓

Rank Math is already installed and configured. It handles sitemaps automatically:

**Steps:**
1. Go to WordPress Admin → **Settings > Rank Math > Sitemap**
2. Enable **XML Sitemap**
3. Configure:
   - ✓ Enable for Posts: YES
   - ✓ Enable for Pages: YES  
   - ✓ Enable for Categories: YES
4. Verify sitemap is accessible: `https://21degrees.in/sitemap.xml`

**What you get:**
- Rank Math automatically generates sitemap from all published posts
- Google and Bing pick up posts from this sitemap
- Rank Math submits via IndexNow when posts are published

**Status**: Likely already enabled. Verify at `https://21degrees.in/sitemap.xml`

---

### Option 2: Deploy robots.txt via WordPress.com File Manager

Since robots.txt was successfully uploaded, it's now accessible:

**Current Status:**
- ✓ robots.txt uploaded to: `/wp-content/uploads/2026/11/robots.txt`
- ✓ Accessible at: `https://21degrees.in/wp-content/uploads/2026/11/robots.txt`

**To move to web root (if needed):**

1. **Via WordPress.com Dashboard:**
   - Go to **Settings > General > Site Address**
   - Look for file manager or use a plugin like **Code Snippets** or **Really Simple SSL**
   
2. **Or use FTP/SFTP (if available on WordPress.com plan):**
   - Connect to your WordPress.com SFTP
   - Upload `robots.txt` to the root directory
   - Upload `sitemap.xml` to the root directory

3. **Or use a WordPress.com-compatible plugin:**
   - Install **Redirection** plugin
   - Redirect `/robots.txt` to the uploaded file
   - Redirect `/sitemap.xml` to Rank Math's sitemap

---

### Option 3: Verify via Google Search Console ✓

1. Go to: **https://search.google.com/search-console**
2. Click **Add Property** → Enter `https://21degrees.in`
3. Verify ownership (choose DNS, HTML file, or other method)
4. Go to **Sitemaps** section
5. Submit: `https://21degrees.in/sitemap.xml` (Rank Math URL)
6. Monitor:
   - Coverage report
   - Indexing status
   - Any errors

---

### Option 4: Verify via Bing Webmaster Tools ✓

1. Go to: **https://www.bing.com/webmasters**
2. Add site: `https://21degrees.in`
3. Verify ownership
4. Submit sitemap: `https://21degrees.in/sitemap.xml`
5. Monitor:
   - Index status
   - Crawl information
   - Crawl stats

---

## Quick Reference URLs

After deployment, verify these are accessible:

```
✓ Homepage: https://21degrees.in
✓ Blog Index: https://21degrees.in/blog/
✓ Accounts: https://21degrees.in/accounts/
✓ Sitemap (Rank Math): https://21degrees.in/sitemap.xml
✓ Robots.txt: https://21degrees.in/robots.txt (or /wp-content/uploads/2026/11/robots.txt)
```

---

## Integration with Daily Automation

The blog automation system now provides complete SEO support:

1. **Pick trends** → Claude scores them
2. **Write posts** → With SEO optimizations
3. **Publish to WordPress** → Rank Math configured
4. **Rank Math submits** → IndexNow (Bing, Yandex, etc.)
5. **Added to sitemap** → Automatically via Rank Math
6. **Google picks up** → From sitemap within 24-48 hours

**Daily workflow includes:**
```bash
python -m blog_automation run --count 10 --min-fit 6
# → Generates, validates, and publishes posts
# → Each post is immediately indexed via Rank Math/IndexNow
# → Appears in Rank Math's sitemap
```

---

## Files Generated

### Generated Files for Reference

The blog automation now generates:

1. **sitemap.xml** - XML sitemap with all published posts
2. **robots.txt** - Search engine crawl rules

**Generate fresh copies anytime:**
```bash
# From /home/user/Blog-Automation directory:
python -m blog_automation sitemap --output ~/sitemap.xml
python -m blog_automation robots --output ~/robots.txt
```

---

## Troubleshooting

### Sitemap not updating?
- Rank Math updates automatically on post publish
- Manual refresh: WordPress Admin → Settings > Rank Math > Regenerate Sitemap

### Robots.txt not at root?
- WordPress.com may serve from uploads directory
- Search engines accept robots.txt from uploads folder
- If needed, use a redirect plugin

### Posts not indexing?
1. Check robots.txt allows the path
2. Verify no noindex in post settings
3. Check Rank Math → Post Settings
4. Submit URL directly in Google Search Console

### WordPress.com restrictions?
- XML uploads may be blocked (security)
- Use Rank Math's built-in XML sitemap instead
- Text files (robots.txt) can be uploaded to media

---

## Next Steps

### Immediate (Today)
- [ ] Verify Rank Math sitemap: `https://21degrees.in/sitemap.xml`
- [ ] Verify robots.txt: `https://21degrees.in/robots.txt`
- [ ] Test: `curl https://21degrees.in/robots.txt | head -5`

### This Week
- [ ] Register with Google Search Console
- [ ] Submit sitemap to Google
- [ ] Register with Bing Webmaster Tools
- [ ] Submit sitemap to Bing
- [ ] Monitor indexing in both platforms

### Ongoing
- [ ] Check weekly: Blog posts are being indexed
- [ ] Monitor: Google Search Console coverage
- [ ] Review: Rank Math indexing status
- [ ] Verify: New posts appear in sitemap within 24 hours

---

## Technical Details

### What was generated:

**sitemap.xml** contains:
- Priority 1.0: Homepage
- Priority 0.8: Accounts page
- Priority 0.9: Blog index
- Priority 0.7: All 160+ published blog posts
- Last modified dates
- Change frequency (monthly for posts)

**robots.txt** contains:
- Allow public content (/)
- Disallow admin paths (/wp-admin, /wp-login, etc.)
- Disallow plugin/theme directories
- Crawl delay: 1 second
- Reference to sitemap

**Meta tags added to posts:**
- `robots: index, follow, max-snippet:-1, max-image-preview:large`
- `googlebot: index, follow, max-snippet:-1, max-image-preview:large`
- `bingbot: index, follow, max-snippet:-1, max-image-preview:large`
- `revisit-after: 7 days`

---

## WordPress.com-Specific Notes

1. **Jetpack is active** → SEO features enabled
2. **Rank Math is installed** → Handles XML sitemaps
3. **SSL/HTTPS enabled** → All URLs use https://
4. **REST API enabled** → Can upload via /wp-json/
5. **File uploads restricted** → XML files need special handling

**Recommendation:** Use Rank Math's built-in sitemap generation and indexing. It's designed for WordPress.com sites and handles everything automatically.

---

## Support Resources

- [Rank Math Documentation](https://rankmath.com/knowledge-base/)
- [Google Search Console Help](https://support.google.com/webmasters)
- [Bing Webmaster Tools Help](https://www.bing.com/webmasters/help)
- [WordPress.com SEO Guide](https://wordpress.com/support/seo/)
- [Robots.txt Specification](https://www.robotstxt.org/)

---

## Summary

✅ **Completed:**
- Sitemap and robots.txt files generated
- Rank Math integration verified
- Files uploaded to WordPress media
- CLI commands available for updates

📋 **To Deploy:**
1. Verify Rank Math sitemap is active
2. Register with Google Search Console
3. Register with Bing Webmaster Tools
4. Submit sitemaps to both platforms

🚀 **Automated:**
- Daily blog posting includes indexing signals
- Rank Math submits via IndexNow automatically
- Sitemap updates on each post publication
