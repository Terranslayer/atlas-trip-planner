from atlas.repos import visited as v_repo
from atlas.repos import users as users_repo
from atlas.repos import cities as cities_repo


def _seed(app):
    with app.app_context():
        uid = users_repo.create("u", "abc12345")
        cities_repo.insert_many([{
            "id": 1, "name": "Reykjavik", "ascii_name": "Reykjavik",
            "country_code": "IS", "country_cca3": "ISL", "admin1": None,
            "latitude": 64.14, "longitude": -21.94,
            "population": 122853, "timezone": "Atlantic/Reykjavik",
        }])
        return uid


def test_log_multiple_visits_to_same_city(app):
    uid = _seed(app)
    with app.app_context():
        v_repo.add(uid, 1, "2024-07-15", journal="trip 1")
        v_repo.add(uid, 1, "2027-05-02", journal="trip 2")
        rows = v_repo.list_for_user(uid)
        assert len(rows) == 2


def test_visited_isolation_between_users(app):
    with app.app_context():
        u1 = users_repo.create("a", "abc12345")
        u2 = users_repo.create("b", "abc12345")
        cities_repo.insert_many([{
            "id": 2, "name": "Paris", "ascii_name": "Paris", "country_code": "FR",
            "country_cca3": "FRA", "admin1": None, "latitude": 48.85, "longitude": 2.35,
            "population": 2148000, "timezone": "Europe/Paris",
        }])
        v_repo.add(u1, 2, "2025-08-01", journal="x")
        assert len(v_repo.list_for_user(u1)) == 1
        assert v_repo.list_for_user(u2) == []
