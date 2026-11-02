from sqlalchemy.exc import IntegrityError

from app.core.deps import ShopScope
from app.core.errors import AppError, conflict


def commit(scope: ShopScope) -> None:
    try:
        scope.db.commit()
    except IntegrityError as exc:
        scope.db.rollback()
        raise conflict() from exc
    except AppError:
        scope.db.rollback()
        raise
    except Exception:
        scope.db.rollback()
        raise
