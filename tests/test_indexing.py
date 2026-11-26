"""Tests for sitemap and search engine indexing functionality."""
import json
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from blog_automation import indexing


def test_generate_sitemap():
    """Test sitemap generation."""
    xml_str = indexing.generate_sitemap()
    assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<urlset" in xml_str
    assert 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"' in xml_str
    assert "<url>" in xml_str
    assert "<loc>" in xml_str
    assert "<lastmod>" in xml_str
    assert "</urlset>" in xml_str


def test_generate_sitemap_to_file():
    """Test sitemap generation and file writing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "sitemap.xml"
        xml_str = indexing.generate_sitemap(output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Verify file content matches returned string
        file_content = output_path.read_text()
        assert file_content == xml_str


def test_sitemap_xml_valid():
    """Test that generated sitemap is valid XML."""
    xml_str = indexing.generate_sitemap()

    # Remove XML declaration for parsing
    root = ET.fromstring(xml_str)
    assert "urlset" in root.tag

    # Check namespace
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = root.findall("s:url", ns)
    assert len(urls) > 0

    # Verify each URL has required elements
    for url in urls[:5]:  # Check first 5
        loc = url.find("s:loc", ns)
        assert loc is not None
        assert loc.text.startswith("https://")


def test_get_indexing_meta_tags():
    """Test meta tags dictionary."""
    tags = indexing.get_indexing_meta_tags()

    assert isinstance(tags, dict)
    assert "robots" in tags
    assert "googlebot" in tags
    assert "bingbot" in tags
    assert "revisit-after" in tags

    assert "index" in tags["robots"]
    assert "follow" in tags["robots"]


def test_add_indexing_headers_to_html():
    """Test adding meta tags to HTML."""
    html = "<html><head></head><body>Test</body></html>"
    result = indexing.add_indexing_headers_to_html(html)

    assert "<meta name=" in result
    assert 'name="robots"' in result
    assert 'name="googlebot"' in result
    assert "index" in result


def test_add_indexing_headers_custom_tags():
    """Test adding custom meta tags to HTML."""
    html = "<html><head></head><body>Test</body></html>"
    custom_tags = {"test-tag": "test-value"}
    result = indexing.add_indexing_headers_to_html(html, custom_tags)

    assert 'name="test-tag"' in result
    assert 'content="test-value"' in result


def test_add_indexing_headers_no_head():
    """Test HTML without head tag."""
    html = "<html><body>Test</body></html>"
    result = indexing.add_indexing_headers_to_html(html)

    # Should return unchanged
    assert result == html


def test_get_robots_txt():
    """Test robots.txt generation."""
    robots = indexing.get_robots_txt()

    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Disallow: /wp-admin/" in robots
    assert "Disallow: /wp-login.php" in robots
    assert "User-agent: Googlebot" in robots
    assert "User-agent: Bingbot" in robots
    assert "Sitemap: https://21degrees.in/sitemap.xml" in robots
    assert "Crawl-delay: 1" in robots


def test_robots_txt_format():
    """Test robots.txt is properly formatted."""
    robots = indexing.get_robots_txt()

    lines = robots.strip().split("\n")
    assert len(lines) > 0

    # Should have distinct sections
    assert any("User-agent:" in line for line in lines)
    assert any("Sitemap:" in line for line in lines)


def test_get_xml_sitemap_index():
    """Test sitemap index generation."""
    xml_str = indexing.get_xml_sitemap_index(post_count=100000)

    assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<sitemapindex" in xml_str
    assert "<sitemap>" in xml_str


def test_sitemap_index_valid_xml():
    """Test generated sitemap index is valid XML."""
    xml_str = indexing.get_xml_sitemap_index(post_count=100000)

    root = ET.fromstring(xml_str)
    assert "sitemapindex" in root.tag


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
