from atlas.repos import cities as cities_repo


def _login(client):
    client.post("/register", data={"username": "alice", "password": "abc12345", "confirm": "abc12345"})


def _seed(app):
    with app.app_context():
        cities_repo.insert_many([
            {"id": 1, "name": "Tokyo", "ascii_name": "Tokyo", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.68, "longitude": 139.65,
             "population": 13929286, "timezone": "Asia/Tokyo"},
            {"id": 2, "name": "Kyoto", "ascii_name": "Kyoto", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.0, "longitude": 135.7,
             "population": 1474570, "timezone": "Asia/Tokyo"},
            {"id": 3, "name": "Paris", "ascii_name": "Paris", "country_code": "FR",
             "country_cca3": "FRA", "admin1": None, "latitude": 48.85, "longitude": 2.35,
             "population": 2148000, "timezone": "Europe/Paris"},
        ])


def test_search_returns_json_matches(client, app):
    _login(client)
    _seed(app)
    rv = client.get("/cities/search?q=ky")
    assert rv.status_code == 200
    data = rv.get_json()
    names = [c["name"] for c in data["results"]]
    assert "Kyoto" in names
    assert "Paris" not in names


def test_search_with_empty_query_returns_empty(client):
    _login(client)
    rv = client.get("/cities/search?q=")
    assert rv.status_code == 200
    assert rv.get_json()["results"] == []


def test_search_requires_login(client):
    rv = client.get("/cities/search?q=tok")
    assert rv.status_code == 302  # redirect to login


def test_search_results_include_required_fields(client, app):
    _login(client)
    _seed(app)
    rv = client.get("/cities/search?q=tok")
    item = rv.get_json()["results"][0]
    for field in ("id", "name", "country_cca3", "country_code", "admin1", "lat", "lon", "population"):
        assert field in item
