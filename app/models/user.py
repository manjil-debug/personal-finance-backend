import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AuthProvider(str, enum.Enum):
    local = "local"
    google = "google"


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_v7()"))
    email         = Column(String(255), nullable=False, unique=True, index=True)
    full_name     = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=True)
    google_id     = Column(String(255), nullable=True, unique=True)
    avatar_url    = Column(String, nullable=True)
    provider      = Column(Enum(AuthProvider), nullable=False, default=AuthProvider.local)
    is_active     = Column(Boolean, nullable=False, default=True)
    is_verified   = Column(Boolean, nullable=False, default=False)
    created_at    = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at    = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
