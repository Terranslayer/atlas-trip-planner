import pytest
import requests
from unittest.mock import patch, MagicMock

from atlas.services.http import get_json, HTTPError


def test_get_json_returns_parsed_payload():
    fake = MagicMock(status_code=200)
    fake.json.return_value = {"ok": True}
    fake.raise_for_status = MagicMock()
    with patch("atlas.services.http.requests.get", return_value=fake) as m:
        assert get_json("https://example.test") == {"ok": True}
        m.assert_called_once()
        assert m.call_args.kwargs["timeout"] == 5


def test_get_json_raises_httperror_on_non_2xx():
    fake = MagicMock(status_code=500)
    fake.raise_for_status.side_effect = requests.HTTPError("500")
    with patch("atlas.services.http.requests.get", return_value=fake):
        with pytest.raises(HTTPError):
            get_json("https://example.test")


def test_get_json_retries_on_timeout(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **kw):
        calls["n"] += 1
        if calls["n"] < 2:
            raise requests.Timeout("slow")
        r = MagicMock(status_code=200)
        r.json.return_value = {"ok": True}
        r.raise_for_status = MagicMock()
        return r

    monkeypatch.setattr("atlas.services.http.requests.get", fake_get)
    monkeypatch.setattr("atlas.services.http.time.sleep", lambda *_: None)
    assert get_json("https://example.test") == {"ok": True}
    assert calls["n"] == 2
