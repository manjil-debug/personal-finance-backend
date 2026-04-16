from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, AuthProvider
from app.schemas.user import SignupRequest


def signup_user(payload: SignupRequest, db: Session) -> User:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        provider=AuthProvider.local,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
