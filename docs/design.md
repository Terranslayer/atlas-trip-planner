# ENPM818Q Capstone Design Document

**Project:** Atlas — A Country and City Travel Planning Companion
**Author:** yxz2803@umd.edu
**Course:** ENPM818Q, Spring 2026
**Document version:** 1.0
**Date:** 2026-05-11

---

## 1. Project Overview

### 1.1 Project Title

Atlas — A Country and City Travel Planning Companion.

### 1.2 One-Paragraph Summary

Atlas is a Flask web application that helps an individual traveler plan future trips at the city level and maintain a structured record of cities they have visited. It combines a queryable reference of countries and major cities with personal data — a wishlist, a visited log, and named trips that group cities into a planned itinerary. For each planned trip, Atlas automatically generates a one-page brief that aggregates information genuinely useful for departure: relevant currencies and current exchange rates, official languages, a climate-match assessment based on the user's travel dates, the United States Department of State travel advisory level, and key facts such as time zone, plug type, drive side, and visa-free duration. The application demonstrates polyglot persistence by storing user-owned relational data in SQLite and document-style external-API caches in MongoDB Atlas, and it integrates six free external data sources without any paid API keys.

### 1.3 Core Use Cases

1. *As a traveler planning a future trip*, I want to assemble a list of cities I want to visit, organize them into a named trip with date ranges, and see an auto-generated brief, so that I can prepare for the trip without consulting six separate websites.
2. *As a returning traveler*, I want to log cities I have visited with personal notes and dates, so that I can maintain a personal record of my travel history visually on a map.
3. *As a user exploring destinations*, I want to search any major city or country and see practical information — currency, language, time zone, climate, travel advisories — so that I can make informed decisions about whether and when to visit.
4. *As a user with multiple planned trips*, I want a dashboard that shows upcoming trips with countdowns, the currencies and languages relevant to my wishlist, and my entire travel plan on a world map, so that I can manage my travel intent at a glance.

### 1.4 Success Criteria

The project is considered successfully delivered when all of the following hold:

- A new user can register an account, log in, and access their own private wishlist, visited log, and trips. Account data is isolated per user.
- City-level search returns relevant matches from the preloaded GeoNames dataset within 300 ms for typical queries.
- A trip with at least two stops can be created, its stops reordered via drag-and-drop, and its auto-generated Trip Brief renders all five informational sections (currency, languages, climate match, advisory, country basics) using live data from external APIs.
- The dashboard renders all wishlist, visited, and trip cities on a world map. Trips with two or more stops display colored polylines with directional arrows connecting consecutive cities in itinerary order.
- The Trip Brief can be exported as a Markdown file.
- The application continues to render meaningful content when any single external API is unreachable, using cached data from MongoDB Atlas.

---

## 2. Users & Scenarios

### 2.1 Target Users

Atlas targets a single class of user: an individual leisure traveler comfortable with English-language web interfaces. The interface, labels, and all generated content are in English; localization is out of scope. Users are assumed to have basic web browser proficiency. The application is multi-tenant in that any number of independent accounts can be registered, and each account has its own private data, but it is not designed for collaboration between users. Trips, wishlists, and visited logs are strictly per-user and never visible to others.

The application defaults to the assumption that the user holds a United States passport when displaying visa-free travel duration. Per-user passport configuration is out of scope, since the course project does not require it and the simplification avoids storing nationality data without a clear product reason.

### 2.2 Main User Flows

**Flow A — Registration and first login**

1. Visitor opens the application URL.
2. Visitor follows the "Register" link, enters a username and password, and submits.
3. The server creates the user record, salts and hashes the password, and signs the visitor in.
4. The user lands on the empty Dashboard, which prompts them to begin browsing or to create a trip.

**Flow B — Adding a city to the wishlist**

1. From any page, the user clicks "Browse" in the top navigation.
2. The user types a query into the search box and submits the form. The server returns a results table backed by the preloaded GeoNames data.
3. Each row shows the city, the country's full name resolved from `countries_cache`, the population, and two actions: "+ Wishlist" and "View country."
4. Clicking "+ Wishlist" adds the city to the user's wishlist immediately at default priority; clicking "View country" opens the country detail page, where the in-page city panel offers the same action with a note + priority form.
5. The wishlist entry is persisted in SQLite, scoped to the current user.

**Flow C — Planning a trip**

