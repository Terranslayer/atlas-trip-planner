from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, request, flash

from ..forms import RegisterForm, LoginForm
from ..repos import users as users_repo
from ..auth import login_user, logout_user


bp = Blueprint("auth", __name__)


def _safe_next(target):
    # Only allow same-origin, root-relative paths to defeat open-redirect attacks.
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/"):
        return None
    return target


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if users_repo.find_by_username(form.username.data):
            form.username.errors.append("Username is already taken.")
        else:
            uid = users_repo.create(form.username.data, form.password.data)
            login_user(uid)
            return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = users_repo.authenticate(form.username.data, form.password.data)
        if user is None:
            flash("Invalid credentials.", "error")
            return render_template("auth/login.html", form=form), 200
        login_user(user["id"])
        next_url = _safe_next(request.args.get("next")) or url_for("dashboard.index")
        return redirect(next_url)
    return render_template("auth/login.html", form=form)


# POST-only: GET-logout would allow third-party links/images to forcibly log a user out.
@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
