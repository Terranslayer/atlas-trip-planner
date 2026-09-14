"""Exercise real trip routes with CSRF enabled and two distinct users."""
import re

import pytest

from atlas.repos import cities, trips, users


@pytest.fixture
def trip_accounts(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    with app.app_context():
        alice = users.create("alice", "abc12345")
        bob = users.create("bob", "abc12345")
        cities.insert_many([
            {"id": city_id, "name": name, "ascii_name": name,
             "country_code": "JP", "country_cca3": "JPN", "admin1": None,
             "latitude": 35.0, "longitude": 139.0, "population": 100000,
             "timezone": "Asia/Tokyo"}
            for city_id, name in [(1, "Tokyo"), (2, "Kyoto")]
        ])
        own_trip = trips.create(alice, "Alice trip")
        own_stops = [trips.add_stop(own_trip, city_id, None, None) for city_id in (1, 2)]
        foreign_trip = trips.create(bob, "Bob private trip", notes="Private notes")
        foreign_stop = trips.add_stop(foreign_trip, 1, None, None, notes="Private stop")
    with client.session_transaction() as session:
        session["user_id"] = alice
    return alice, bob, own_trip, own_stops, foreign_trip, foreign_stop


def _csrf_token(client):
    response = client.get("/trips")
    assert response.status_code == 200
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match is not None
    return match.group(1).decode()


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_create_trip_rejects_missing_or_invalid_csrf(app, client, trip_accounts, token):
    alice = trip_accounts[0]
    data = {"name": "Unwanted trip"}
    if token is not None:
        data["csrf_token"] = token
    response = client.post("/trips/new", data=data)
    assert response.status_code == 400
    with app.app_context():
        assert [trip["name"] for trip in trips.list_for_user(alice)] == ["Alice trip"]


def test_create_trip_accepts_form_csrf_token(app, client, trip_accounts):
    alice = trip_accounts[0]
    response = client.post("/trips/new", data={"name": "New trip", "csrf_token": _csrf_token(client)})
    assert response.status_code == 302
    with app.app_context():
        assert sorted(trip["name"] for trip in trips.list_for_user(alice)) == ["Alice trip", "New trip"]


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_reorder_rejects_missing_or_invalid_csrf(app, client, trip_accounts, token):
    _, _, own_trip, own_stops, _, _ = trip_accounts
    headers = {} if token is None else {"X-CSRFToken": token}
    response = client.post(f"/trips/{own_trip}/stops/reorder", json={"order": own_stops[::-1]}, headers=headers)
    assert response.status_code == 400
    with app.app_context():
        assert [stop["city_id"] for stop in trips.list_stops(own_trip)] == [1, 2]


def test_reorder_accepts_csrf_header(app, client, trip_accounts):
    _, _, own_trip, own_stops, _, _ = trip_accounts
    response = client.post(
        f"/trips/{own_trip}/stops/reorder", json={"order": own_stops[::-1]},
        headers={"X-CSRFToken": _csrf_token(client)},
    )
    assert response.status_code == 200
    assert response.json == {"ok": True}
    with app.app_context():
        assert [stop["city_id"] for stop in trips.list_stops(own_trip)] == [2, 1]


@pytest.mark.parametrize("suffix,method,expected_status", [
    ("", "GET", 404),
    ("/export.md", "GET", 404),
    ("/edit", "POST", 404),
    ("/delete", "POST", 302),
    ("/stops/add", "POST", 404),
    ("/stops/reorder", "POST", 404),
])
def test_other_users_trip_cannot_be_read_or_changed(
    app, client, trip_accounts, suffix, method, expected_status,
):
    _, bob, _, _, foreign_trip, foreign_stop = trip_accounts
    with app.app_context():
        before_trip = dict(trips.get(foreign_trip, bob))
        before_stops = [dict(stop) for stop in trips.list_stops(foreign_trip)]
    kwargs = {"headers": {"X-CSRFToken": _csrf_token(client)}}
    if suffix == "/stops/reorder":
        kwargs["json"] = {"order": [foreign_stop]}
    elif method == "POST":
        kwargs["data"] = {"name": "Tampered", "notes": "Tampered", "city_id": "2"}
    response = client.open(f"/trips/{foreign_trip}{suffix}", method=method, **kwargs)
    assert response.status_code == expected_status
    assert b"Private notes" not in response.data
    with app.app_context():
        assert dict(trips.get(foreign_trip, bob)) == before_trip
        assert [dict(stop) for stop in trips.list_stops(foreign_trip)] == before_stops


@pytest.mark.parametrize("action", ["edit", "delete"])
def test_foreign_stop_id_cannot_be_changed_via_owned_trip(app, client, trip_accounts, action):
    _, _, own_trip, _, foreign_trip, foreign_stop = trip_accounts
    with app.app_context():
        before = [dict(stop) for stop in trips.list_stops(foreign_trip)]
    response = client.post(
        f"/trips/{own_trip}/stops/{foreign_stop}/{action}",
        data={"notes": "Tampered", "csrf_token": _csrf_token(client)},
    )
    assert response.status_code == 302
    with app.app_context():
        assert [dict(stop) for stop in trips.list_stops(foreign_trip)] == before