1. From the Dashboard, the user clicks "New Trip" and enters a name and tentative date range.
2. On the trip detail page, the user adds existing wishlist cities to the trip via a city picker, or types in new cities directly (which are added to the wishlist on the fly).
3. For each stop, the user enters an arrival and departure date and reorders stops by dragging.
4. The Trip Brief panel re-renders automatically after each change, refetching climate, currency, and advisory data as needed.

**Flow D — Logging a visited city**

1. From the city detail panel, the user clicks "Mark as visited."
2. The user enters the date visited and an optional journal note.
3. The visited record is persisted in SQLite. The Dashboard map updates to show the city as green on next refresh.

**Flow E — Exporting a trip brief**

1. On any trip detail page, the user clicks "Export Brief (.md)."
2. The server renders the brief as Markdown and serves it with a `Content-Disposition: attachment` header.
3. The user saves the file locally for offline reference.

---

## 3. Data & External Services

### 3.1 External Data Sources

All external services used by Atlas are free, public, and require no API key.

| Service | Purpose | Endpoint | Notes |
|---|---|---|---|
| REST Countries v3.1 | Country-level metadata (name, capital, currency, languages, timezones, plug types, drive side, calling codes, flags) | `https://restcountries.com/v3.1/all?fields=…` and `/alpha/{cca3}` | Light rate limits; we always pass the `fields` parameter to reduce payload and avoid the gated `/all` mode. |
| GeoNames cities15000 | City dataset (cities with population ≥ 15,000), used as the source of truth for searchable city entities | Tab-separated dump: `https://download.geonames.org/export/dump/cities15000.zip` | One-time CSV import into SQLite. Approximately 26,000 rows. |
| Frankfurter | Live currency exchange rates | `https://api.frankfurter.app/latest?from=USD&to=…` | Updated daily on weekdays at the European Central Bank rate. |
| Open-Meteo Climate API | Monthly climate normals for any latitude/longitude (temperature, precipitation) | `https://climate-api.open-meteo.com/v1/climate` | Used to score the climate match for trip dates. |
| US State Department Travel Advisories | Per-country travel advisory levels (1–4) | RSS feed: `https://travel.state.gov/_res/rss/TAsTWs.xml` | Polled once per day. The full text page can be linked from the badge. |
| Wikivoyage MediaWiki API (stretch) | Per-country travel guide sections ("Get In," "Stay safe," "Etiquette," "Money") | `https://en.wikivoyage.org/w/api.php` with `action=parse` and section index | Used only if implementation time permits. |

### 3.2 Local Data

**SQLite** stores user-owned relational data and the static cities reference table. Tables are described in detail in §6.1.

**MongoDB Atlas** stores cache documents for the external services above. Each cache collection has a different time-to-live policy reflecting the underlying volatility of the source:

| Collection | Source | Document granularity | TTL |
|---|---|---|---|
| `countries_cache` | REST Countries | One document per country (keyed by `cca3`) | 7 days |
| `currency_cache` | Frankfurter | One document per currency pair | 1 hour |
| `climate_cache` | Open-Meteo | One document per city, with 12 monthly entries | 30 days |
| `advisory_cache` | US Travel Advisories | One document per country | 24 hours |
| `travel_notes_cache` | Wikivoyage (stretch) | One document per country with per-section text | 7 days |

### 3.3 Environment Variables and Secrets

The following variables must be defined in a `.env` file at the project root. The repository includes a `.env.example` template with placeholder values. No real secrets are committed.

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Session cookie signing key (high-entropy random string) |
| `MONGODB_URI` | MongoDB Atlas connection string |
| `MONGODB_DB_NAME` | Database name on the Atlas cluster (defaults to `atlas_capstone`) |
| `REST_COUNTRIES_BASE` | REST Countries base URL (defaults to `https://restcountries.com/v3.1`) |
| `FRANKFURTER_BASE` | Frankfurter base URL (defaults to `https://api.frankfurter.app`) |
| `OPEN_METEO_BASE` | Open-Meteo Climate base URL |
| `CACHE_TTL_HOURS_COUNTRIES` | Override for countries cache TTL (defaults to 168) |
| `CACHE_TTL_HOURS_CLIMATE` | Override for climate cache TTL (defaults to 720) |
| `CACHE_TTL_HOURS_CURRENCY` | Override for currency cache TTL (defaults to 1) |
| `CACHE_TTL_HOURS_ADVISORY` | Override for advisory cache TTL (defaults to 24) |

---

## 4. System Architecture

