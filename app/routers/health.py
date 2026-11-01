from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.deps import DbSession
from app.core.errors import AppError

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check that the API and database are reachable")
def health(db: DbSession) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError(
            status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", "Database is not reachable"
        ) from exc
    return {"status": "ok", "database": "ok"}
