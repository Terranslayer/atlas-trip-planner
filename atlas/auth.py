from functools import wraps
from flask import session, redirect, url_for, request, g

from .repos import users as users_repo


def login_user(user_id: int):
    session.clear()
    session["user_id"] = user_id


def logout_user():
    session.clear()


def current_user():
    if "user_id" not in session:
        return None
    return users_repo.find_by_id(session["user_id"])


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        g.user = users_repo.find_by_id(session["user_id"])
        if g.user is None:
            session.clear()
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapper
