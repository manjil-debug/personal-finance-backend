import enum
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TransactionType(str, enum.Enum):
    income   = "income"
    expense  = "expense"
    transfer = "transfer"


class Transaction(Base):
    __tablename__ = "transactions"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id  = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    type        = Column(Enum(TransactionType), nullable=False)
    amount      = Column(Numeric(18, 2), nullable=False)
    currency    = Column(String(3), nullable=False, default="USD")
    description = Column(String(255), nullable=False)
    notes       = Column(Text, nullable=True)
    date        = Column(Date, nullable=False)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at  = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
