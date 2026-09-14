# How a trip request works

## Creating a trip

1. The form in `atlas/templates/trips/list.html` sends a name, dates, and CSRF token.
2. The login decorator in `atlas/auth.py` loads the session's user.
3. `atlas/routes/trips.py` validates the input and passes the current user's ID to the repository. The browser does not choose the owner.
4. `atlas/repos/trips.py` writes the trip through a parameterized SQL query.
5. The route redirects to the brief, where `atlas/services/trip_brief.py` combines stops with cached travel data.

## Why two stores?

Accounts and itineraries have relationships and belong in SQLite. External responses are document-shaped and can be refreshed independently, so they live in MongoDB. This was a useful capstone exercise, although one database would reduce operational work for a small deployment.

## Authentication, CSRF, and ownership

Authentication identifies the current account. CSRF protection rejects modifying requests without the session's token. Ownership checks decide which trip the account may read or change. A valid token does not grant access to another user's trip.

Stop mutations include both stop ID and trip ID. This prevents a stop from a different trip being changed through an owned trip URL. `tests/test_trip_security.py` exercises these boundaries and checks the resulting database state.

## Testing the cache

`tests/conftest.py` supplies an empty MongoDB substitute for each test and a temporary SQLite file. Service tests insert reference data, choose a cache timestamp, and provide the upstream HTTP response. That makes cache hits, refreshes, and fallback behavior repeatable.

For example, the advisory refresh needs country-name mappings as well as RSS input. The test supplies both. A real MongoDB server and current upstream APIs still need separate integration checks.
