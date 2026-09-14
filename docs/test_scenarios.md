# Manual Test Scenarios

Execute each scenario against a fresh database. To reset:

```bash
del instance\atlas.sqlite3                # or: rm instance/atlas.sqlite3 on macOS/Linux
flask init-db
python -m scripts.load_cities
```

To reset MongoDB caches (optional, recommended for fresh runs), use `mongosh` or the Atlas UI to drop the `countries_cache`, `currency_cache`, `climate_cache`, `advisory_cache` collections.

## 1. Cold start
- Visit `/`. Expect a redirect to `/login`.
- Register a new user. Expect a redirect to an empty Dashboard with all four stats at 0.

## 2. First wishlist entry (via Browse navigation)
- Click "Browse" in the top navigation.
- Search "Reykjavik". The result row shows the city, the country full name (`Iceland`) and code (`ISL`), the population, and two actions.
- Click "View country" on the Reykjavik row. Iceland's detail page renders with currency (ISK), advisory badge, country basics, Wikivoyage travel notes (if available), and an in-page city search panel.
- In the city panel, locate Reykjavik and click "Add to wishlist" with note `summer 2026` and priority Medium.
- Visit `/wishlist`. Reykjavik appears with the note and priority.
- The dashboard count for "Wishlist cities" is now 1.

## 3. First visited entry
- On the wishlist row for Reykjavik, set "Visited on" to `2026-07-15`, optional journal `Kex Hostel`, and click "Mark visited". Flash: "Marked Reykjavik as visited."
- Visit `/visited`. The entry is listed; the wishlist row is gone.
- Open the dashboard. The map shows a green pin near Reykjavik.

## 4. Multi-stop trip
- Create a trip "Japan Spring 2027" with `start=2027-04-10` and `end=2027-04-20`.
- On the trip page, add Tokyo (arrive 04-10, depart 04-14), Kyoto (04-14 to 04-17), Osaka (04-17 to 04-20).
- Drag Kyoto above Tokyo in the itinerary. Refresh the page. The order persists.
- The Trip Brief sections render: Currency (JPY rate from Frankfurter), Languages (Japanese), Travel Advisory (Level 1 if cached), Country Basics (Timezone UTC+09:00, Drive side Left).
- Climate match for April: all three cities show Ideal or Good.

## 5. API resilience
- With Atlas running, temporarily block outbound HTTP to `restcountries.com` (firewall rule or `/etc/hosts` entry pointing it to 127.0.0.1).
- Reload an already-cached country page (e.g., `/countries/JPN`). The page renders from MongoDB cache; if cache is stale, a yellow "cached data" banner appears.
- Try a never-cached country (e.g., `/countries/TUV` if Tuvalu wasn't warmed). Expect a 404.

## 6. Markdown export
- Open the Japan trip page. Click "Export Brief (.md)".
- The file downloads as `trip_Japan_Spring_2027.md`. Open in any text editor.
- Confirm sections: Title with dates, Itinerary table, Currencies, Languages, Travel Advisories, Country Basics.

## 7. Per-user isolation
- Register a second account "bob". Verify bob's Dashboard is empty (0 wishlist, 0 visited, 0 trips, 0 countries).
- Attempt to access `/trips/<id>` of alice's trip while logged in as bob. Expect a 404.
- Confirm bob cannot see or modify alice's wishlist or visited entries.

## 8. CSRF protection
- Open browser dev tools. Inspect any POST form (e.g., wishlist add).
- Remove the hidden `csrf_token` field and submit. The request is rejected with a 400 Bad Request.

## 9. Password policy
- Attempt to register with password `short`. The form is rejected with a clear error message.
- Attempt with `abcdefgh` (no digit). The form is rejected.
- Attempt with `abc12345` (8 chars, letter + digit). The form is accepted.

## 10. Open-redirect prevention
- Manually visit `/login?next=https://evil.example/phish` while logged out, then sign in. The redirect goes to `/dashboard`, not the external URL.

## 11. Logout method enforcement
- Attempt `GET /logout` (e.g., type the URL in the browser bar). The server returns 405 Method Not Allowed; the session remains active. Only the POST form on the Dashboard can log the user out.
