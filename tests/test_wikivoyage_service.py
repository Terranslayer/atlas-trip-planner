from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from atlas.services import wikivoyage
from atlas.repos import mongo as mongo_repo


def _clean(name="WikivoyageTestCountry"):
    return name


def test_for_country_returns_cached_when_fresh(app):
    name = _clean()
    with app.app_context():
        db = mongo_repo.get_db()
        db["travel_notes_cache"].delete_many({"_id": name})
        db["travel_notes_cache"].insert_one({
            "_id": name,
            "sections": {"Stay safe": "<p>Safe.</p>"},
            "source_url": "https://en.wikivoyage.org/wiki/" + name,
            "cached_at": datetime.now(timezone.utc),
        })
        with patch("atlas.services.wikivoyage.get_json") as m:
            doc = wikivoyage.for_country(name)
            m.assert_not_called()
            assert "Stay safe" in doc["sections"]
        db["travel_notes_cache"].delete_many({"_id": name})


def test_for_country_fetches_and_caches_when_missing(app):
    name = _clean("WikivoyageMissCountry")
    sections_payload = {
        "parse": {
            "sections": [
                {"line": "Overview", "index": "1"},
                {"line": "Get in",   "index": "2"},
                {"line": "Stay safe","index": "3"},
                {"line": "Money",    "index": "4"},
            ]
        }
    }
    section_html = {
        "2": '<p>Fly into the international airport.</p><a href="/wiki/Visa">Visa</a>',
        "3": '<p>Generally safe. Avoid demonstrations.</p>',
        "4": '<p>Local currency widely accepted.</p>',
    }

    def fake_get_json(url, params, **kwargs):
        if params.get("prop") == "sections":
            return sections_payload
        idx = params.get("section")
        return {"parse": {"text": {"*": section_html[idx]}}}

    with app.app_context():
        db = mongo_repo.get_db()
        db["travel_notes_cache"].delete_many({"_id": name})
        with patch("atlas.services.wikivoyage.get_json", side_effect=fake_get_json):
            doc = wikivoyage.for_country(name)
        assert doc is not None
        assert set(doc["sections"].keys()) == {"Get in", "Stay safe", "Money"}
        # Sanitiser must have rewritten the internal /wiki/ link to absolute.
        assert "https://en.wikivoyage.org/wiki/Visa" in doc["sections"]["Get in"]
        # Plain paragraph content survives sanitisation.
        assert "Fly into" in doc["sections"]["Get in"]
        db["travel_notes_cache"].delete_many({"_id": name})


def test_for_country_returns_none_when_upstream_404_and_no_cache(app):
    name = _clean("WikivoyageBrokenCountry")
    with app.app_context():
        db = mongo_repo.get_db()
        db["travel_notes_cache"].delete_many({"_id": name})
        from atlas.services.http import HTTPError
        with patch("atlas.services.wikivoyage.get_json", side_effect=HTTPError("404")):
            assert wikivoyage.for_country(name) is None
        db["travel_notes_cache"].delete_many({"_id": name})


def test_for_country_returns_stale_on_upstream_failure(app):
    name = _clean("WikivoyageStaleCountry")
    with app.app_context():
        db = mongo_repo.get_db()
        db["travel_notes_cache"].delete_many({"_id": name})
        stale = datetime.now(timezone.utc) - timedelta(days=30)
        db["travel_notes_cache"].insert_one({
            "_id": name,
            "sections": {"Stay safe": "<p>old advice</p>"},
            "source_url": "x",
            "cached_at": stale,
        })
        from atlas.services.http import HTTPError
        with patch("atlas.services.wikivoyage.get_json", side_effect=HTTPError("500")):
            doc = wikivoyage.for_country(name)
        assert doc is not None
        assert doc.get("stale") is True
        assert "Stay safe" in doc["sections"]
        db["travel_notes_cache"].delete_many({"_id": name})


def test_sanitiser_strips_script_tags(app):
    name = _clean("WikivoyageScriptCountry")
    sections_payload = {"parse": {"sections": [{"line": "Stay safe", "index": "1"}]}}
    bad_html = '<p>OK.</p><script>alert(1)</script><p onclick="bad()">click</p>'

    def fake_get_json(url, params, **kwargs):
        if params.get("prop") == "sections":
            return sections_payload
        return {"parse": {"text": {"*": bad_html}}}

    with app.app_context():
        db = mongo_repo.get_db()
        db["travel_notes_cache"].delete_many({"_id": name})
        with patch("atlas.services.wikivoyage.get_json", side_effect=fake_get_json):
            doc = wikivoyage.for_country(name)
        html = doc["sections"]["Stay safe"]
        # The <script> tag itself is stripped — bleach with strip=True leaves
        # the inner text as inert characters, which is fine (no JS executes).
        assert "<script" not in html
        # Event-handler attributes are dropped, leaving only the bare <p>.
        assert "onclick" not in html
        assert "<p>OK.</p>" in html
        db["travel_notes_cache"].delete_many({"_id": name})
