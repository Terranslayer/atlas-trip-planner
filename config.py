import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-not-for-prod")

    MONGODB_URI = os.environ.get("MONGODB_URI", "")
    MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", "atlas_capstone")

    REST_COUNTRIES_BASE = os.environ.get("REST_COUNTRIES_BASE", "https://restcountries.com/v3.1")
    FRANKFURTER_BASE = os.environ.get("FRANKFURTER_BASE", "https://api.frankfurter.app")
    OPEN_METEO_BASE = os.environ.get("OPEN_METEO_BASE", "https://climate-api.open-meteo.com/v1")
    US_ADVISORY_RSS = os.environ.get("US_ADVISORY_RSS", "https://travel.state.gov/_res/rss/TAsTWs.xml")

    CACHE_TTL_HOURS_COUNTRIES = int(os.environ.get("CACHE_TTL_HOURS_COUNTRIES", "168"))
    CACHE_TTL_HOURS_CLIMATE = int(os.environ.get("CACHE_TTL_HOURS_CLIMATE", "720"))
    CACHE_TTL_HOURS_CURRENCY = int(os.environ.get("CACHE_TTL_HOURS_CURRENCY", "1"))
    CACHE_TTL_HOURS_ADVISORY = int(os.environ.get("CACHE_TTL_HOURS_ADVISORY", "24"))

    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "instance" / "atlas.sqlite3"))

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLITE_PATH = ":memory:"
    SECRET_KEY = "testing"