### 4.1 High-Level Description

The browser communicates with a single Flask process over HTTP. The Flask process delegates to a service layer; the service layer in turn communicates with three persistence backends: SQLite for relational and user-owned data, MongoDB Atlas for document caches, and the six external HTTP APIs listed in §3.1. Templates are rendered server-side with Jinja. Interactive client-side behavior — the world map, charts, and drag-and-drop reordering — is implemented with three CDN-loaded libraries: Leaflet, leaflet-polylinedecorator, and Chart.js. No JavaScript build step is required.

```
Browser ── HTTP ──▶ Flask routes ──▶ Service layer ──┬──▶ REST Countries
                          │                            ├──▶ Frankfurter
                          │                            ├──▶ Open-Meteo Climate
                          │                            ├──▶ US State Advisories
                          │                            ├──▶ Wikivoyage (stretch)
                          │                            ├──▶ MongoDB Atlas
                          │                            └──▶ SQLite
                          └──▶ Jinja templates ──▶ Browser
```

### 4.2 Main Components

- `app.py` — application factory, blueprint registration, session configuration.
- `routes/auth.py` — registration, login, logout.
- `routes/dashboard.py` — dashboard page, map data endpoint.
- `routes/countries.py` — country detail page.
- `routes/cities.py` — city search and city detail.
- `routes/wishlist.py` — wishlist CRUD.
- `routes/visited.py` — visited log CRUD.
- `routes/trips.py` — trip CRUD, stop CRUD, brief rendering, Markdown export.
- `services/countries_service.py` — coordinates cache and API for country data.
- `services/currency_service.py` — coordinates cache and API for exchange rates.
- `services/climate_service.py` — coordinates cache and API for monthly climate.
- `services/advisory_service.py` — pulls and parses the State Department RSS feed.
- `services/wikivoyage_service.py` — fetches per-section content (stretch).
- `services/api_client.py` — shared HTTP client with timeouts and retry policy.
- `repos/sqlite_repo.py` — data-access functions for all SQLite tables.
- `repos/mongo_repo.py` — data-access functions for all MongoDB collections.
- `repos/cities_loader.py` — one-time bootstrap that loads GeoNames into SQLite.
- `templates/` — base layout and per-page templates.
- `static/` — CSS, GeoJSON world borders (used by Dashboard map), and any small client scripts.

The route layer never calls external HTTP APIs or database drivers directly; it always goes through the service or repository layer. This separation matters for testability and for keeping retry / cache logic in one place.

### 4.3 Data Flow: Rendering a Trip Brief

This is the most complex flow and exercises every layer.

1. The browser issues `GET /trips/<trip_id>`.
2. The trips route handler validates that the requested trip belongs to the logged-in user (SQLite lookup, abort 404 otherwise).
3. The handler loads the trip, its stops in `sequence_order`, and the cities referenced by those stops, all from SQLite.
4. For each distinct country in the trip, the country service is asked for the country document. The service first looks up `countries_cache` in MongoDB; if missing or older than the 7-day TTL, it fetches `/v3.1/alpha/{cca3}` from REST Countries, normalizes the response, and upserts the cache.
5. For each distinct currency in the trip, the currency service returns a `USD -> <currency>` rate, similarly cached for 1 hour.
6. For each stop, the climate service returns the city's 12-month climate normals (cached for 30 days). The handler picks the rows for the stop's months and runs the climate-match scoring function (see §7.2 for rules).
7. For each distinct country in the trip, the advisory service returns the latest US State Department level (cached for 24 hours).
8. If the Wikivoyage stretch feature is implemented, the handler fetches the relevant per-country sections.
9. The handler hands all aggregated data to `trips/brief.html`, which renders the page.

The same data structure is reused for Markdown export — the export route calls the same aggregation function and passes its output to a Markdown template instead of HTML.

---

## 5. Flask Routes & Pages

