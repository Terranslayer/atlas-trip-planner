import re

from flask import Blueprint, render_template, abort

from ..auth import login_required
from ..services import countries as countries_service
from ..services import currency as currency_service
from ..services import advisory as advisory_service
from ..services import wikivoyage as wikivoyage_service


bp = Blueprint("countries", __name__)
CCA3_RE = re.compile(r"^[A-Z]{3}$")


@bp.route("/countries/<cca3>")
@login_required
def detail(cca3):
    if not CCA3_RE.match(cca3):
        abort(404)
    country = countries_service.get(cca3)
    if not country:
        abort(404)

    currencies = country.get("currencies", {}) or {}
    rates = {}
    for code in currencies.keys():
        rates[code] = currency_service.rate(code)

    advisory = advisory_service.for_cca3(cca3)

    # Wikivoyage notes are best-effort: if the page doesn't exist or the API
    # is unreachable, the template renders without the section.
    travel_notes = None
    common_name = (country.get("name") or {}).get("common")
    if common_name:
        try:
            travel_notes = wikivoyage_service.for_country(common_name)
        except Exception:
            travel_notes = None

    warnings = []
    if country.get("stale"):
        warnings.append("Country data shown from cache; upstream temporarily unavailable.")
    for code, rate in rates.items():
        if rate and rate.get("stale"):
            warnings.append(f"Exchange rate for {code} shown from cache.")
    if travel_notes and travel_notes.get("stale"):
        warnings.append("Travel notes shown from cache.")
    cache_warning = " ".join(warnings) if warnings else None

    return render_template(
        "countries/detail.html",
        country=country, rates=rates, advisory=advisory,
        travel_notes=travel_notes,
        cache_warning=cache_warning,
    )
