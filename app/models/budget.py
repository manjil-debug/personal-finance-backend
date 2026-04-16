import enum
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class BudgetPeriod(str, enum.Enum):
    weekly  = "weekly"
    monthly = "monthly"
    yearly  = "yearly"


class Budget(Base):
    __tablename__ = "budgets"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name        = Column(String(100), nullable=False)
    amount      = Column(Numeric(18, 2), nullable=False)
    period      = Column(Enum(BudgetPeriod, name="budget_period"), nullable=False, default=BudgetPeriod.monthly)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=True)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at  = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