| Path | Methods | Auth | Template / Response | Reads | Writes |
|---|---|---|---|---|---|
| `/` | GET | — | redirect to `/dashboard` if logged in, else `/login` | session | — |
| `/register` | GET, POST | no | `auth/register.html` | form | SQLite insert into `users` |
| `/login` | GET, POST | no | `auth/login.html` | form, SQLite users | session |
| `/logout` | POST | yes | redirect to `/login` | — | session |
| `/dashboard` | GET | yes | `dashboard.html` | SQLite wishlist/visited/trips/cities | — |
| `/api/map-data` | GET | yes | JSON | SQLite + MongoDB | — |
| `/cities/search` | GET | yes | JSON list (autocomplete) | SQLite `cities` (indexed `ascii_name`) | — |
| `/cities/<city_id>` | GET | yes | `cities/detail.html` | SQLite cities + MongoDB countries_cache | — |
| `/countries/<cca3>` | GET | yes | `countries/detail.html` | MongoDB caches (countries, currency, advisory) | — |
| `/wishlist` | GET | yes | `wishlist/list.html` | SQLite | — |
| `/wishlist/add` | POST | yes | redirect | form | SQLite insert |
| `/wishlist/<id>/edit` | POST | yes | redirect | form | SQLite update |
| `/wishlist/<id>/delete` | POST | yes | redirect | — | SQLite delete |
| `/visited` | GET | yes | `visited/list.html` | SQLite | — |
| `/visited/add` | POST | yes | redirect | form | SQLite insert |
| `/visited/<id>/edit` | POST | yes | redirect | form | SQLite update |
| `/visited/<id>/delete` | POST | yes | redirect | — | SQLite delete |
| `/trips` | GET | yes | `trips/list.html` | SQLite | — |
| `/trips/new` | POST | yes | redirect to `/trips/<id>` | form | SQLite insert |
| `/trips/<id>` | GET | yes | `trips/brief.html` | SQLite + all MongoDB caches | — |
| `/trips/<id>/edit` | POST | yes | redirect | form | SQLite update |
| `/trips/<id>/delete` | POST | yes | redirect to `/trips` | — | SQLite delete |
| `/trips/<id>/stops/add` | POST | yes | redirect | form | SQLite insert into `trip_stops` |
| `/trips/<id>/stops/<stop_id>/edit` | POST | yes | redirect | form | SQLite update |
| `/trips/<id>/stops/<stop_id>/delete` | POST | yes | redirect | — | SQLite delete |
| `/trips/<id>/stops/reorder` | POST | yes | JSON `{ok:true}` | JSON body `[stop_id, ...]` | SQLite update `sequence_order` |
| `/trips/<id>/export.md` | GET | yes | Markdown file download | SQLite + all MongoDB caches | — |
| `/admin/refresh` | POST | yes + admin | redirect | — | MongoDB bulk upsert |

All POST routes are protected by Flask-WTF's CSRF token, except `/cities/search` (GET-only) and `/api/map-data` (GET-only).

---

## 6. Database Design

### 6.1 SQLite Schema

```sql
CREATE TABLE users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    is_admin       INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cities (
    id            INTEGER PRIMARY KEY,                 -- GeoNames geonameid
    name          TEXT    NOT NULL,
    ascii_name    TEXT    NOT NULL,
    country_code  TEXT    NOT NULL,                    -- ISO cca2
    country_cca3  TEXT    NOT NULL,                    -- joins to countries_cache._id
    admin1        TEXT,                                -- state/province name
    latitude      REAL    NOT NULL,
    longitude     REAL    NOT NULL,
    population    INTEGER,
    timezone      TEXT
);
CREATE INDEX idx_cities_name        ON cities(ascii_name);
CREATE INDEX idx_cities_country     ON cities(country_cca3);

CREATE TABLE wishlist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    city_id     INTEGER NOT NULL REFERENCES cities(id),
    note        TEXT,
    priority    INTEGER NOT NULL DEFAULT 1 CHECK(priority IN (0,1,2)),
    added_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, city_id)
);
CREATE INDEX idx_wishlist_user ON wishlist(user_id);

CREATE TABLE visited (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    city_id       INTEGER NOT NULL REFERENCES cities(id),
    visited_date  DATE    NOT NULL,
    journal       TEXT,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_visited_user      ON visited(user_id);
CREATE INDEX idx_visited_user_city ON visited(user_id, city_id);
-- No UNIQUE(user_id, city_id): a user may log multiple visits to the same city
-- (e.g., Tokyo in 2024 and again in 2027), each with its own date and journal note.

CREATE TABLE trips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    start_date  DATE,
    end_date    DATE,
    notes       TEXT,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_trips_user ON trips(user_id);

CREATE TABLE trip_stops (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_id         INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    city_id         INTEGER NOT NULL REFERENCES cities(id),
    arrival_date    DATE,
    departure_date  DATE,
    sequence_order  INTEGER NOT NULL,
    stop_notes      TEXT,
    UNIQUE(trip_id, sequence_order)
);
CREATE INDEX idx_stops_trip ON trip_stops(trip_id);
```

