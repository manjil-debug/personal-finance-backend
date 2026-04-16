import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AccountType(str, enum.Enum):
    checking    = "checking"
    savings     = "savings"
    credit_card = "credit_card"
    cash        = "cash"
    investment  = "investment"
    loan        = "loan"
    other       = "other"


class Account(Base):
    __tablename__ = "accounts"

    id         = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(100), nullable=False)
    type       = Column(Enum(AccountType), nullable=False)
    balance    = Column(Numeric(18, 2), nullable=False)
    currency   = Column(String(3), nullable=False, default="USD")
    color      = Column(String(7), nullable=True)
    icon       = Column(String(50), nullable=True)
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
