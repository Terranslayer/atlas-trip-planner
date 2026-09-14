from .sqlite import get_conn


COLUMNS = ("id", "name", "ascii_name", "country_code", "country_cca3",
           "admin1", "latitude", "longitude", "population", "timezone")


def insert_many(rows):
    conn = get_conn()
    conn.executemany(
        f"INSERT OR REPLACE INTO cities ({','.join(COLUMNS)}) VALUES ({','.join(['?']*len(COLUMNS))})",
        [tuple(r[c] for c in COLUMNS) for r in rows],
    )
    conn.commit()


def get(city_id: int):
    return get_conn().execute(
        "SELECT * FROM cities WHERE id = ?", (city_id,)
    ).fetchone()


# SQLite sorts NULLs first under DESC by default, so we add an explicit
# `population IS NULL` clause to push unknown-population entries to the end.
def search(query: str, limit: int = 20):
    q = (query or "").strip()
    if not q:
        return []
    like = q + "%"
    sub_like = "% " + q + "%"
    rows = get_conn().execute(
        """
        SELECT * FROM cities
        WHERE ascii_name LIKE ? COLLATE NOCASE
           OR name LIKE ? COLLATE NOCASE
           OR ascii_name LIKE ? COLLATE NOCASE
        ORDER BY population IS NULL, population DESC
        LIMIT ?
        """,
        (like, like, sub_like, limit),
    ).fetchall()
    return rows


def count():
    return get_conn().execute("SELECT COUNT(*) AS n FROM cities").fetchone()["n"]
