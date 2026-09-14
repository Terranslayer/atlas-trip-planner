from datetime import datetime, timedelta, timezone

from flask import current_app

from .http import get_json, HTTPError
from ..repos import mongo as mongo_repo


COLLECTION = "currency_cache"


def _is_fresh(doc, ttl_hours):
    cached = doc.get("cached_at")
    if not cached:
        return False
    if cached.tzinfo is None:
        cached = cached.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cached) < timedelta(hours=ttl_hours)


def rate(to_code, from_code="USD"):
    key = f"{from_code}_{to_code}"
    db = mongo_repo.get_db()
    col = db[COLLECTION]
    cached = col.find_one({"_id": key})
    ttl = current_app.config["CACHE_TTL_HOURS_CURRENCY"]

    if cached and _is_fresh(cached, ttl):
        return cached

    base = current_app.config["FRANKFURTER_BASE"]
    try:
        data = get_json(f"{base}/latest", params={"from": from_code, "to": to_code})
        rate_value = float(data["rates"][to_code])
        doc = {
            "_id": key, "from": from_code, "to": to_code,
            "rate": rate_value, "as_of": data.get("date"),
            "cached_at": datetime.now(timezone.utc),
        }
        col.replace_one({"_id": key}, doc, upsert=True)
        return doc
    except (HTTPError, KeyError, ValueError):
        if cached:
            cached["stale"] = True
            return cached
        return None
