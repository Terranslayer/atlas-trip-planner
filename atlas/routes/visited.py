from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from ..auth import login_required
from ..repos import visited as v_repo
from ..repos import cities as cities_repo


bp = Blueprint("visited", __name__)


@bp.route("/visited")
@login_required
def index():
    items = v_repo.list_for_user(g.user["id"])
    return render_template("visited/list.html", items=items)


@bp.route("/visited/add", methods=["POST"])
@login_required
def add():
    try:
        city_id = int(request.form.get("city_id"))
    except (TypeError, ValueError):
        flash("Invalid city.", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    visited_date = (request.form.get("visited_date") or "").strip()
    journal = (request.form.get("journal") or "").strip()[:500]

    try:
        d = date.fromisoformat(visited_date)
        if d > date.today():
            raise ValueError("future date")
    except ValueError:
        flash("Date must be a past or today's date (YYYY-MM-DD).", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    if cities_repo.get(city_id) is None:
        flash("Unknown city.", "error")
        return redirect(url_for("dashboard.index"))

    v_repo.add(g.user["id"], city_id, visited_date, journal=journal)
    flash("Visit logged.", "success")
    return redirect(request.referrer or url_for("visited.index"))


@bp.route("/visited/<int:item_id>/edit", methods=["POST"])
@login_required
def edit(item_id):
    visited_date = (request.form.get("visited_date") or "").strip()
    journal = (request.form.get("journal") or "").strip()[:500]
    try:
        d = date.fromisoformat(visited_date)
        if d > date.today():
            raise ValueError("future date")
    except ValueError:
        flash("Date must be a past or today's date (YYYY-MM-DD).", "error")
        return redirect(url_for("visited.index"))
    v_repo.update(item_id, g.user["id"], visited_date, journal)
    flash("Visit updated.", "success")
    return redirect(url_for("visited.index"))


@bp.route("/visited/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    v_repo.delete(item_id, g.user["id"])
    flash("Removed.", "success")
    return redirect(url_for("visited.index"))
