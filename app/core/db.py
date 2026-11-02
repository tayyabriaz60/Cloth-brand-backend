from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

# Long enough for a sleeping Neon compute to wake up, short enough to fail clearly.
CONNECT_TIMEOUT_SECONDS = 10
# /health must answer fast, even when the database is unreachable.
HEALTH_CONNECT_TIMEOUT_SECONDS = 3


def build_engine(url: str, connect_timeout: int = CONNECT_TIMEOUT_SECONDS) -> Engine:
    # NullPool: serverless functions must not keep connections open; Neon's pooler does pooling.
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout},
    )


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

health_engine = build_engine(get_settings().database_url, HEALTH_CONNECT_TIMEOUT_SECONDS)
HealthSessionLocal = sessionmaker(bind=health_engine, autoflush=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_health_db() -> Iterator[Session]:
    db = HealthSessionLocal()
    try:
        yield db
    finally:
        db.close()
