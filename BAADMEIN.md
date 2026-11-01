# Baad mein (later ideas, not in current phase)

- Login limiter is in-memory per instance; move failed-attempt counts to a DB table for a real limit on Vercel.
- Usernames are unique per shop only; add a shop code on the login screen (or make usernames global) before onboarding a second shop.
- Run the test suite against a real Postgres test database (e.g. a Neon branch) in CI, in addition to SQLite.
- Add vercel.json / Vercel entrypoint config for the backend when we reach the deploy phase.
- Split pytest/httpx into requirements-dev.txt so Vercel does not install them.
- Starlette warns that httpx is deprecated for TestClient (suggests httpx2); revisit when upgrading.
- Seed admin password change flow (owner changes own and cashier passwords from Settings).
