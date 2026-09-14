"""Wikivoyage travel-notes service.

Fetches the MediaWiki HTML of selected sections ("Get in", "Stay safe",
"Respect", "Money") from each country's Wikivoyage page, sanitises the HTML
to a small whitelist, rewrites internal /wiki/... links to absolute URLs,
and caches the result per country in MongoDB (TTL 7 days).
"""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import bleach
from flask import current_app

from .http import get_json, HTTPError
from ..repos import mongo as mongo_repo


COLLECTION = "travel_notes_cache"
API_URL = "https://en.wikivoyage.org/w/api.php"
SITE_BASE = "https://en.wikivoyage.org/"
TTL_HOURS = 24 * 7

# Wikimedia API policy requires a contact-bearing User-Agent on every request.
USER_AGENT = "AtlasCapstone/1.0 (ENPM818Q Capstone; yxz2803@umd.edu)"
HEADERS = {"User-Agent": USER_AGENT}

# Section titles we care about. Matched case-insensitively against the
# `line` field of the parse?prop=sections response.
WANTED_SECTIONS = ("Get in", "Stay safe", "Respect", "Money")

# HTML sanitisation whitelist. Wikivoyage's section HTML is mostly p / ul /
# ol / table / a / strong / em, so this whitelist preserves structure while
# stripping anything that could carry script or style.
ALLOWED_TAGS = {
    "p", "br", "hr", "div", "span",
    "a",
    "ul", "ol", "li", "dl", "dt", "dd",
    "strong", "em", "b", "i", "u", "small",
    "h3", "h4", "h5",
    "table", "thead", "tbody", "tr", "th", "td",
    "code", "pre", "blockquote",
}
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "*": [],  # no global attrs (drop class/id/style/data-*)
}


def _is_fresh(doc, ttl_hours=TTL_HOURS):
    cached = doc.get("cached_at")
    if not cached:
        return False
    if cached.tzinfo is None:
        cached = cached.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cached) < timedelta(hours=ttl_hours)


# Pre-bleach scrubbers. bleach.clean(strip=True) drops tags but keeps inner
# text; for <style> and <script> the inner text is CSS / JS, which would leak
# into the rendered page as plain text. Remove these elements wholesale first.
_STYLE_RE  = re.compile(r"<style\b[^>]*>.*?</style>",  flags=re.DOTALL | re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", flags=re.DOTALL | re.IGNORECASE)
# Wikivoyage's section parse output starts with a repeated heading block of
# the shape `<div>...<h1|h2|h3>Title</h3>...</div>`. We collapse that down so
# the <summary> in our template already carries the title.
_LEADING_HEADING_RE = re.compile(
    r"^\s*<div[^>]*>.*?</div>", flags=re.DOTALL
)


def _sanitise_section(html: str) -> str:
    """Whitelist tags, drop attributes, rewrite relative wiki links."""
    html = _STYLE_RE.sub("", html)
    html = _SCRIPT_RE.sub("", html)
    # Drop the leading heading wrapper (only the first match, only if it is
    # at the very start of the response).
    html = _LEADING_HEADING_RE.sub("", html, count=1)

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
        strip_comments=True,
    )
    # Rewrite Wikivoyage internal links to absolute URLs so they do not
    # resolve against the Atlas host.
    return cleaned.replace('href="/wiki/', f'href="{SITE_BASE}wiki/').replace(
        'href="/w/', f'href="{SITE_BASE}w/'
    )


def for_country(country_name: str):
    """Return a cache document with sanitised section HTML for the country,
    or None if Wikivoyage has no usable page and there's no cached fallback.
    """
    if not country_name:
        return None
    db = mongo_repo.get_db()
    col = db[COLLECTION]
    cached = col.find_one({"_id": country_name})

    if cached and _is_fresh(cached):
        return cached

    try:
        toc = get_json(
            API_URL,
            params={
                "action": "parse",
                "page": country_name,
                "prop": "sections",
                "format": "json",
                "redirects": 1,
                "disableeditsection": 1,
            },
            headers=HEADERS,
            timeout=10,
        )
    except HTTPError:
        if cached:
            cached["stale"] = True
            return cached
        return None

    sections_meta = (toc.get("parse") or {}).get("sections") or []
    wanted_map = {}
    for sec in sections_meta:
        line = (sec.get("line") or "").strip()
        for target in WANTED_SECTIONS:
            if line.lower() == target.lower() and target not in wanted_map:
                wanted_map[target] = sec.get("index")
                break

    sections = {}
    for title, idx in wanted_map.items():
        if idx is None:
            continue
        try:
            data = get_json(
                API_URL,
                params={
                    "action": "parse",
                    "page": country_name,
                    "section": idx,
                    "prop": "text",
                    "format": "json",
                    "redirects": 1,
                },
                headers=HEADERS,
                timeout=10,
            )
        except HTTPError:
            continue
        raw_html = ((data.get("parse") or {}).get("text") or {}).get("*", "")
        if raw_html:
            sections[title] = _sanitise_section(raw_html)

    if not sections and not cached:
        return None

    doc = {
        "_id": country_name,
        "sections": sections or (cached or {}).get("sections", {}),
        "source_url": urljoin(SITE_BASE, "wiki/" + country_name.replace(" ", "_")),
        "cached_at": datetime.now(timezone.utc),
    }
    col.replace_one({"_id": country_name}, doc, upsert=True)
    return doc
