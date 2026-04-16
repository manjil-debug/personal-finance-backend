import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id:  uuid.UUID
    category_id: Optional[uuid.UUID] = None
    type:        TransactionType
    amount:      Decimal = Field(..., gt=0, description="Must be a positive value")
    currency:    str = Field(default="USD", min_length=3, max_length=3)
    description: str = Field(..., min_length=1, max_length=255)
    notes:       Optional[str] = None
    date:        date


class TransactionResponse(BaseModel):
    id:          uuid.UUID
    user_id:     uuid.UUID
    account_id:  uuid.UUID
    category_id: Optional[uuid.UUID]
    type:        TransactionType
    amount:      Decimal
    currency:    str
    description: str
    notes:       Optional[str]
    date:        date
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}
