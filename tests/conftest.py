import os
import tempfile
import mongomock
import pytest

from atlas import create_app
from config import TestConfig
from atlas.repos.sqlite import init_schema


def pytest_addoption(parser):
    parser.addoption(
        "--run-live-mongo", action="store_true", default=False,
        help="Run live MongoDB checks using ATLAS_TEST_MONGODB_URI.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live-mongo"):
        if not os.environ.get("ATLAS_TEST_MONGODB_URI"):
            raise pytest.UsageError(
                "--run-live-mongo requires ATLAS_TEST_MONGODB_URI"
            )
        return
    skip_live = pytest.mark.skip(reason="Use --run-live-mongo to run live MongoDB checks")
    for item in items:
        if "live_mongo" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(db_fd)

    class _Cfg(TestConfig):
        SQLITE_PATH = db_path
        MONGODB_URI = ""
        MONGODB_DB_NAME = "atlas_test"

    app = create_app(_Cfg)
    # Use the same repository/service code with a fresh in-memory document store.
    # Never inherit a developer's MongoDB connection or share cache state.
    mongo_client = mongomock.MongoClient()
    app.extensions["mongo_client"] = mongo_client
    try:
        with app.app_context():
            init_schema()
        yield app
    finally:
        mongo_client.close()
        os.unlink(db_path)


@pytest.fixture
def live_mongo_app():
    class _Cfg(TestConfig):
        MONGODB_URI = os.environ["ATLAS_TEST_MONGODB_URI"]
        MONGODB_DB_NAME = "atlas_test"

    app = create_app(_Cfg)
    try:
        yield app
    finally:
        mongo_client = app.extensions.pop("mongo_client", None)
        if mongo_client is not None:
            mongo_client.close()


@pytest.fixture
def client(app):
    return app.test_client()
