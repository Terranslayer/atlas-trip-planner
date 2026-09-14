from datetime import datetime, timedelta, timezone

from flask import current_app

from .http import get_json, HTTPError
from ..repos import mongo as mongo_repo


COLLECTION = "climate_cache"


def _is_fresh(doc, ttl_hours):
    cached = doc.get("cached_at")
    if not cached:
        return False
    if cached.tzinfo is None:
        cached = cached.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cached) < timedelta(hours=ttl_hours)


def _normalize(raw, city_id, name=None, lat=None, lon=None):
    """Collapse multi-year monthly observations into per-month-of-year averages."""
    monthly_raw = raw.get("monthly", {})
    times = monthly_raw.get("time", [])
    temps = monthly_raw.get("temperature_2m_mean", [])
    precip = monthly_raw.get("precipitation_sum", [])
    by_month = {m: {"t": [], "p": []} for m in range(1, 13)}
    for i, t_iso in enumerate(times):
        try:
            month = int(t_iso[5:7])
        except (ValueError, IndexError):
            continue
        if i < len(temps) and temps[i] is not None:
            by_month[month]["t"].append(float(temps[i]))
        if i < len(precip) and precip[i] is not None:
            by_month[month]["p"].append(float(precip[i]))
    monthly = []
    for m in range(1, 13):
        ts = by_month[m]["t"]
        ps = by_month[m]["p"]
        monthly.append({
            "month": m,
            "tavg_c": sum(ts) / len(ts) if ts else None,
            "precip_mm": sum(ps) / len(ps) if ps else None,
        })
    return {
        "_id": city_id, "city_name": name, "lat": lat, "lon": lon,
        "monthly": monthly,
        "cached_at": datetime.now(timezone.utc),
    }


def for_city(city_id, lat, lon, name=None):
    db = mongo_repo.get_db()
    col = db[COLLECTION]
    cached = col.find_one({"_id": city_id})
    ttl = current_app.config["CACHE_TTL_HOURS_CLIMATE"]

    if cached and _is_fresh(cached, ttl):
        return cached

    base = current_app.config["OPEN_METEO_BASE"]
    try:
        data = get_json(
            f"{base}/climate",
            params={
                "latitude": lat, "longitude": lon,
                "start_date": "1991-01-01", "end_date": "2020-12-31",
                "monthly": "temperature_2m_mean,precipitation_sum",
                "models": "MRI_AGCM3_2_S",
            },
            timeout=15,
        )
        doc = _normalize(data, city_id, name=name, lat=lat, lon=lon)
        col.replace_one({"_id": city_id}, doc, upsert=True)
        return doc
    except HTTPError:
        if cached:
            cached["stale"] = True
            return cached
        return None
