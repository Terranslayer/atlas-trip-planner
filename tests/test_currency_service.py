from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from atlas.services import currency as currency_service
from atlas.repos import mongo as mongo_repo


def test_rate_returns_cached_when_fresh(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["currency_cache"].delete_many({"_id": "USD_JPY"})
        db["currency_cache"].insert_one({
            "_id": "USD_JPY", "from": "USD", "to": "JPY",
            "rate": 150.0, "as_of": "2026-05-10",
            "cached_at": datetime.now(timezone.utc),
        })
        with patch("atlas.services.currency.get_json") as m:
            r = currency_service.rate("JPY")
            m.assert_not_called()
            assert r["rate"] == 150.0
        db["currency_cache"].delete_many({"_id": "USD_JPY"})


def test_rate_fetches_when_stale(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["currency_cache"].delete_many({"_id": "USD_EUR"})
        stale = datetime.now(timezone.utc) - timedelta(hours=5)
        db["currency_cache"].insert_one({
            "_id": "USD_EUR", "from": "USD", "to": "EUR",
            "rate": 0.9, "as_of": "2026-05-05",
            "cached_at": stale,
        })
        with patch("atlas.services.currency.get_json",
                   return_value={"amount": 1.0, "base": "USD", "date": "2026-05-10",
                                 "rates": {"EUR": 0.93}}) as m:
            r = currency_service.rate("EUR")
            m.assert_called_once()
            assert r["rate"] == 0.93
        db["currency_cache"].delete_many({"_id": "USD_EUR"})
