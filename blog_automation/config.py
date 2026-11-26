"""Settings shared by the picker, generator and validator."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
OUTPUT_DIR = ROOT / "output"
POST_INVENTORY = ROOT / "analysis" / "data" / "all_posts_metadata.json"
BACKLOG = ROOT / "data" / "backlog.json"

MODEL = "claude-opus-5-5"
# Server-side refusal fallback (routes a declined request to another model).
FALLBACK_BETA = "server-side-fallback-2026-07-01"

TRENDS_RSS = "https://trends.google.com/trending/rss?geo={geo}"
DEFAULT_GEO = "IN"

SITE = "https://21degrees.in"
BOOKING_URL = "https://21degrees.setmore.com/services/s1578e91e34903b0a632dfcdcaff71d9526b5749c"
SERVICE_PAGES = {
    "Home / Virtual CFO services": f"{SITE}/",
    "Accounts services": f"{SITE}/accounts/",
    "Book a consultation": BOOKING_URL,
}

# Topic clusters every post maps to (see analysis/blog-pattern-analysis.md §4.1).
PILLARS = {
    "virtual-cfo": "Virtual CFO: pricing, when to hire, vs CA / accountant, what's included",
    "gst-compliance": "GST, ITC, TDS, ROC and regulatory compliance",
    "cash-flow": "Cash flow, working capital, cost control, profitability",
    "funding-banking": "Funding, loans, RBI policy, banking, investors",
    "industry-playbooks": "Industry playbooks: restaurants, manufacturing, D2C, SaaS, retail",
    "tax-planning": "Income tax, tax planning, deadlines, founders' personal finance",
    "business-growth": "Strategy, leadership and growth lessons for founders",
}

# Picker weighting by angle type. News with a direct finance link gets a small boost;
# sport / celebrity / culture metaphors stay fully in play (they drive traffic too).
ANGLE_WEIGHTS = {"direct": 1.15, "metaphor": 1.0, "none": 0.0}

# Evergreen keywords to pair with a trending hook (searchable in India).
SEED_KEYWORDS = [
    "virtual cfo services", "virtual cfo cost in india", "cfo vs ca", "cash flow management",
    "working capital management", "gst input tax credit", "gst filing", "itr filing",
    "tax planning for business", "startup funding india", "business loan", "msme",
    "restaurant profit margin", "manufacturing cost control", "financial planning for small business",
    "bookkeeping services", "business budgeting", "profit and loss statement",
]

# Generation targets (analysis §4.4). The validator enforces these.
TARGETS = {
    "words": (1400, 2000),
    "title_tag_max": 60,
    "meta_desc": (140, 160),
    "slug_max_words": 6,
    "quick_answer_words": (40, 60),
    "avg_sentence_words_max": 15,
    "faq_count": (4, 6),
    "external_links_min": 2,
    "internal_links": (3, 5),
    "brand_mentions": (3, 5),
    "legal_name_max": 2,
    "question_heading_share_min": 0.5,
}

BANNED_PHRASES = [
    "idiot",
    "we already feel sorry",
    "pioneers, not imitators",
    "partners, not vendors",
    "not just another virtual cfo",
    "the question is not whether you can afford us",
    "let me leave you with this",
]

# WordPress category IDs on 21degrees.in (Finance=1, Career=2, Tech=8, Virtual CFO=26).
# Existing categories are reused; no new categories are created.
CATEGORY_IDS = {
    "default": [1, 26],
    "business-growth": [1, 26, 2],
}

# Daily schedule: posts go live spread between these hours (IST), each at least
# min_review_hours after the run that created it, so there is time to review.
SCHEDULE = {"posts_per_day": 10, "first_hour_ist": 11, "last_hour_ist": 20, "min_review_hours": 4,
            # two runs a day of 5 posts each: the morning run's posts go live 10:00-12:00 IST,
            # the second run's posts 17:00-19:00 IST (every 30 minutes)
            "windows": {"morning": [10, 12], "evening": [17, 19]}, "batch": 5}

# Featured images. engine: "auto" tries Nano Banana (needs a Google AI Studio key with billing,
# about $0.034 per image) and falls back to a free branded title card; "card" never calls the API.
IMAGES = {
    "engine": "unsplash",  # free Unsplash photos (UNSPLASH_ACCESS_KEY); falls back to drawings / card
    "model": "gemini-nano-banana-2.1",
    "aspect_ratio": "3:2",
    "image_size": "1K",
    "api_revision": "2026-05-20",
}