### 6.2 MongoDB Collections

The MongoDB schemas below are illustrative; documents are not strictly enforced by the database but are validated at the service layer before insert.

**`countries_cache`** (one document per country):

```jsonc
{
  "_id": "JPN",
  "name":      { "common": "Japan", "official": "Japan" },
  "capital":   ["Tokyo"],
  "region":    "Asia",
  "subregion": "Eastern Asia",
  "population": 125836021,
  "area":       377930,
  "languages":  { "jpn": "Japanese" },
  "currencies": { "JPY": { "name": "Japanese yen", "symbol": "¥" } },
  "flags":      { "png": "...", "svg": "...", "alt": "..." },
  "timezones":  ["UTC+09:00"],
  "borders":    [],
  "latlng":     [36.0, 138.0],
  "car":        { "side": "left" },
  "plug_types": ["A", "B"],
  "calling_code": "+81",
  "us_visa_free_days": 90,
  "cached_at":  { "$date": "2026-05-11T18:00:00Z" }
}
```

**`currency_cache`** (one document per pair):

```jsonc
{
  "_id":       "USD_JPY",
  "from":      "USD",
  "to":        "JPY",
  "rate":      153.42,
  "as_of":     "2026-05-10",
  "cached_at": { "$date": "2026-05-11T18:00:00Z" }
}
```

**`climate_cache`** (one document per city):

```jsonc
{
  "_id": 1850147,
  "city_name":  "Tokyo",
  "lat":        35.6762,
  "lon":        139.6503,
  "monthly":    [
    { "month":  1, "tavg_c":  5.2, "precip_mm":  52 },
    { "month":  2, "tavg_c":  6.1, "precip_mm":  56 },
    { "month":  3, "tavg_c":  9.4, "precip_mm": 117 },
    { "month":  4, "tavg_c": 14.3, "precip_mm": 124 },
    { "month":  5, "tavg_c": 18.8, "precip_mm": 137 },
    { "month":  6, "tavg_c": 21.9, "precip_mm": 167 },
    { "month":  7, "tavg_c": 25.7, "precip_mm": 153 },
    { "month":  8, "tavg_c": 26.9, "precip_mm": 168 },
    { "month":  9, "tavg_c": 23.3, "precip_mm": 209 },
    { "month": 10, "tavg_c": 18.0, "precip_mm": 197 },
    { "month": 11, "tavg_c": 12.5, "precip_mm":  92 },
    { "month": 12, "tavg_c":  7.7, "precip_mm":  51 }
  ],
  "cached_at": { "$date": "2026-05-11T18:00:00Z" }
}
```

**`advisory_cache`** (one document per country):

```jsonc
{
  "_id":         "JPN",
  "country":     "Japan",
  "level":       1,
  "level_text":  "Exercise Normal Precautions",
  "summary":     "...",
  "url":         "https://travel.state.gov/.../japan-travel-advisory.html",
  "published":   "2026-03-14",
  "cached_at":   { "$date": "2026-05-11T18:00:00Z" }
}
```

Indexes: each collection's `_id` is the natural primary key. Additional indexes are not required at the project's expected data volume.

### 6.3 Relationships and Constraints

- A user has many wishlist entries, many visited entries, and many trips. All three relations have `ON DELETE CASCADE` so removing a user cleans up their data.
- A trip has many trip stops. Each stop references a city and carries a position within the trip via `sequence_order`. The `(trip_id, sequence_order)` uniqueness constraint prevents duplicate positions; the reorder endpoint always renumbers from 0.
- `wishlist.city_id` and `visited.city_id` both reference `cities(id)`. Wishlist is uniqueness-constrained per `(user_id, city_id)` so a city cannot be added twice to one user's wishlist. Visited is *not* uniqueness-constrained, so a user can record multiple visits to the same city across different dates. Different users always track cities independently.
- `cities.country_cca3` is a logical foreign key to `countries_cache._id` in MongoDB. The reference is not enforced by either store but is validated at the service layer when a city is first inserted.

---

## 7. API Usage & Error Handling

### 7.1 Endpoints Called

