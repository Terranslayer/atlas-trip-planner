from .sqlite import get_conn


def create(user_id, name, start_date=None, end_date=None, notes=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO trips (user_id, name, start_date, end_date, notes) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, start_date, end_date, notes),
    )
    conn.commit()
    return cur.lastrowid


def update(trip_id, user_id, name, start_date, end_date, notes):
    conn = get_conn()
    conn.execute(
        "UPDATE trips SET name=?, start_date=?, end_date=?, notes=? WHERE id=? AND user_id=?",
        (name, start_date, end_date, notes, trip_id, user_id),
    )
    conn.commit()


def delete(trip_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM trips WHERE id=? AND user_id=?", (trip_id, user_id))
    conn.commit()


def get(trip_id, user_id):
    return get_conn().execute(
        "SELECT * FROM trips WHERE id=? AND user_id=?", (trip_id, user_id)
    ).fetchone()


def list_for_user(user_id):
    return get_conn().execute(
        "SELECT * FROM trips WHERE user_id=? ORDER BY COALESCE(start_date, created_at) DESC",
        (user_id,),
    ).fetchall()


def add_stop(trip_id, city_id, arrival, departure, notes=None):
    conn = get_conn()
    nxt = conn.execute(
        "SELECT COALESCE(MAX(sequence_order) + 1, 0) AS n FROM trip_stops WHERE trip_id=?",
        (trip_id,),
    ).fetchone()["n"]
    cur = conn.execute(
        """INSERT INTO trip_stops (trip_id, city_id, arrival_date, departure_date, sequence_order, stop_notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (trip_id, city_id, arrival, departure, nxt, notes),
    )
    conn.commit()
    return cur.lastrowid


def update_stop(stop_id, trip_id, arrival, departure, notes):
    conn = get_conn()
    conn.execute(
        "UPDATE trip_stops SET arrival_date=?, departure_date=?, stop_notes=? WHERE id=? AND trip_id=?",
        (arrival, departure, notes, stop_id, trip_id),
    )
    conn.commit()


def delete_stop(stop_id, trip_id):
    conn = get_conn()
    conn.execute("DELETE FROM trip_stops WHERE id=? AND trip_id=?", (stop_id, trip_id))
    conn.commit()


def list_stops(trip_id):
    return get_conn().execute(
        """SELECT s.*, c.name AS city_name, c.country_cca3, c.country_code,
                  c.latitude, c.longitude, c.timezone
           FROM trip_stops s JOIN cities c ON c.id = s.city_id
           WHERE s.trip_id=?
           ORDER BY s.sequence_order""",
        (trip_id,),
    ).fetchall()


def reorder_stops(trip_id, stop_id_order):
    """Renumber stops in the trip according to the given list of stop_ids.

    Two-phase to avoid colliding with the UNIQUE(trip_id, sequence_order) constraint:
    first push existing orders out of the conflict range, then write the new sequence.
    """
    conn = get_conn()
    conn.execute(
        "UPDATE trip_stops SET sequence_order = sequence_order + 1000000 WHERE trip_id=?",
        (trip_id,),
    )
    for idx, sid in enumerate(stop_id_order):
        conn.execute(
            "UPDATE trip_stops SET sequence_order=? WHERE id=? AND trip_id=?",
            (idx, sid, trip_id),
        )
    conn.commit()


def count_for_user(user_id):
    return get_conn().execute(
        "SELECT COUNT(*) AS n FROM trips WHERE user_id=?", (user_id,)
    ).fetchone()["n"]


def upcoming(user_id, n=5):
    return get_conn().execute(
        """SELECT * FROM trips
           WHERE user_id=? AND start_date IS NOT NULL AND start_date >= date('now')
           ORDER BY start_date ASC LIMIT ?""",
        (user_id, n),
    ).fetchall()
