from sqlalchemy import Column, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    from_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    to_transaction_id   = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    created_at          = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