| Service | Endpoint | Use |
|---|---|---|
| REST Countries | `GET /v3.1/alpha/{cca3}?fields=name,cca3,capital,region,subregion,population,languages,currencies,flags,timezones,borders,latlng,car,idd` | Country detail on demand |
| REST Countries | `GET /v3.1/all?fields=cca3,name,flags` | Used by `/admin/refresh` for bulk warm-up of `countries_cache`. Not required for normal operation, since the lazy lookup on country detail will populate entries on demand. |
| Frankfurter | `GET /latest?from=USD&to={code}` | Currency rate for a specific currency |
| Open-Meteo Climate | `GET /v1/climate?latitude={lat}&longitude={lon}&start_date=1991-01-01&end_date=2020-12-31&monthly=temperature_2m_mean,precipitation_sum` | 30-year monthly normals per city |
| US Travel Advisories | `GET https://travel.state.gov/_res/rss/TAsTWs.xml` | Daily advisory feed (parsed for level + URL per country) |
| Wikivoyage (stretch) | `GET /w/api.php?action=parse&page={country}&format=json&prop=wikitext&section={n}` | One section of the country's travel guide |

### 7.2 Failure Modes

| Failure | Behavior |
|---|---|
| External API timeout (5-second cap) | Service falls back to MongoDB cache. The page renders with a "cached <timestamp>" indicator on affected sections. |
| Cache miss and API down | Country detail and Trip Brief render the structural information available from local data (cities, dates, basic facts already saved) and display a yellow banner "Some live data is currently unavailable — try again later." Wishlist and trip CRUD remain fully functional because they do not require live external data. |
| Upstream returns 404 or unknown country code | Section is omitted and a small "Data not available for this country" notice is shown for that block only. |
| MongoDB Atlas unreachable | Cache-dependent pages show the maintenance banner but core wishlist/trip CRUD on SQLite remains functional. |
| Malformed input (e.g., trip dates with arrival after departure) | Form validation rejects with a per-field error message; no data is written. |

### 7.3 Validation and Security

- **Password hashing**: Werkzeug's `generate_password_hash` (PBKDF2-SHA256, default work factor). Passwords are never stored or logged in plaintext.
- **Session cookies**: `HttpOnly`, `SameSite=Lax`. The `SECURE` flag is set in production via environment variable.
- **CSRF**: All non-GET endpoints require a CSRF token, validated by Flask-WTF.
- **Authentication**: A `@login_required` decorator wraps every view that touches user-owned data. Unauthenticated requests are redirected to `/login` with the original destination preserved in the next-URL query parameter.
- **Authorization**: Every query for user-owned data (wishlist, visited, trips) includes `user_id = current_user.id` in the WHERE clause. The trip detail handler also confirms the requested trip belongs to the current user before any aggregation begins.
- **Input validation**:
  - Username: regex `^[A-Za-z0-9_]{3,30}$`.
  - Password: minimum length 8, at least one letter and one digit.
  - City search query: trimmed, length 1–60.
  - Notes / journal fields: ≤ 500 characters, HTML-escaped by Jinja's autoescape on render.
  - Trip dates: `end_date >= start_date`; stop `departure_date >= arrival_date`.
  - cca3 path parameter: regex `^[A-Z]{3}$`.
- **External data trust**: API responses are not echoed into rendered pages without escaping. Numeric fields are parsed and bounded; missing fields default to `null` and the template handles their absence.
- **Climate-match scoring rule** (deterministic): For each stop, take the average temperature and total precipitation for the months the stop spans. Apply: `temp_score = max(0, 1 - |t - 18|/15)` and `precip_score = max(0, 1 - max(0, p - 80)/120)`. Stop verdict: `Ideal` (combined ≥ 0.8), `Good` (≥ 0.5), `Fair` (≥ 0.25), `Poor` (< 0.25).

---

## 8. UX & Templates

### 8.1 Main Screens

- **Register** and **Login**: minimal forms, server-rendered errors.
- **Dashboard**: hero stats, world map with city pins and trip polylines (with directional arrows), upcoming trips countdown panel, currency cheat sheet, languages on user's list.
- **City Search**: search bar and result list, with each result linking to the city detail panel embedded within its country page.
- **Country Detail**: country basics table (timezone, drive side, plug, calling code, visa), current exchange rate, advisory badge, list of cities in that country with quick wishlist/visited toggles.
- **Wishlist** and **Visited**: tables of saved cities with note, priority, status, and inline edit/delete forms.
- **Trips index**: list of trips with countdowns and quick links.
- **Trip Brief**: itinerary table with drag-and-drop reordering, plus the five Trip Brief sections (currency, languages, climate match, advisory, country basics) and a Markdown export button.

