from datetime import datetime, timedelta, timezone

from flask import current_app

from .http import get_json, HTTPError
from ..repos import mongo as mongo_repo


COLLECTION = "countries_cache"


def _is_fresh(doc, ttl_hours):
    cached = doc.get("cached_at")
    if not cached:
        return False
    if cached.tzinfo is None:
        cached = cached.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cached) < timedelta(hours=ttl_hours)


def _normalize(raw, cca3):
    return {
        "_id": cca3,
        "name": raw.get("name", {}),
        "cca2": raw.get("cca2"),
        "capital": raw.get("capital", []),
        "region": raw.get("region"),
        "subregion": raw.get("subregion"),
        "population": raw.get("population"),
        "area": raw.get("area"),
        "languages": raw.get("languages", {}),
        "currencies": raw.get("currencies", {}),
        "flags": raw.get("flags", {}),
        "timezones": raw.get("timezones", []),
        "borders": raw.get("borders", []),
        "latlng": raw.get("latlng", []),
        "car": raw.get("car", {}),
        "idd": raw.get("idd", {}),
        "cached_at": datetime.now(timezone.utc),
    }


def get(cca3):
    db = mongo_repo.get_db()
    col = db[COLLECTION]
    cached = col.find_one({"_id": cca3})
    ttl = current_app.config["CACHE_TTL_HOURS_COUNTRIES"]

    if cached and _is_fresh(cached, ttl):
        return cached

    base = current_app.config["REST_COUNTRIES_BASE"]
    try:
        data = get_json(f"{base}/alpha/{cca3}")
        if isinstance(data, list):
            data = data[0]
        doc = _normalize(data, cca3)
        col.replace_one({"_id": cca3}, doc, upsert=True)
        return doc
    except HTTPError:
        if cached:
            cached["stale"] = True
            return cached
        return None
