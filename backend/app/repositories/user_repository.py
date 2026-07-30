import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.lower())
        return self.db.scalar(statement)

    def create(self, *, email: str, full_name: str | None, password_hash: str) -> User:
        user = User(email=email, full_name=full_name, password_hash=password_hash)
        self.db.add(user)
        self.db.flush()
        return user
