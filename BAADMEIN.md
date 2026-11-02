# Baad mein (later ideas, not in current phase)

- Database-backed login rate limit: store failed attempts in a table so the limit holds across Vercel instances (current limiter is in-memory per instance).
- Composite foreign keys for cross-shop integrity, e.g. bill_items (shop_id, product_id) -> products (shop_id, id), so a row can never point at another shop's data.
- Run the test suite against a real Postgres test database (e.g. a Neon branch) in CI, in addition to SQLite.
- Starlette warns that httpx is deprecated for TestClient (suggests httpx2); revisit when upgrading.
- Seed admin password change flow (owner changes own and cashier passwords from Settings).
