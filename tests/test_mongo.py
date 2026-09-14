import pytest

from atlas.repos.mongo import get_db, ping


pytestmark = [pytest.mark.live_mongo, pytest.mark.enable_socket]


def test_ping_returns_true(live_mongo_app):
    with live_mongo_app.app_context():
        assert ping() is True


def test_get_db_returns_named_database(live_mongo_app):
    with live_mongo_app.app_context():
        db = get_db()
        assert db.name == "atlas_test"
