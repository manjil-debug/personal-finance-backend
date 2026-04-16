import uuid
import datetime as dt
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class TransferCreate(BaseModel):
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal = Field(..., gt=0, description="Must be a positive value")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    date: date

    @model_validator(mode="after")
    def accounts_must_differ(self):
        if self.from_account_id == self.to_account_id:
            raise ValueError("Source and destination accounts must be different")
        return self


class TransferUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None
    date: Optional[dt.date] = None


class TransferResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    from_transaction_id: uuid.UUID
    to_transaction_id: uuid.UUID
    from_account_id: uuid.UUID
    to_account_id: uuid.UUID
    amount: Decimal
    currency: str
    description: Optional[str]
    date: date
    created_at: datetime

    model_config = {"from_attributes": True}
