from flask import Blueprint, request, jsonify, render_template

from ..auth import login_required
from ..repos import cities as cities_repo
from ..repos import mongo as mongo_repo


bp = Blueprint("cities", __name__)


def _country_names_for(cca3s):
    """Return {cca3: common_name} for the given codes via one MongoDB query."""
    codes = sorted(set(c for c in cca3s if c))
    if not codes:
        return {}
    cursor = mongo_repo.get_db()["countries_cache"].find(
        {"_id": {"$in": codes}},
        {"_id": 1, "name.common": 1},
    )
    return {doc["_id"]: (doc.get("name") or {}).get("common") or doc["_id"]
            for doc in cursor}


@bp.route("/cities")
@login_required
def browse():
    q = (request.args.get("q") or "").strip()[:60]
    results = cities_repo.search(q, limit=50) if q else []
    country_names = _country_names_for(r["country_cca3"] for r in results)
    return render_template(
        "cities/browse.html",
        q=q, results=results, country_names=country_names,
    )


@bp.route("/cities/search")
@login_required
def search():
    q = (request.args.get("q") or "").strip()[:60]
    if len(q) < 1:
        return jsonify({"results": []})
    rows = cities_repo.search(q, limit=20)
    return jsonify({
        "results": [
            {
                "id": r["id"], "name": r["name"], "country_cca3": r["country_cca3"],
                "country_code": r["country_code"], "admin1": r["admin1"],
                "lat": r["latitude"], "lon": r["longitude"],
                "population": r["population"],
            }
            for r in rows
        ]
    })
