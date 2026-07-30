from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLogin, UserRegister


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, data: UserRegister) -> User:
        email = str(data.email).strip().lower()
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError

        try:
            user = self.users.create(
                email=email,
                full_name=data.full_name,
                password_hash=hash_password(data.password),
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailAlreadyRegisteredError from exc
        self.db.refresh(user)
        return user

    def login(self, data: UserLogin) -> str:
        user = self.users.get_by_email(str(data.email).strip().lower())
        if user is None or not user.is_active:
            raise InvalidCredentialsError
        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError
        return create_access_token(subject=str(user.id))
