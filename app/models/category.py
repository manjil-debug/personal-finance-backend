import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class CategoryType(str, enum.Enum):
    income  = "income"
    expense = "expense"


class Category(Base):
    __tablename__ = "categories"

    id         = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    parent_id  = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name       = Column(String(100), nullable=False)
    type       = Column(Enum(CategoryType, name="category_type"), nullable=False)
    color      = Column(String(7), nullable=True)
    icon       = Column(String(50), nullable=True)
    is_system  = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
