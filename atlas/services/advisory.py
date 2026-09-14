import re
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import current_app
import feedparser

from .http import get_text, HTTPError
from ..repos import mongo as mongo_repo


COLLECTION = "advisory_cache"
LEVEL_RE = re.compile(r"Level\s+(\d)", re.I)
_TRAILING_ADVISORY_RE = re.compile(r"\s+Travel Advisory$", re.I)

# State Department feed item titles refer to a few countries by names that
# don't match REST Countries' common/official names. Map them to the
# canonical REST Countries common name before looking up the cca3.
_NAME_ALIASES = {
    "Burma": "Myanmar",
    "Vatican City": "Holy See",
    "Cape Verde": "Cabo Verde",
    "Macedonia": "North Macedonia",
    "Swaziland": "Eswatini",
    "Czech Republic": "Czechia",
    "East Timor": "Timor-Leste",
    "Ivory Coast": "Côte d'Ivoire",
}

# Auto-refresh coordination. The State Department RSS is a single document
# covering all countries, so it cannot be fetched lazily per cca3 the way
# countries / currency / climate / wikivoyage are. Instead, the first read
# after the cache passes its TTL triggers a one-shot refresh in the
# foreground; subsequent reads in the same process pay zero overhead.
_REFRESH_LOCK = threading.Lock()
_LAST_REFRESH_TS = 0.0
_REFRESH_TTL_SECONDS = 24 * 3600


def _parse_title(title):
    """Extract country name, level, and trailing text from e.g.
    'Japan - Level 1: Exercise Normal Precautions'.

    Some titles have the form 'Mexico Travel Advisory' with no level; in that
    case the trailing 'Travel Advisory' suffix is stripped and level is None.
    """
    m = LEVEL_RE.search(title)
    level = int(m.group(1)) if m else None
    parts = title.split(" - Level", 1)
    country_name = (parts[0].strip() if parts else title.strip())
    country_name = _TRAILING_ADVISORY_RE.sub("", country_name).strip()
    text_after_level = title.split(": ", 1)[1].strip() if ": " in title else ""
    return country_name, level, text_after_level


def _resolve_cca3(country_name):
    """Look up cca3 for an advisory entry by country name.

    The State Department feed uses FIPS 10-4 country codes in its <category>
    field, not ISO 3166-1 alpha-2, so the codes cannot be mapped through the
    project's ISO-based cca2_to_cca3.json. Resolve via the country name
    instead, with a small alias table for the names REST Countries spells
    differently (e.g. Burma vs Myanmar).
    """
    if not country_name:
        return None, None
    canonical = _NAME_ALIASES.get(country_name, country_name)
    col = mongo_repo.get_db()["countries_cache"]
    for field in ("name.common", "name.official"):
        doc = col.find_one({field: canonical}, projection={"_id": 1, "cca2": 1})
        if doc:
            return doc["_id"], doc.get("cca2")
    return None, None


def refresh():
    """Fetch the RSS feed, parse each item, upsert advisory docs.

    Returns number of advisory documents written."""
    url = current_app.config["US_ADVISORY_RSS"]
    try:
        text = get_text(url, timeout=10)
    except HTTPError:
        return 0

    feed = feedparser.parse(text)
    db = mongo_repo.get_db()
    col = db[COLLECTION]
    written = 0

    for item in feed.entries:
        title = item.get("title", "")
        country, level, level_text = _parse_title(title)
        cca3, cca2 = _resolve_cca3(country)
        if not cca3:
            continue
        doc = {
            "_id": cca3, "cca2": cca2, "country": country,
            "level": level, "level_text": level_text,
            "summary": item.get("summary", "") or item.get("description", ""),
            "url": item.get("link", ""), "published": item.get("published", ""),
            "cached_at": datetime.now(timezone.utc),
        }
        col.replace_one({"_id": cca3}, doc, upsert=True)
        written += 1
    return written


def _maybe_refresh():
    """Refresh the advisory cache if it is empty or older than the TTL.

    Cheap fast-path: every call after the first one within the TTL window
    returns in nanoseconds via a process-local timestamp check. Only the
    boundary call pays the Mongo round-trip and (if needed) the upstream
    RSS fetch. Refresh failures are swallowed so a transient network error
    on the State Department feed never breaks a country detail page render.
    """
    global _LAST_REFRESH_TS

    # Don't auto-fetch during tests; tests inject their own state.
    if current_app and current_app.config.get("TESTING"):
        return

    if time.time() - _LAST_REFRESH_TS < _REFRESH_TTL_SECONDS:
        return

    with _REFRESH_LOCK:
        if time.time() - _LAST_REFRESH_TS < _REFRESH_TTL_SECONDS:
            return

        # Another worker process (or yesterday's run on this process) may
        # have already refreshed within the TTL. Check Mongo before paying
        # for the upstream fetch.
        col = mongo_repo.get_db()[COLLECTION]
        sentinel = col.find_one({}, sort=[("cached_at", -1)],
                                projection={"cached_at": 1})
        last = sentinel and sentinel.get("cached_at")
        if last and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if last and (now - last) < timedelta(seconds=_REFRESH_TTL_SECONDS):
            _LAST_REFRESH_TS = time.time()
            return

        try:
            written = refresh()
        except Exception:
            # Stale data is better than a broken page; keep what we have.
            # Don't update the timestamp so the next request retries instead
            # of waiting another full TTL window.
            return
        if written:
            _LAST_REFRESH_TS = time.time()


def for_cca3(cca3):
    _maybe_refresh()
    return mongo_repo.get_db()[COLLECTION].find_one({"_id": cca3})
