from unittest.mock import patch

from atlas.services import trip_brief
from atlas.repos import trips as trips_repo
from atlas.repos import users as users_repo
from atlas.repos import cities as cities_repo


def _seed_japan_trip(app):
    with app.app_context():
        uid = users_repo.create("u", "abc12345")
        cities_repo.insert_many([
            {"id": 1, "name": "Tokyo", "ascii_name": "Tokyo", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.68, "longitude": 139.65,
             "population": 13929286, "timezone": "Asia/Tokyo"},
            {"id": 2, "name": "Kyoto", "ascii_name": "Kyoto", "country_code": "JP",
             "country_cca3": "JPN", "admin1": None, "latitude": 35.0, "longitude": 135.7,
             "population": 1474570, "timezone": "Asia/Tokyo"},
        ])
        tid = trips_repo.create(uid, "Japan 2027", "2027-04-10", "2027-04-17")
        trips_repo.add_stop(tid, 1, "2027-04-10", "2027-04-14")
        trips_repo.add_stop(tid, 2, "2027-04-14", "2027-04-17")
        return uid, tid


def test_brief_aggregates_all_sections(app):
    uid, tid = _seed_japan_trip(app)
    with app.app_context():
        country_doc = {
            "_id": "JPN", "name": {"common": "Japan"}, "cca2": "JP",
            "capital": ["Tokyo"], "languages": {"jpn": "Japanese"},
            "currencies": {"JPY": {"name": "Japanese yen", "symbol": "¥"}},
            "timezones": ["UTC+09:00"], "borders": [],
            "car": {"side": "left"}, "idd": {"root": "+8", "suffixes": ["1"]},
        }
        climate_tokyo = {"_id": 1, "monthly": [{"month": m, "tavg_c": 14.0, "precip_mm": 130.0} for m in range(1, 13)]}
        climate_kyoto = {"_id": 2, "monthly": [{"month": m, "tavg_c": 14.0, "precip_mm": 140.0} for m in range(1, 13)]}
        rate_doc = {"_id": "USD_JPY", "from": "USD", "to": "JPY", "rate": 153.42, "as_of": "2026-05-10"}
        adv_doc = {"_id": "JPN", "level": 1, "level_text": "Exercise Normal Precautions",
                   "url": "x", "published": "2026-03-14"}

        def fake_climate(city_id, lat, lon, name=None):
            return climate_tokyo if city_id == 1 else climate_kyoto

        with patch("atlas.services.trip_brief.countries_service.get", return_value=country_doc), \
             patch("atlas.services.trip_brief.currency_service.rate", return_value=rate_doc), \
             patch("atlas.services.trip_brief.climate_service.for_city", side_effect=fake_climate), \
             patch("atlas.services.trip_brief.advisory_service.for_cca3", return_value=adv_doc):
            brief = trip_brief.build(uid, tid)

        assert brief["trip"]["name"] == "Japan 2027"
        assert len(brief["stops"]) == 2
        assert brief["countries"]["JPN"]["name"]["common"] == "Japan"
        assert "JPY" in brief["currencies"]
        assert brief["currencies"]["JPY"]["rate"] == 153.42
        assert brief["languages"] == ["Japanese"]
        assert brief["advisories"]["JPN"]["level"] == 1
        for stop in brief["stops"]:
            assert "climate_score" in stop
            assert "climate_verdict" in stop


def test_brief_returns_none_for_other_users_trip(app):
    uid, tid = _seed_japan_trip(app)
    with app.app_context():
        other = users_repo.create("other", "abc12345")
        assert trip_brief.build(other, tid) is None


def test_brief_handles_missing_advisory_and_country_gracefully(app):
    uid, tid = _seed_japan_trip(app)
    with app.app_context():
        with patch("atlas.services.trip_brief.countries_service.get", return_value=None), \
             patch("atlas.services.trip_brief.currency_service.rate", return_value=None), \
             patch("atlas.services.trip_brief.climate_service.for_city", return_value=None), \
             patch("atlas.services.trip_brief.advisory_service.for_cca3", return_value=None):
            brief = trip_brief.build(uid, tid)
        assert brief is not None
        assert brief["trip"]["name"] == "Japan 2027"
        assert len(brief["stops"]) == 2
        assert brief["advisories"]["JPN"] is None
