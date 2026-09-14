import re
from atlas.repos import cities as cities_repo


def _login(client):
    client.post("/register", data={"username": "alice", "password": "abc12345", "confirm": "abc12345"})


def _seed(app):
    with app.app_context():
        cities_repo.insert_many([{
            "id": 1850147, "name": "Tokyo", "ascii_name": "Tokyo",
            "country_code": "JP", "country_cca3": "JPN", "admin1": None,
            "latitude": 35.68, "longitude": 139.65, "population": 13929286,
            "timezone": "Asia/Tokyo",
        }])


def test_add_then_list_shows_entry(client, app):
    _login(client); _seed(app)
    rv = client.post("/wishlist/add", data={"city_id": "1850147", "note": "spring", "priority": "2"})
    assert rv.status_code == 302
    rv = client.get("/wishlist")
    assert rv.status_code == 200
    assert b"Tokyo" in rv.data
    assert b"spring" in rv.data


def test_delete_removes_entry(client, app):
    _login(client); _seed(app)
    client.post("/wishlist/add", data={"city_id": "1850147", "note": "x", "priority": "1"})
    rv = client.get("/wishlist")
    m = re.search(rb'data-wishlist-id="(\d+)"', rv.data)
    assert m
    wid = m.group(1).decode()
    rv = client.post(f"/wishlist/{wid}/delete")
    assert rv.status_code == 302
    rv = client.get("/wishlist")
    assert b"Tokyo" not in rv.data
