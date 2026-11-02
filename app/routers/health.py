from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_health_db
from app.core.errors import AppError

router = APIRouter(tags=["health"])


@router.get("/health", summary="Check that the API and database are reachable (3 s timeout)")
def health(db: Annotated[Session, Depends(get_health_db)]) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError(
            status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable", "Database is not reachable"
        ) from exc
    return {"status": "ok", "database": "ok"}
