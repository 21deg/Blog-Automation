// Render an SVG file to a 1536x1024 JPEG with the pre-installed Chromium.
// Usage: node scripts/render_svg.js in.svg out.jpg
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const svg = fs.readFileSync(process.argv[2], 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1536, height: 1024 } });
  await page.setContent('<html><body style="margin:0;background:#F3E6D3">' + svg + '</body></html>');
  await page.screenshot({ path: process.argv[3], type: 'jpeg', quality: 88 });
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
