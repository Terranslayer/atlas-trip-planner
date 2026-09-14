from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from atlas.services import countries as countries_service
from atlas.repos import mongo as mongo_repo


SAMPLE = {
    "name": {"common": "Japan", "official": "Japan"},
    "cca2": "JP", "cca3": "JPN",
    "capital": ["Tokyo"],
    "region": "Asia", "subregion": "Eastern Asia",
    "population": 125836021, "area": 377930,
    "languages": {"jpn": "Japanese"},
    "currencies": {"JPY": {"name": "Japanese yen", "symbol": "¥"}},
    "flags": {"png": "x", "svg": "y", "alt": "z"},
    "timezones": ["UTC+09:00"],
    "borders": [], "latlng": [36.0, 138.0],
    "car": {"side": "left"},
    "idd": {"root": "+8", "suffixes": ["1"]},
}


def test_get_country_returns_cached_when_fresh(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["countries_cache"].delete_many({"_id": "TJPN_TEST"})
        keys = ("name", "cca2", "capital", "region", "subregion", "population",
                "languages", "currencies", "flags", "timezones", "borders", "latlng", "car", "idd")
        db["countries_cache"].insert_one({
            **{k: SAMPLE[k] for k in keys},
            "_id": "TJPN_TEST",
            "cached_at": datetime.now(timezone.utc),
        })
        with patch("atlas.services.countries.get_json") as m:
            doc = countries_service.get("TJPN_TEST")
            m.assert_not_called()
            assert doc["_id"] == "TJPN_TEST"
            assert doc["name"]["common"] == "Japan"
        db["countries_cache"].delete_many({"_id": "TJPN_TEST"})


def test_get_country_fetches_when_stale(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["countries_cache"].delete_many({"_id": "TXX_TEST"})
        stale = datetime.now(timezone.utc) - timedelta(days=10)
        db["countries_cache"].insert_one({"_id": "TXX_TEST", "name": {"common": "Old"}, "cached_at": stale})

        with patch("atlas.services.countries.get_json",
                   return_value=[{**SAMPLE, "cca3": "TXX_TEST"}]) as m:
            doc = countries_service.get("TXX_TEST")
            m.assert_called_once()
            assert doc["name"]["common"] == "Japan"
        db["countries_cache"].delete_many({"_id": "TXX_TEST"})


def test_get_country_handles_upstream_failure_with_stale(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["countries_cache"].delete_many({"_id": "TYY_TEST"})
        stale = datetime.now(timezone.utc) - timedelta(days=30)
        db["countries_cache"].insert_one({"_id": "TYY_TEST", "name": {"common": "Stale"}, "cached_at": stale})

        from atlas.services.http import HTTPError
        with patch("atlas.services.countries.get_json", side_effect=HTTPError("boom")):
            doc = countries_service.get("TYY_TEST")
            assert doc["name"]["common"] == "Stale"
            assert doc.get("stale") is True
        db["countries_cache"].delete_many({"_id": "TYY_TEST"})
