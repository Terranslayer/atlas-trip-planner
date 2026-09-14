from flask import Blueprint, render_template, jsonify, g, session, redirect, url_for

from ..auth import login_required
from ..repos import wishlist as wl_repo
from ..repos import visited as v_repo
from ..repos import trips as trips_repo
from ..services import currency as currency_service
from ..services import countries as countries_service


bp = Blueprint("dashboard", __name__)


@bp.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def index():
    uid = g.user["id"]
    wl_count = wl_repo.count_for_user(uid)
    v_count = v_repo.count_for_user(uid)
    t_count = trips_repo.count_for_user(uid)
    countries_visited = len(v_repo.distinct_countries_for_user(uid))
    upcoming = trips_repo.upcoming(uid, n=5)
    return render_template(
        "dashboard.html",
        wl_count=wl_count, v_count=v_count, t_count=t_count,
        countries_visited=countries_visited, upcoming=upcoming,
    )


@bp.route("/api/map-data")
@login_required
def map_data():
    uid = g.user["id"]
    visited = v_repo.list_for_user(uid)
    wishlist = wl_repo.list_for_user(uid)
    trips = trips_repo.list_for_user(uid)

    visited_pins = [
        {"lat": r["latitude"], "lon": r["longitude"], "name": r["city_name"],
         "country": r["country_cca3"], "kind": "visited",
         "note": r["journal"], "date": str(r["visited_date"]) if r["visited_date"] else None}
        for r in visited
    ]

    trip_data = []
    cities_in_trips = set()
    palette = ["#dc2626", "#0891b2", "#7e22ce", "#15803d", "#ca8a04", "#d97706"]
    for idx, t in enumerate(trips):
        stops = trips_repo.list_stops(t["id"])
        for s in stops:
            cities_in_trips.add(s["city_id"])
        trip_data.append({
            "id": t["id"], "name": t["name"],
            "color": palette[idx % len(palette)],
            "coords": [[s["latitude"], s["longitude"]] for s in stops],
            "cities": [{"lat": s["latitude"], "lon": s["longitude"], "name": s["city_name"]} for s in stops],
            "start_date": str(t["start_date"]) if t["start_date"] else None,
            "end_date": str(t["end_date"]) if t["end_date"] else None,
        })

    wishlist_pins = [
        {"lat": r["latitude"], "lon": r["longitude"], "name": r["city_name"],
         "country": r["country_cca3"], "kind": "wishlist",
         "priority": r["priority"], "note": r["note"]}
        for r in wishlist if r["city_id"] not in cities_in_trips
    ]

    # Aggregate currencies and languages across all wishlist countries
    seen_cca3 = {r["country_cca3"] for r in wishlist}
    currency_rows = {}
    languages = set()
    for cca3 in seen_cca3:
        cdoc = countries_service.get(cca3)
        if not cdoc:
            continue
        for code, info in (cdoc.get("currencies") or {}).items():
            if code not in currency_rows:
                r = currency_service.rate(code)
                if r:
                    currency_rows[code] = {
                        "code": code, "name": info.get("name"),
                        "rate": r["rate"], "as_of": r.get("as_of"),
                    }
        for lang in (cdoc.get("languages") or {}).values():
            languages.add(lang)

    return jsonify({
        "visited": visited_pins,
        "wishlist": wishlist_pins,
        "trips": trip_data,
        "currencies": list(currency_rows.values()),
        "languages": sorted(languages),
    })
