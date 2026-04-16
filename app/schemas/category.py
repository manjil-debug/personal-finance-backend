import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.category import CategoryType


class CategoryResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    parent_id: Optional[uuid.UUID]
    name: str
    type: CategoryType
    color: Optional[str]
    icon: Optional[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
