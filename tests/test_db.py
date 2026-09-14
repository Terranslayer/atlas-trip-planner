from atlas.repos.sqlite import get_conn


def test_get_conn_returns_usable_connection(app):
    with app.app_context():
        conn = get_conn()
        cur = conn.execute("SELECT 1 AS one")
        row = cur.fetchone()
        assert row["one"] == 1


def test_users_table_exists(app):
    with app.app_context():
        conn = get_conn()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchall()
        assert len(rows) == 1
