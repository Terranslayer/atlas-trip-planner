import sqlite3
from pathlib import Path

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    is_admin       INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cities (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    ascii_name    TEXT    NOT NULL,
    country_code  TEXT    NOT NULL,
    country_cca3  TEXT    NOT NULL,
    admin1        TEXT,
    latitude      REAL    NOT NULL,
    longitude     REAL    NOT NULL,
    population    INTEGER,
    timezone      TEXT
);
CREATE INDEX IF NOT EXISTS idx_cities_name    ON cities(ascii_name);
CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_cca3);

CREATE TABLE IF NOT EXISTS wishlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    city_id     INTEGER NOT NULL REFERENCES cities(id),
    note        TEXT,
    priority    INTEGER NOT NULL DEFAULT 1 CHECK(priority IN (0,1,2)),
    added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, city_id)
);
CREATE INDEX IF NOT EXISTS idx_wishlist_user ON wishlist(user_id);

CREATE TABLE IF NOT EXISTS visited (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    city_id       INTEGER NOT NULL REFERENCES cities(id),
    visited_date  DATE    NOT NULL,
    journal       TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_visited_user_city ON visited(user_id, city_id);

CREATE TABLE IF NOT EXISTS trips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    start_date  DATE,
    end_date    DATE,
    notes       TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id);

CREATE TABLE IF NOT EXISTS trip_stops (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    city_id         INTEGER NOT NULL REFERENCES cities(id),
    arrival_date    DATE,
    departure_date  DATE,
    sequence_order  INTEGER NOT NULL,
    stop_notes      TEXT,
    UNIQUE(trip_id, sequence_order)
);
CREATE INDEX IF NOT EXISTS idx_stops_trip ON trip_stops(trip_id);
"""


def get_conn():
    if "sqlite_conn" not in g:
        path = current_app.config["SQLITE_PATH"]
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.sqlite_conn = conn
    return g.sqlite_conn


def close_conn(_exc=None):
    conn = g.pop("sqlite_conn", None)
    if conn is not None:
        conn.close()


def init_schema():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
