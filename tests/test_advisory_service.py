from datetime import datetime, timezone
from unittest.mock import patch

from atlas.services import advisory as advisory_service
from atlas.repos import mongo as mongo_repo


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Travel Advisories</title>
<item>
  <title>Japan - Level 1: Exercise Normal Precautions</title>
  <link>https://travel.state.gov/.../japan-travel-advisory.html</link>
  <pubDate>Fri, 14 Mar 2026 12:00:00 GMT</pubDate>
  <description>Exercise normal precautions in Japan.</description>
  <category>JP</category>
</item>
<item>
  <title>Russia - Level 4: Do Not Travel</title>
  <link>https://travel.state.gov/.../russia-travel-advisory.html</link>
  <pubDate>Fri, 14 Mar 2026 12:00:00 GMT</pubDate>
  <description>Do not travel to Russia.</description>
  <category>RU</category>
</item>
</channel></rss>"""


def test_refresh_parses_rss_and_writes_advisories(app):
    with app.app_context():
        db = mongo_repo.get_db()
        # The resolver uses country names, not the RSS category's FIPS codes.
        db["countries_cache"].insert_many([
            {"_id": "JPN", "cca2": "JP", "name": {"common": "Japan", "official": "Japan"}},
            {"_id": "RUS", "cca2": "RU", "name": {"common": "Russia", "official": "Russian Federation"}},
        ])
        with patch("atlas.services.advisory.get_text", return_value=SAMPLE_RSS):
            n = advisory_service.refresh()
        assert n == 2
        japan = db["advisory_cache"].find_one({"_id": "JPN"})
        assert japan["level"] == 1
        assert "normal" in (japan.get("summary") or "").lower()
        russia = db["advisory_cache"].find_one({"_id": "RUS"})
        assert russia["level"] == 4


def test_for_cca3_returns_advisory_when_present(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["advisory_cache"].delete_many({"_id": "TJPN_TEST"})
        db["advisory_cache"].insert_one({
            "_id": "TJPN_TEST", "cca2": "JP", "country": "Japan",
            "level": 1, "level_text": "Exercise Normal Precautions",
            "summary": "x", "url": "https://...", "published": "2026-03-14",
            "cached_at": datetime.now(timezone.utc),
        })
        a = advisory_service.for_cca3("TJPN_TEST")
        assert a["level"] == 1
        db["advisory_cache"].delete_many({"_id": "TJPN_TEST"})


def test_for_cca3_returns_none_when_missing(app):
    with app.app_context():
        db = mongo_repo.get_db()
        db["advisory_cache"].delete_many({"_id": "TZZZ_TEST"})
        assert advisory_service.for_cca3("TZZZ_TEST") is None
