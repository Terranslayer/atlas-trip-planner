import pytest

from atlas.repos import users as users_repo


def test_create_and_find_user(app):
    with app.app_context():
        uid = users_repo.create("alice", "secret-pw-1")
        assert isinstance(uid, int)
        user = users_repo.find_by_username("alice")
        assert user["id"] == uid
        assert user["username"] == "alice"


def test_password_is_hashed_not_stored_plain(app):
    with app.app_context():
        users_repo.create("bob", "my-password")
        user = users_repo.find_by_username("bob")
        assert user["password_hash"] != "my-password"
        assert user["password_hash"].startswith("pbkdf2:")


def test_check_password_returns_user_on_match(app):
    with app.app_context():
        users_repo.create("carol", "correct-horse-battery-staple")
        user = users_repo.authenticate("carol", "correct-horse-battery-staple")
        assert user is not None
        assert user["username"] == "carol"


def test_check_password_returns_none_on_mismatch(app):
    with app.app_context():
        users_repo.create("dave", "right")
        assert users_repo.authenticate("dave", "wrong") is None


def test_username_uniqueness(app):
    with app.app_context():
        users_repo.create("eve", "pw")
        with pytest.raises(Exception):
            users_repo.create("eve", "pw")
