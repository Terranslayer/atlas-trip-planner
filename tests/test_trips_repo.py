from atlas.repos import trips as trips_repo
from atlas.repos import users as users_repo
from atlas.repos import cities as cities_repo


def _seed(app):
    with app.app_context():
        uid = users_repo.create("u", "abc12345")
        cities_repo.insert_many([
            {"id": 1, "name": "Tokyo", "ascii_name": "Tokyo", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.68, "longitude": 139.65,
             "population": 13929286, "timezone": "Asia/Tokyo"},
            {"id": 2, "name": "Kyoto", "ascii_name": "Kyoto", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.0, "longitude": 135.7,
             "population": 1474570, "timezone": "Asia/Tokyo"},
            {"id": 3, "name": "Osaka", "ascii_name": "Osaka", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 34.69, "longitude": 135.5,
             "population": 2691000, "timezone": "Asia/Tokyo"},
        ])
        return uid


def test_create_trip_and_list(app):
    uid = _seed(app)
    with app.app_context():
        tid = trips_repo.create(uid, "Japan 2027", "2027-04-10", "2027-04-20", notes=None)
        trips = trips_repo.list_for_user(uid)
        assert len(trips) == 1
        assert trips[0]["name"] == "Japan 2027"


def test_add_stops_with_sequence_order(app):
    uid = _seed(app)
    with app.app_context():
        tid = trips_repo.create(uid, "Japan", "2027-04-10", "2027-04-20")
        trips_repo.add_stop(tid, city_id=1, arrival="2027-04-10", departure="2027-04-14")
        trips_repo.add_stop(tid, city_id=2, arrival="2027-04-14", departure="2027-04-17")
        trips_repo.add_stop(tid, city_id=3, arrival="2027-04-17", departure="2027-04-20")
        stops = trips_repo.list_stops(tid)
        assert [s["sequence_order"] for s in stops] == [0, 1, 2]
        assert [s["city_id"] for s in stops] == [1, 2, 3]


def test_reorder_stops(app):
    uid = _seed(app)
    with app.app_context():
        tid = trips_repo.create(uid, "Japan", None, None)
        s1 = trips_repo.add_stop(tid, city_id=1, arrival=None, departure=None)
        s2 = trips_repo.add_stop(tid, city_id=2, arrival=None, departure=None)
        s3 = trips_repo.add_stop(tid, city_id=3, arrival=None, departure=None)
        trips_repo.reorder_stops(tid, [s3, s1, s2])
        stops = trips_repo.list_stops(tid)
        assert [s["city_id"] for s in stops] == [3, 1, 2]


def test_trip_isolation(app):
    with app.app_context():
        u1 = users_repo.create("a", "abc12345")
        u2 = users_repo.create("b", "abc12345")
        t1 = trips_repo.create(u1, "Alice trip", None, None)
        assert trips_repo.get(t1, u1) is not None
        assert trips_repo.get(t1, u2) is None
