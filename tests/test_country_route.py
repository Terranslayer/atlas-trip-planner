from unittest.mock import patch


def _login(client):
    client.post("/register", data={"username": "alice", "password": "abc12345", "confirm": "abc12345"})


def test_country_page_renders_with_data(client, app):
    _login(client)
    country_doc = {
        "_id": "JPN", "name": {"common": "Japan"}, "cca2": "JP",
        "capital": ["Tokyo"], "region": "Asia", "subregion": "Eastern Asia",
        "population": 125000000, "area": 377930,
        "languages": {"jpn": "Japanese"},
        "currencies": {"JPY": {"name": "Japanese yen", "symbol": "¥"}},
        "flags": {"png": "x", "svg": "y", "alt": "z"},
        "timezones": ["UTC+09:00"], "borders": [], "latlng": [36.0, 138.0],
        "car": {"side": "left"}, "idd": {"root": "+8", "suffixes": ["1"]},
    }
    with patch("atlas.routes.countries.countries_service.get", return_value=country_doc), \
         patch("atlas.routes.countries.currency_service.rate",
               return_value={"_id":"USD_JPY","rate":153.4,"as_of":"2026-05-10","to":"JPY"}), \
         patch("atlas.routes.countries.advisory_service.for_cca3",
               return_value={"level":1,"level_text":"Exercise Normal Precautions",
                             "url":"x","published":"2026-03-14"}), \
         patch("atlas.routes.countries.wikivoyage_service.for_country", return_value=None):
        rv = client.get("/countries/JPN")
    assert rv.status_code == 200
    assert b"Japan" in rv.data
    assert b"JPY" in rv.data
    assert b"153.4" in rv.data
    assert b"Level 1" in rv.data
    assert b"Left" in rv.data


def test_country_page_renders_wikivoyage_notes_when_available(client, app):
    _login(client)
    country_doc = {
        "_id": "JPN", "name": {"common": "Japan"}, "cca2": "JP",
        "capital": ["Tokyo"], "region": "Asia", "subregion": "Eastern Asia",
        "population": 125000000, "area": 377930,
        "languages": {"jpn": "Japanese"}, "currencies": {},
        "flags": {}, "timezones": ["UTC+09:00"], "borders": [], "latlng": [36.0, 138.0],
        "car": {"side": "left"}, "idd": {},
    }
    notes = {
        "_id": "Japan",
        "sections": {
            "Stay safe": "<p>Japan is one of the safest countries in the world.</p>",
            "Money": "<p>Cash is still widely used outside major cities.</p>",
        },
        "source_url": "https://en.wikivoyage.org/wiki/Japan",
    }
    with patch("atlas.routes.countries.countries_service.get", return_value=country_doc), \
         patch("atlas.routes.countries.currency_service.rate", return_value=None), \
         patch("atlas.routes.countries.advisory_service.for_cca3", return_value=None), \
         patch("atlas.routes.countries.wikivoyage_service.for_country", return_value=notes):
        rv = client.get("/countries/JPN")
    assert rv.status_code == 200
    assert b"Travel Notes" in rv.data
    assert b"Stay safe" in rv.data
    assert b"safest countries" in rv.data
    assert b"wikivoyage.org/wiki/Japan" in rv.data


def test_country_page_returns_404_when_unknown(client):
    _login(client)
    with patch("atlas.routes.countries.countries_service.get", return_value=None):
        rv = client.get("/countries/ZZZ")
    assert rv.status_code == 404


def test_country_route_rejects_malformed_cca3(client):
    _login(client)
    rv = client.get("/countries/zz")
    assert rv.status_code == 404


def test_country_page_handles_missing_advisory(client, app):
    """Spec note from Task 10 implementer: only ~70% of cca3s have an advisory."""
    _login(client)
    country_doc = {
        "_id": "ABC", "name": {"common": "Atlantia"}, "cca2": "AT",
        "capital": ["Capital"], "region": "X", "subregion": "Y",
        "population": 1, "area": 1, "languages": {}, "currencies": {},
        "flags": {}, "timezones": [], "borders": [], "latlng": [0, 0],
        "car": {}, "idd": {},
    }
    with patch("atlas.routes.countries.countries_service.get", return_value=country_doc), \
         patch("atlas.routes.countries.currency_service.rate", return_value=None), \
         patch("atlas.routes.countries.advisory_service.for_cca3", return_value=None), \
         patch("atlas.routes.countries.wikivoyage_service.for_country", return_value=None):
        rv = client.get("/countries/ABC")
    assert rv.status_code == 200
    assert b"No advisory on file" in rv.data
    # When Wikivoyage returns nothing, the page does not render the Travel Notes heading.
    assert b"Travel Notes" not in rv.data
