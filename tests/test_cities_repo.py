from atlas.repos import cities as cities_repo


def test_insert_and_get_city(app):
    with app.app_context():
        cities_repo.insert_many([
            {
                "id": 1850147, "name": "Tokyo", "ascii_name": "Tokyo",
                "country_code": "JP", "country_cca3": "JPN", "admin1": "Tokyo",
                "latitude": 35.6762, "longitude": 139.6503,
                "population": 13929286, "timezone": "Asia/Tokyo",
            }
        ])
        c = cities_repo.get(1850147)
        assert c["name"] == "Tokyo"
        assert c["country_cca3"] == "JPN"


def test_search_returns_prefix_matches(app):
    with app.app_context():
        cities_repo.insert_many([
            {"id": 1, "name": "Kyoto", "ascii_name": "Kyoto", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.0, "longitude": 135.0,
             "population": 1500000, "timezone": "Asia/Tokyo"},
            {"id": 2, "name": "Kyiv", "ascii_name": "Kyiv", "country_code": "UA",
             "country_cca3": "UKR", "admin1": None, "latitude": 50.0, "longitude": 30.0,
             "population": 3000000, "timezone": "Europe/Kyiv"},
            {"id": 3, "name": "Paris", "ascii_name": "Paris", "country_code": "FR",
             "country_cca3": "FRA", "admin1": None, "latitude": 48.85, "longitude": 2.35,
             "population": 2148000, "timezone": "Europe/Paris"},
        ])
        results = cities_repo.search("ky", limit=10)
        names = [r["name"] for r in results]
        assert "Kyoto" in names and "Kyiv" in names and "Paris" not in names


def test_search_orders_by_population_desc(app):
    with app.app_context():
        cities_repo.insert_many([
            {"id": 4, "name": "Springfield", "ascii_name": "Springfield", "country_code": "US",
             "country_cca3": "USA", "admin1": "IL", "latitude": 39.78, "longitude": -89.65,
             "population": 116000, "timezone": "America/Chicago"},
            {"id": 5, "name": "Springfield", "ascii_name": "Springfield", "country_code": "US",
             "country_cca3": "USA", "admin1": "MO", "latitude": 37.21, "longitude": -93.29,
             "population": 169000, "timezone": "America/Chicago"},
        ])
        results = cities_repo.search("spring", limit=2)
        assert results[0]["population"] >= results[1]["population"]
