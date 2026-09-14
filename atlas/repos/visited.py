from .sqlite import get_conn


def add(user_id, city_id, visited_date, journal=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO visited (user_id, city_id, visited_date, journal) VALUES (?, ?, ?, ?)",
        (user_id, city_id, visited_date, journal),
    )
    conn.commit()
    return cur.lastrowid


def update(item_id, user_id, visited_date, journal):
    conn = get_conn()
    conn.execute(
        "UPDATE visited SET visited_date=?, journal=? WHERE id=? AND user_id=?",
        (visited_date, journal, item_id, user_id),
    )
    conn.commit()


def delete(item_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM visited WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()


def list_for_user(user_id):
    return get_conn().execute(
        """SELECT v.*, c.name AS city_name, c.country_cca3, c.latitude, c.longitude
           FROM visited v JOIN cities c ON c.id = v.city_id
           WHERE v.user_id=?
           ORDER BY v.visited_date DESC""",
        (user_id,),
    ).fetchall()


def count_for_user(user_id):
    return get_conn().execute(
        "SELECT COUNT(*) AS n FROM visited WHERE user_id=?", (user_id,)
    ).fetchone()["n"]


def distinct_countries_for_user(user_id):
    return get_conn().execute(
        """SELECT DISTINCT c.country_cca3 AS cca3
           FROM visited v JOIN cities c ON c.id = v.city_id
           WHERE v.user_id=?""",
        (user_id,),
    ).fetchall()
