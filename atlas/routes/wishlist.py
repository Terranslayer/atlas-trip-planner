from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from ..auth import login_required
from ..repos import wishlist as wl_repo
from ..repos import visited as v_repo
from ..repos import cities as cities_repo


bp = Blueprint("wishlist", __name__)


@bp.route("/wishlist")
@login_required
def index():
    items = wl_repo.list_for_user(g.user["id"])
    return render_template("wishlist/list.html", items=items)


@bp.route("/wishlist/add", methods=["POST"])
@login_required
def add():
    try:
        city_id = int(request.form.get("city_id"))
        priority = int(request.form.get("priority", "1"))
        if priority not in (0, 1, 2):
            priority = 1
    except (TypeError, ValueError):
        flash("Invalid input.", "error")
        return redirect(request.referrer or url_for("dashboard.index"))

    note = (request.form.get("note") or "").strip()[:500]
    if cities_repo.get(city_id) is None:
        flash("Unknown city.", "error")
        return redirect(url_for("dashboard.index"))

    try:
        wl_repo.add(g.user["id"], city_id, note=note, priority=priority)
        flash("Added to wishlist.", "success")
    except wl_repo.DuplicateWishlistEntry:
        flash("Already on your wishlist.", "error")
    return redirect(request.referrer or url_for("wishlist.index"))


@bp.route("/wishlist/<int:item_id>/edit", methods=["POST"])
@login_required
def edit(item_id):
    note = (request.form.get("note") or "").strip()[:500]
    try:
        priority = int(request.form.get("priority", "1"))
        if priority not in (0, 1, 2):
            priority = 1
    except ValueError:
        priority = 1
    wl_repo.update(item_id, g.user["id"], note=note, priority=priority)
    flash("Updated.", "success")
    return redirect(url_for("wishlist.index"))


@bp.route("/wishlist/<int:item_id>/visit", methods=["POST"])
@login_required
def visit(item_id):
    """Promote a wishlist entry to a visited record. Removes the wishlist row on success."""
    item = wl_repo.get(item_id, g.user["id"])
    if item is None:
        flash("Wishlist entry not found.", "error")
        return redirect(url_for("wishlist.index"))

    visited_date = (request.form.get("visited_date") or "").strip()
    journal = (request.form.get("journal") or "").strip()[:500]

    try:
        d = date.fromisoformat(visited_date)
        if d > date.today():
            raise ValueError("future date")
    except ValueError:
        flash("Date must be a past or today's date (YYYY-MM-DD).", "error")
        return redirect(url_for("wishlist.index"))

    v_repo.add(g.user["id"], item["city_id"], visited_date, journal=journal or None)
    wl_repo.delete(item_id, g.user["id"])
    flash(f"Marked {item['city_name']} as visited.", "success")
    return redirect(url_for("wishlist.index"))


@bp.route("/wishlist/<int:item_id>/delete", methods=["POST"])
@login_required
def delete(item_id):
    wl_repo.delete(item_id, g.user["id"])
    flash("Removed.", "success")
    return redirect(url_for("wishlist.index"))
