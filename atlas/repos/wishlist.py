import sqlite3

from .sqlite import get_conn


class DuplicateWishlistEntry(Exception):
    """Raised when (user_id, city_id) already exists in wishlist."""


def add(user_id, city_id, note=None, priority=1):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO wishlist (user_id, city_id, note, priority) VALUES (?, ?, ?, ?)",
            (user_id, city_id, note, priority),
        )
    except sqlite3.IntegrityError as e:
        # The UNIQUE(user_id, city_id) constraint is the only one that can fire
        # on this insert; surface it as a typed error so the route can render
        # a friendly message without swallowing unrelated exceptions.
        raise DuplicateWishlistEntry from e
    conn.commit()
    return cur.lastrowid


def update(item_id, user_id, note, priority):
    conn = get_conn()
    conn.execute(
        "UPDATE wishlist SET note=?, priority=? WHERE id=? AND user_id=?",
        (note, priority, item_id, user_id),
    )
    conn.commit()


def delete(item_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM wishlist WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()


def get(item_id, user_id):
    return get_conn().execute(
        """SELECT w.*, c.name AS city_name, c.country_cca3, c.country_code,
                  c.latitude, c.longitude
           FROM wishlist w JOIN cities c ON c.id = w.city_id
           WHERE w.id=? AND w.user_id=?""",
        (item_id, user_id),
    ).fetchone()


def list_for_user(user_id):
    return get_conn().execute(
        """SELECT w.id, w.note, w.priority, w.added_at, w.city_id,
                  c.name AS city_name, c.country_cca3, c.country_code,
                  c.latitude, c.longitude, c.population
           FROM wishlist w JOIN cities c ON c.id = w.city_id
           WHERE w.user_id=?
           ORDER BY w.priority DESC, w.added_at DESC""",
        (user_id,),
    ).fetchall()


def count_for_user(user_id):
    return get_conn().execute(
        "SELECT COUNT(*) AS n FROM wishlist WHERE user_id=?", (user_id,)
    ).fetchone()["n"]
