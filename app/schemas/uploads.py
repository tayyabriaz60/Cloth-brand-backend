from uuid import UUID

from pydantic import Field

from app.core.constants import ALLOWED_IMAGE_TYPES
from app.schemas.common import ORMModel


class PresignIn(ORMModel):
    content_type: str = Field(examples=list(ALLOWED_IMAGE_TYPES))
    product_id: UUID


class PresignOut(ORMModel):
    upload_url: str
    key: str
    public_url: str
