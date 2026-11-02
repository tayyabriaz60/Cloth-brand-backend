from fastapi import APIRouter

from app.core.deps import OwnerUser, Scope
from app.schemas.uploads import PresignIn, PresignOut
from app.services import uploads as uploads_service

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignOut, summary="Presigned R2 PUT URL (owner)")
def presign(_owner: OwnerUser, scope: Scope, body: PresignIn) -> PresignOut:
    return uploads_service.presign(scope, body)
