#!/bin/bash
# Setup sitemap and robots.txt for 21degrees.in
# This script generates the necessary files for search engine indexing

set -e

SITE_URL="https://21degrees.in"
OUTPUT_DIR="${1:-.}"

echo "Setting up search engine indexing files..."
echo "Site: $SITE_URL"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Generate sitemap
echo "1. Generating sitemap.xml..."
python -m blog_automation sitemap --output "$OUTPUT_DIR/sitemap.xml"
echo "   ✓ Sitemap generated"

# Generate robots.txt
echo ""
echo "2. Generating robots.txt..."
python -m blog_automation robots --output "$OUTPUT_DIR/robots.txt"
echo "   ✓ robots.txt generated"

# Display summary
echo ""
echo "========================================"
echo "Search Engine Indexing Setup Complete!"
echo "========================================"
echo ""
echo "Files generated:"
ls -lh "$OUTPUT_DIR/sitemap.xml" "$OUTPUT_DIR/robots.txt"
echo ""
echo "Next steps:"
echo "1. Upload sitemap.xml and robots.txt to the root of 21degrees.in"
echo "2. Verify files are accessible:"
echo "   - $SITE_URL/sitemap.xml"
echo "   - $SITE_URL/robots.txt"
echo ""
echo "3. Submit to Google Search Console:"
echo "   - Go to: https://search.google.com/search-console"
echo "   - Add property: $SITE_URL"
echo "   - Submit sitemap: $SITE_URL/sitemap.xml"
echo ""
echo "4. Submit to Bing Webmaster Tools:"
echo "   - Go to: https://www.bing.com/webmasters"
echo "   - Add site: $SITE_URL"
echo "   - Submit sitemap: $SITE_URL/sitemap.xml"
echo ""
echo "5. Configure WordPress (Rank Math):"
echo "   - Settings > Rank Math > Sitemap"
echo "   - Enable XML Sitemap"
echo "   - Configure sitemap settings for blog posts"
echo ""
