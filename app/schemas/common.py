from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.core.money import qty_str

QtyOut = Annotated[Decimal, PlainSerializer(lambda v: qty_str(v), return_type=str)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
