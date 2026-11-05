# Baad mein (later ideas, not in current phase)

- Database-backed login rate limit: store failed attempts in a table so the limit holds across Vercel instances (current limiter is in-memory per instance).
- Composite foreign keys for cross-shop integrity, e.g. bill_items (shop_id, product_id) -> products (shop_id, id), so a row can never point at another shop's data.
- Run the test suite against a real Postgres test database (e.g. a Neon branch) in CI, in addition to SQLite.
- Starlette warns that httpx is deprecated for TestClient (suggests httpx2); revisit when upgrading.
- I2 thaan/roll records (nullable roll_id on stock_movements, sale picks a roll or FIFO) only if the shopkeeper tracks each thaan.
- List endpoints have no limit/offset pagination yet.
- Asia/Karachi is a fixed UTC+5 offset (Pakistan has no DST); switch to zoneinfo+tzdata if DST ever returns.
- R2 upload size is not enforced on the server (browser only).
