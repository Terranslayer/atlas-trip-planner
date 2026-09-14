import pytest

from atlas.repos import wishlist as wl_repo
from atlas.repos import users as users_repo
from atlas.repos import cities as cities_repo


def _seed_one_city_and_user(app):
    with app.app_context():
        uid = users_repo.create("alice", "abc12345")
        cities_repo.insert_many([{
            "id": 1850147, "name": "Tokyo", "ascii_name": "Tokyo",
            "country_code": "JP", "country_cca3": "JPN", "admin1": None,
            "latitude": 35.68, "longitude": 139.65,
            "population": 13929286, "timezone": "Asia/Tokyo",
        }])
        return uid


def test_add_and_list(app):
    uid = _seed_one_city_and_user(app)
    with app.app_context():
        new_id = wl_repo.add(uid, 1850147, note="spring", priority=2)
        assert isinstance(new_id, int)
        items = wl_repo.list_for_user(uid)
        assert len(items) == 1
        assert items[0]["note"] == "spring"
        assert items[0]["priority"] == 2
        assert items[0]["city_name"] == "Tokyo"


def test_duplicate_add_raises(app):
    uid = _seed_one_city_and_user(app)
    with app.app_context():
        wl_repo.add(uid, 1850147, note="x", priority=1)
        with pytest.raises(Exception):
            wl_repo.add(uid, 1850147, note="y", priority=2)


def test_update(app):
    uid = _seed_one_city_and_user(app)
    with app.app_context():
        rid = wl_repo.add(uid, 1850147, note="x", priority=0)
        wl_repo.update(rid, uid, note="updated", priority=2)
        rec = wl_repo.get(rid, uid)
        assert rec["note"] == "updated"
        assert rec["priority"] == 2


def test_delete(app):
    uid = _seed_one_city_and_user(app)
    with app.app_context():
        rid = wl_repo.add(uid, 1850147, note="x", priority=0)
        wl_repo.delete(rid, uid)
        assert wl_repo.list_for_user(uid) == []


def test_isolation_between_users(app):
    with app.app_context():
        u1 = users_repo.create("alice", "abc12345")
        u2 = users_repo.create("bob",   "abc12345")
        cities_repo.insert_many([{
            "id": 1, "name": "Kyoto", "ascii_name": "Kyoto", "country_code": "JP",
            "country_cca3": "JPN", "admin1": None, "latitude": 35.0, "longitude": 135.7,
            "population": 1474570, "timezone": "Asia/Tokyo",
        }])
        wl_repo.add(u1, 1, note="a", priority=1)
        assert wl_repo.list_for_user(u1)
        assert wl_repo.list_for_user(u2) == []
