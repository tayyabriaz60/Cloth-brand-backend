# Cloth POS — Backend

FastAPI + SQLAlchemy 2 + Alembic on Neon Postgres. Built to run on Vercel (serverless).

## Install

Requires Python 3.12+ (Windows PowerShell shown; on macOS/Linux use `source .venv/bin/activate`).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

- `requirements.txt`: runtime packages only (this is what Vercel installs).
- `requirements-dev.txt`: runtime + `pytest` and `httpx`, for your laptop.

Copy `.env.example` to `.env` and fill in real values by hand. Never commit `.env`.
If a variable is wrong, the app refuses to start and says which variable and rule failed
(for example `JWT_SECRET must be at least 32 characters`), never the value.

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | Neon **pooled** URL (host contains `-pooler`); must start with `postgresql+psycopg://` |
| `DATABASE_URL_DIRECT` | no | Neon **direct** URL, used only by Alembic; same prefix rule |
| `JWT_SECRET` | yes | 32+ random characters |
| `JWT_EXPIRE_MINUTES` | no | default 720 |
| `FRONTEND_URL` | no | comma-separated allowed origins, no `*` |
| `R2_*` | no | the app starts without them; empty or `PASTE...` values count as not set |

## Database

Migrations are never run at app startup. Run them from your laptop:

```powershell
alembic upgrade head
```

Load demo data (safe to run twice):

```powershell
python -m scripts.seed
```

Demo logins: `owner` / `owner123` (display name Demo Owner) and
`cashier` / `cashier123` (Demo Cashier). **Change these before real use.**

```powershell
python -m scripts.set_password owner
```

The script asks for the new password twice (nothing is echoed). Min 10 characters.

Full HTTP contract for the frontend: [`docs/API.md`](docs/API.md). Interactive docs: `/docs`.

Usernames are unique across all shops and stored lower-case; login ignores case and
surrounding spaces.

## Run

```powershell
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/docs
- Health (pings the database, gives up after 3 s): http://localhost:8000/health

## Test

```powershell
pytest
```

Tests use an in-memory SQLite database and override `DATABASE_URL`, so they never touch Neon.

## Deploy (Vercel, from the dashboard)

Vercel finds `app` in `app/main.py` automatically and installs `requirements.txt` (runtime
packages only). `.python-version` pins Python 3.12 and `vercel.json` keeps tests, migrations,
scripts and `requirements-dev.txt` out of the bundle.

If the deploy shows `500 FUNCTION_INVOCATION_FAILED`, open the project's Runtime Logs: a bad
environment variable appears there as `Invalid configuration: <VARIABLE> <rule>`.

1. Run `alembic upgrade head` and `python -m scripts.seed` from your laptop against Neon first.
2. Vercel dashboard: Add New → Project → import `Cloth-brand-backend`. Framework: FastAPI.
3. Add environment variables: `DATABASE_URL` (pooled URL), `JWT_SECRET` (a new random value),
   `JWT_EXPIRE_MINUTES`, `FRONTEND_URL`. `DATABASE_URL_DIRECT` and `R2_*` are not needed yet.
4. Deploy. Open `https://<project>.vercel.app/health`, then `/docs`.

The first request after idle time can take a few seconds (Vercel and Neon wake up).

## Layout

```
app/
  main.py        FastAPI app (CORS, error handlers, routers)
  core/          config, db, security (bcrypt + JWT), deps (auth + ShopScope), errors, rate_limit
  models/        SQLAlchemy models (money = Integer rupees, quantity = Numeric(10,2))
  schemas/       Pydantic request/response models
  routers/       thin HTTP layer
  services/      business logic
alembic/         migrations
scripts/seed.py  demo data
tests/           pytest
```

Errors always look like `{"code": "...", "message": "..."}`.
