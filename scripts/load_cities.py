"""One-time loader for GeoNames cities15000.

Downloads https://download.geonames.org/export/dump/cities15000.zip,
extracts cities15000.txt, and inserts rows into the cities table.

Usage:
    python -m scripts.load_cities
"""
import csv
import json
import zipfile
from pathlib import Path

import click
import requests

from atlas import create_app
from atlas.repos.sqlite import init_schema
from atlas.repos import cities as cities_repo


URL = "https://download.geonames.org/export/dump/cities15000.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ZIP_PATH = DATA_DIR / "cities15000.zip"
TXT_PATH = DATA_DIR / "cities15000.txt"
CCA2_TO_CCA3_PATH = DATA_DIR / "cca2_to_cca3.json"

# GeoNames TSV columns per https://download.geonames.org/export/dump/readme.txt
COLS = ["geonameid", "name", "asciiname", "alternatenames", "latitude",
        "longitude", "feature_class", "feature_code", "country_code", "cc2",
        "admin1_code", "admin2_code", "admin3_code", "admin4_code",
        "population", "elevation", "dem", "timezone", "modification_date"]


def download():
    if ZIP_PATH.exists():
        click.echo(f"already downloaded: {ZIP_PATH}")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    click.echo(f"downloading {URL} ...")
    r = requests.get(URL, timeout=60, stream=True)
    r.raise_for_status()
    with open(ZIP_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=64 * 1024):
            f.write(chunk)
    click.echo("download complete")


def extract():
    if TXT_PATH.exists():
        return
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extract("cities15000.txt", DATA_DIR)


def load_cca2_to_cca3():
    if not CCA2_TO_CCA3_PATH.exists():
        raise FileNotFoundError(
            f"Missing {CCA2_TO_CCA3_PATH}. Run `python -m scripts.warm_countries` first."
        )
    return json.loads(CCA2_TO_CCA3_PATH.read_text(encoding="utf-8"))


def parse_rows(cca2_to_cca3):
    with open(TXT_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for raw in reader:
            if len(raw) != len(COLS):
                continue
            row = dict(zip(COLS, raw))
            cca2 = row["country_code"]
            cca3 = cca2_to_cca3.get(cca2)
            if not cca3:
                continue
            try:
                yield {
                    "id": int(row["geonameid"]),
                    "name": row["name"],
                    "ascii_name": row["asciiname"] or row["name"],
                    "country_code": cca2,
                    "country_cca3": cca3,
                    "admin1": row["admin1_code"] or None,
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "population": int(row["population"]) if row["population"] else None,
                    "timezone": row["timezone"] or None,
                }
            except (ValueError, KeyError):
                continue


def main():
    download()
    extract()
    cca2_to_cca3 = load_cca2_to_cca3()

    app = create_app()
    with app.app_context():
        init_schema()
        BATCH_SIZE = 2000
        batch = []
        total = 0
        for row in parse_rows(cca2_to_cca3):
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                cities_repo.insert_many(batch)
                total += len(batch)
                batch = []
                click.echo(f"  inserted {total} so far ...")
        if batch:
            cities_repo.insert_many(batch)
            total += len(batch)
        click.echo(f"done: {total} cities inserted")


if __name__ == "__main__":
    main()
