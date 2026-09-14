"""Bulk-fetch REST Countries and write data/cca2_to_cca3.json plus warm MongoDB.

Usage:
    python -m scripts.warm_countries
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import click
import requests

from atlas import create_app


# REST Countries enforces a 10-field cap per request as of late 2024, so we
# split the schema across two batches and merge them on cca3 before persisting.
BASE = "https://restcountries.com/v3.1/all"
FIELDS_A = ["cca2", "cca3", "name", "flags", "capital", "region", "subregion", "population", "languages", "currencies"]
FIELDS_B = ["cca3", "timezones", "borders", "latlng", "car", "idd"]
OUT = Path(__file__).resolve().parent.parent / "data" / "cca2_to_cca3.json"


def _fetch(fields):
    url = f"{BASE}?fields={','.join(fields)}"
    click.echo(f"fetching {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    batch_a = _fetch(FIELDS_A)
    batch_b = _fetch(FIELDS_B)
    b_by_cca3 = {c["cca3"]: c for c in batch_b if c.get("cca3")}
    countries = []
    for c in batch_a:
        if not c.get("cca3"):
            continue
        merged = dict(c)
        merged.update(b_by_cca3.get(c["cca3"], {}))
        countries.append(merged)

    mapping = {c["cca2"]: c["cca3"] for c in countries if c.get("cca2") and c.get("cca3")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    click.echo(f"wrote {OUT} with {len(mapping)} entries")

    app = create_app()
    with app.app_context():
        try:
            from atlas.repos import mongo as mongo_repo
            db = mongo_repo.get_db()
        except Exception as e:
            click.echo(f"skipping MongoDB warm: {e}")
            return

        from pymongo import UpdateOne
        ops = []
        for c in countries:
            doc = {
                "_id": c["cca3"],
                "name": c.get("name", {}),
                "cca2": c.get("cca2"),
                "capital": c.get("capital", []),
                "region": c.get("region"),
                "subregion": c.get("subregion"),
                "population": c.get("population"),
                "languages": c.get("languages", {}),
                "currencies": c.get("currencies", {}),
                "flags": c.get("flags", {}),
                "timezones": c.get("timezones", []),
                "borders": c.get("borders", []),
                "latlng": c.get("latlng", []),
                "car": c.get("car", {}),
                "idd": c.get("idd", {}),
                "cached_at": datetime.now(timezone.utc),
            }
            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
        if ops:
            db["countries_cache"].bulk_write(ops)
            click.echo(f"upserted {len(ops)} countries into MongoDB")


if __name__ == "__main__":
    main()