### 8.2 Template Structure

A single `base.html` provides the document scaffold, navigation, and a flash-messages block. All pages extend `base.html` and override `{% block content %}`. Shared partials live in `templates/_partials/` and are included where useful — for example, the city-card partial is reused on Dashboard, search results, and trip stop lists.

```
templates/
├── base.html
├── _partials/
│   ├── city_card.html
│   ├── advisory_badge.html
│   └── climate_pill.html
├── auth/
│   ├── login.html
│   └── register.html
├── dashboard.html
├── cities/
│   └── detail.html
├── countries/
│   └── detail.html
├── wishlist/list.html
├── visited/list.html
└── trips/
    ├── list.html
    ├── brief.html
    └── brief.md.jinja
```

The Markdown template `brief.md.jinja` shares partials for itinerary and country-basics rendering by overriding only their text rendering blocks.

### 8.3 Forms and Feedback

| Form | Fields | Validation | Feedback |
|---|---|---|---|
| Register | username, password, confirm password | per §7.3 | success: redirect to Dashboard; error: per-field |
| Login | username, password | non-empty | success: redirect to next URL or Dashboard; error: generic "Invalid credentials" |
| Add to wishlist | city_id (hidden), note, priority | priority in {0,1,2}; note ≤ 500 | success: flash "Added"; duplicate: flash "Already in wishlist" |
| Edit wishlist | note, priority | as above | flash on save |
| Mark visited | city_id (hidden), date, journal | date ≤ today | flash "Logged" |
| New trip | name, start_date, end_date | end ≥ start; name 1–60 | redirect to trip detail |
| Edit trip stop | arrival_date, departure_date, notes | departure ≥ arrival | inline rerender |

All forms render server-side error messages adjacent to the relevant field. Successful actions emit a flash message styled as a dismissible green banner; errors use a yellow banner.

---

## 9. Milestones & Work Plan

### 9.1 Phases

This project is a single-student effort. Work is divided into four weekly phases.

### 9.2 Tasks

| Phase | Tasks |
|---|---|
| Week 1 — Scaffold | Initialize repository and Python environment. Implement Flask application factory and base template. Set up `.env` loading. Add Flask-WTF and Werkzeug. Build registration, login, logout, and `@login_required` decorator. Connect to SQLite and MongoDB Atlas with smoke-test endpoints. Write and run the GeoNames cities loader. Add CSRF protection. |
| Week 2 — Core data and country detail | Implement the REST Countries API client and `countries_cache` repository. Implement the Frankfurter currency service. Build the country detail page rendering basics, currency, and the advisory badge stub. Implement city search (autocomplete) over the indexed `cities.ascii_name` column. Implement wishlist and visited CRUD with city-level granularity. |
| Week 3 — Trips and dashboard | Implement trip and trip-stop CRUD, including the drag-and-drop reorder endpoint. Build the Trip Brief aggregation function and the brief template. Implement the climate service and climate-match scoring. Implement the dashboard map with city pins and trip polylines using leaflet-polylinedecorator. Wire up the upcoming trips, currency, and language panels. |
| Week 4 — Polish and stretch | Implement Markdown export of the Trip Brief. Implement the US Travel Advisories service (RSS parsing, daily refresh). If time permits, integrate the Wikivoyage section extractor. Write README and setup instructions. Write the final report. Prepare the presentation. Run end-to-end manual tests. |

### 9.3 Timeline

The course timeline is week 13 through week 16 of the term:

- **End of week 13**: phases 1 and 2 complete. A registered user can search cities, view country detail with currency, and manage their wishlist.
- **End of week 14**: phase 3 complete. Trip and Trip Brief work end-to-end. Dashboard map renders.
- **End of week 16**: phase 4 complete. Markdown export and advisories are integrated. Report and presentation are submitted.

---

## 10. Testing & Demo Plan

### 10.1 Manual Test Scenarios

