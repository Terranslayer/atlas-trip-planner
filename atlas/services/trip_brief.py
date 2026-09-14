from datetime import date

from . import countries as countries_service
from . import currency as currency_service
from . import climate as climate_service
from . import advisory as advisory_service
from .scoring import climate_match, verdict
from ..repos import trips as trips_repo


def _months_for_stop(stop):
    """Return the calendar months covered by a stop's date range."""
    a_raw = stop["arrival_date"]
    d_raw = stop["departure_date"]
    if not a_raw or not d_raw:
        return []
    try:
        a = date.fromisoformat(a_raw) if isinstance(a_raw, str) else a_raw
        d = date.fromisoformat(d_raw) if isinstance(d_raw, str) else d_raw
    except (TypeError, ValueError):
        return []
    months = set()
    cur = a
    while cur <= d:
        months.add(cur.month)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return sorted(months)


def _score_stop(stop, climate_doc):
    months = _months_for_stop(stop)
    if not climate_doc or not months:
        return None, None
    monthly = climate_doc.get("monthly", [])
    scores = []
    for m in months:
        rec = next((row for row in monthly if row.get("month") == m), None)
        if not rec:
            continue
        s = climate_match(rec.get("tavg_c"), rec.get("precip_mm"))
        scores.append(s)
    if not scores:
        return None, None
    avg = sum(scores) / len(scores)
    return round(avg, 3), verdict(avg)


def build(user_id, trip_id):
    trip = trips_repo.get(trip_id, user_id)
    if not trip:
        return None

    stops_raw = trips_repo.list_stops(trip_id)
    stops = []
    countries = {}
    currencies = {}
    languages = set()
    advisories = {}

    for s in stops_raw:
        cca3 = s["country_cca3"]
        if cca3 not in countries:
            country = countries_service.get(cca3) or {"_id": cca3, "name": {}, "currencies": {}, "languages": {}}
            countries[cca3] = country
        country = countries[cca3]

        climate = climate_service.for_city(s["city_id"], s["latitude"], s["longitude"], name=s["city_name"])
        score, vrd = _score_stop(s, climate)

        stop = dict(s)
        stop["climate"] = climate
        stop["climate_score"] = score
        stop["climate_verdict"] = vrd
        stops.append(stop)

        for code in (country.get("currencies") or {}).keys():
            if code not in currencies:
                rate_doc = currency_service.rate(code)
                if rate_doc:
                    currencies[code] = {
                        "code": code, "name": country["currencies"][code].get("name"),
                        "symbol": country["currencies"][code].get("symbol"),
                        "rate": rate_doc.get("rate"), "as_of": rate_doc.get("as_of"),
                        "stale": rate_doc.get("stale", False),
                    }
        for lang in (country.get("languages") or {}).values():
            languages.add(lang)
        if cca3 not in advisories:
            advisories[cca3] = advisory_service.for_cca3(cca3)

    return {
        "trip": trip,
        "stops": stops,
        "countries": countries,
        "currencies": currencies,
        "languages": sorted(languages),
        "advisories": advisories,
    }
