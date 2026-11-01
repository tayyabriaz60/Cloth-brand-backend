from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

POSTGRES_PREFIX = "postgresql"
# Long enough for a sleeping Neon compute to wake up, short enough to fail clearly.
CONNECT_TIMEOUT_SECONDS = 10


def build_engine(url: str) -> Engine:
    if not url.startswith(POSTGRES_PREFIX):
        raise ValueError("Only Postgres URLs are supported (postgresql+psycopg://...)")
    # NullPool: serverless functions must not keep connections open; Neon's pooler does pooling.
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
