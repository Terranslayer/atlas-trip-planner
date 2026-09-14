from datetime import date

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, g, abort, Response, jsonify)

from ..auth import login_required
from ..repos import trips as trips_repo
from ..repos import cities as cities_repo
from ..services import trip_brief


bp = Blueprint("trips", __name__)


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        return None


@bp.route("/trips")
@login_required
def index():
    trips = trips_repo.list_for_user(g.user["id"])
    return render_template("trips/list.html", trips=trips)


@bp.route("/trips/new", methods=["POST"])
@login_required
def new():
    name = (request.form.get("name") or "").strip()[:60]
    if not name:
        flash("Trip name is required.", "error")
        return redirect(url_for("trips.index"))
    sd = _parse_date(request.form.get("start_date"))
    ed = _parse_date(request.form.get("end_date"))
    if sd and ed and ed < sd:
        flash("End date must be on or after start date.", "error")
        return redirect(url_for("trips.index"))
    tid = trips_repo.create(g.user["id"], name, sd, ed)
    return redirect(url_for("trips.brief", trip_id=tid))


@bp.route("/trips/<int:trip_id>")
@login_required
def brief(trip_id):
    data = trip_brief.build(g.user["id"], trip_id)
    if data is None:
        abort(404)
    return render_template("trips/brief.html", **data)


@bp.route("/trips/<int:trip_id>/edit", methods=["POST"])
@login_required
def edit(trip_id):
    if not trips_repo.get(trip_id, g.user["id"]):
        abort(404)
    name = (request.form.get("name") or "").strip()[:60]
    sd = _parse_date(request.form.get("start_date"))
    ed = _parse_date(request.form.get("end_date"))
    notes = (request.form.get("notes") or "").strip()[:1000]
    trips_repo.update(trip_id, g.user["id"], name, sd, ed, notes)
    flash("Trip updated.", "success")
    return redirect(url_for("trips.brief", trip_id=trip_id))


@bp.route("/trips/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete(trip_id):
    trips_repo.delete(trip_id, g.user["id"])
    flash("Trip deleted.", "success")
    return redirect(url_for("trips.index"))


@bp.route("/trips/<int:trip_id>/stops/add", methods=["POST"])
@login_required
def add_stop(trip_id):
    if not trips_repo.get(trip_id, g.user["id"]):
        abort(404)
    try:
        city_id = int(request.form.get("city_id"))
    except (TypeError, ValueError):
        flash("Invalid city.", "error")
        return redirect(url_for("trips.brief", trip_id=trip_id))
    if cities_repo.get(city_id) is None:
        flash("Unknown city.", "error")
        return redirect(url_for("trips.brief", trip_id=trip_id))
    arrival = _parse_date(request.form.get("arrival_date"))
    departure = _parse_date(request.form.get("departure_date"))
    if arrival and departure and departure < arrival:
        flash("Departure must be on or after arrival.", "error")
        return redirect(url_for("trips.brief", trip_id=trip_id))
    trips_repo.add_stop(trip_id, city_id, arrival, departure)
    return redirect(url_for("trips.brief", trip_id=trip_id))


@bp.route("/trips/<int:trip_id>/stops/<int:stop_id>/edit", methods=["POST"])
@login_required
def edit_stop(trip_id, stop_id):
    if not trips_repo.get(trip_id, g.user["id"]):
        abort(404)
    arrival = _parse_date(request.form.get("arrival_date"))
    departure = _parse_date(request.form.get("departure_date"))
    notes = (request.form.get("notes") or "").strip()[:500]
    trips_repo.update_stop(stop_id, trip_id, arrival, departure, notes)
    return redirect(url_for("trips.brief", trip_id=trip_id))


@bp.route("/trips/<int:trip_id>/stops/<int:stop_id>/delete", methods=["POST"])
@login_required
def delete_stop(trip_id, stop_id):
    if not trips_repo.get(trip_id, g.user["id"]):
        abort(404)
    trips_repo.delete_stop(stop_id, trip_id)
    return redirect(url_for("trips.brief", trip_id=trip_id))


@bp.route("/trips/<int:trip_id>/stops/reorder", methods=["POST"])
@login_required
def reorder_stops(trip_id):
    if not trips_repo.get(trip_id, g.user["id"]):
        abort(404)
    payload = request.get_json(silent=True) or {}
    order = payload.get("order")
    if not isinstance(order, list) or not all(isinstance(i, int) for i in order):
        return jsonify({"ok": False, "error": "invalid order"}), 400
    trips_repo.reorder_stops(trip_id, order)
    return jsonify({"ok": True})


@bp.route("/trips/<int:trip_id>/export.md")
@login_required
def export_md(trip_id):
    data = trip_brief.build(g.user["id"], trip_id)
    if data is None:
        abort(404)
    body = render_template("trips/brief.md.jinja", **data)
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in data["trip"]["name"])
    headers = {"Content-Disposition": f'attachment; filename="trip_{safe_name}.md"'}
    return Response(body, mimetype="text/markdown", headers=headers)