1. **Cold start**: empty database. Register a new account. Verify Dashboard shows zero stats and an empty map.
2. **First wishlist**: search "Reykjavik," click result, add to wishlist with note "summer 2026." Verify entry appears in `/wishlist` and Dashboard count updates.
3. **First visited**: log Reykjavik as visited with date and a journal entry. Verify map pin turns green.
4. **Multi-stop trip**: create trip "Japan Spring 2027." Add Tokyo, Kyoto, Osaka with appropriate dates. Drag Kyoto above Tokyo and back. Verify `sequence_order` updates persist after refresh. Verify Trip Brief renders all five sections.
5. **API resilience**: temporarily block outbound HTTP to `restcountries.com` (firewall rule). Reload the country detail page. Verify cached content still renders with a "cached" indicator.
6. **Markdown export**: download Tokyo trip brief. Open the file. Verify all sections are present and human-readable.
7. **Per-user isolation**: register a second account, log in, and verify the second user sees an empty Dashboard and no trace of the first user's data.
8. **CSRF protection**: submit a wishlist add form with a stripped CSRF token. Verify the request is rejected.
9. **Password policy**: attempt to register with password `short`. Verify the form rejects it.

### 10.2 Automated Tests

A small `pytest` suite covers the most error-prone units, without aiming for full coverage:

- `tests/test_api_client.py` — mocks REST Countries responses (including a malformed payload) and asserts that parsing and field defaulting behave as specified.
- `tests/test_climate_scoring.py` — exercises the climate-match rule against fixed inputs at boundary cases (e.g., 18°C and 80 mm should score 1.0; 0°C and 0 mm should score lower).
- `tests/test_repos.py` — exercises wishlist, visited, and trip CRUD against a temporary SQLite file, including the unique-per-user constraint and the cascade-on-user-delete behavior.

### 10.3 Demo Script

A 5-minute live walkthrough:

1. Open `/register`. Create a new account on the projector. Note password hashing and CSRF token presence in browser dev tools.
2. From the empty Dashboard, click "Browse cities" and search "Tokyo." Add Tokyo to wishlist with a note.
3. Add Kyoto and Osaka similarly.
4. Create a trip "Japan Spring 2027." Add the three cities. Set dates. Drag Kyoto above Tokyo and back, demonstrating persistence.
5. Open the Trip Brief. Walk through the five sections: currency rate (live from Frankfurter), languages, climate match chart (with Apr highlighted), advisory level, and country basics. Toggle one city off the climate chart to demonstrate the per-city toggle.
6. Click "Export Brief (.md)." Open the downloaded file in a text editor to show its structure.
7. Return to Dashboard. Show the map with the three red Tokyo→Kyoto→Osaka trip pins connected by a red arrow polyline. Hover any pin to show the tooltip.
8. Briefly show the data flow diagram and the polyglot persistence rationale.

---

## 11. Risks, Limitations & Stretch Goals

### 11.1 Risks

- **External API rate limiting or gating**: REST Countries has periodically restricted its `/all` endpoint. Mitigation: always pass the `fields` parameter; cache aggressively (7-day TTL); include a small static seed of countries in the repository so the application can start cold even if the upstream is unavailable.
- **MongoDB Atlas free-tier latency**: Atlas free clusters can have cold-start delays. Mitigation: a small set of warmup queries runs on Flask startup; if cold-start ever exceeds a threshold, the application logs a warning rather than blocking the user.
- **Scope vs. time**: solo development with a fixed 4-week window. Mitigation: stretch goals are clearly separated and tackled only after the must-have feature set is verified end-to-end.

### 11.2 Limitations

- The application is read-only with respect to external services. It does not push data back to REST Countries, Wikivoyage, or any other source.
- Visa-free duration is shown for a hard-coded US passport; per-user passport support is out of scope.
- City coverage is limited to the GeoNames cities15000 dataset (~26,000 cities with population ≥ 15,000). Smaller towns will not appear in search.
- Climate scoring uses 30-year monthly normals; it does not predict actual weather for the trip dates.
- No mobile-specific layout. The pages are usable on mobile but are designed for desktop.
- No multi-language interface. All UI text is English.

### 11.3 Stretch Goals

- **Wikivoyage section extraction**: pull the "Get In," "Stay safe," "Etiquette," and "Money & costs" sections from the country's Wikivoyage page and render them as collapsible cards on the country detail page and within the Trip Brief.
- **Per-city detail page** with city-specific climate normals and Wikivoyage city pages, beyond the country-level view.
- **ICS calendar export**: in addition to Markdown, produce a `.ics` file that can be imported into Google Calendar or Apple Calendar with one event per trip stop.
- **"Best month to visit"** widget on the Dashboard, listing wishlist cities whose ideal months fall within the next 60 days.
- **City pin clustering** at low zoom levels using `Leaflet.markercluster` to keep the world map legible when the user has many entries.
