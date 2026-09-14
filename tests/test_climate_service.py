from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from atlas.services import climate as climate_service
from atlas.repos import mongo as mongo_repo


def test_for_city_returns_cached(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["climate_cache"].delete_many({"_id": 9999999})
        db["climate_cache"].insert_one({
            "_id": 9999999, "city_name": "Test", "lat": 0, "lon": 0,
            "monthly": [{"month": m, "tavg_c": 18.0, "precip_mm": 80.0} for m in range(1, 13)],
            "cached_at": datetime.now(timezone.utc),
        })
        with patch("atlas.services.climate.get_json") as m:
            doc = climate_service.for_city(9999999, 0, 0)
            m.assert_not_called()
            assert len(doc["monthly"]) == 12
        db["climate_cache"].delete_many({"_id": 9999999})


def test_for_city_fetches_when_missing(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["climate_cache"].delete_many({"_id": 1234567})
        fake = {
            "monthly": {
                "time": ["1991-01-01","1991-02-01","1991-03-01","1991-04-01","1991-05-01","1991-06-01",
                         "1991-07-01","1991-08-01","1991-09-01","1991-10-01","1991-11-01","1991-12-01"],
                "temperature_2m_mean": [5,6,9,14,19,22,26,27,23,18,12,7],
                "precipitation_sum": [52,56,117,124,137,167,153,168,209,197,92,51],
            }
        }
        with patch("atlas.services.climate.get_json", return_value=fake):
            doc = climate_service.for_city(1234567, 35.0, 139.0)
        assert len(doc["monthly"]) == 12
        assert doc["monthly"][3]["tavg_c"] == 14
        assert doc["monthly"][3]["precip_mm"] == 124
        db["climate_cache"].delete_many({"_id": 1234567})
