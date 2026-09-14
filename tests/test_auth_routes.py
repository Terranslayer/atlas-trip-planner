def test_register_get_renders_form(client):
    rv = client.get("/register")
    assert rv.status_code == 200
    assert b"Register" in rv.data


def test_register_creates_user_and_logs_in(client):
    rv = client.post(
        "/register",
        data={"username": "alice", "password": "abc12345", "confirm": "abc12345"},
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("/dashboard")

    with client.session_transaction() as sess:
        assert "user_id" in sess


def test_register_rejects_mismatched_passwords(client):
    rv = client.post(
        "/register",
        data={"username": "alice", "password": "abc12345", "confirm": "different"},
    )
    assert rv.status_code == 200
    assert b"Passwords must match" in rv.data


def test_login_rejects_bad_credentials(client):
    client.post("/register", data={"username": "u", "password": "abc12345", "confirm": "abc12345"})
    client.post("/logout")
    rv = client.post("/login", data={"username": "u", "password": "wrong"})
    assert rv.status_code == 200
    assert b"Invalid credentials" in rv.data


def test_login_ignores_off_site_next_redirect(client):
    client.post("/register", data={"username": "nina", "password": "abc12345", "confirm": "abc12345"})
    client.post("/logout")
    rv = client.post(
        "/login?next=https://evil.example/phish",
        data={"username": "nina", "password": "abc12345"},
        follow_redirects=False,
    )
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("/dashboard")


def test_logout_rejects_get(client):
    client.post("/register", data={"username": "xena", "password": "abc12345", "confirm": "abc12345"})
    rv = client.get("/logout")
    assert rv.status_code == 405
    with client.session_transaction() as sess:
        assert "user_id" in sess  # still logged in — GET cannot log out


def test_dashboard_redirects_when_unauthenticated(client):
    rv = client.get("/dashboard")
    assert rv.status_code == 302
    assert "/login" in rv.headers["Location"]


def test_logout_clears_session(client):
    client.post("/register", data={"username": "u2", "password": "abc12345", "confirm": "abc12345"})
    client.post("/logout")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
