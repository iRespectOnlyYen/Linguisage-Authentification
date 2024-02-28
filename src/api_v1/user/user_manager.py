import uuid
from typing import Optional
from fastapi import Depends, Request, BackgroundTasks
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
)
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)

from fastapi_users.db import SQLAlchemyUserDatabase
from loguru import logger

from src.core import settings
from src.core.database.models import (
    User,
    db_user_dependency,
    AccessToken,
    db_access_token_dependency,
)
from src.email.confirm_account.mail import sand_confirm_email


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.auth.RESET_PASSWORD_SECRET
    verification_token_secret = settings.auth.VERIFICATION_TOKEN_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        logger.info(await self.request_verify(user))

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        pass

    async def on_after_request_verify(
        self,
        user: User,
        token: str,
        request: Optional[Request] = None,
    ):
        sand_confirm_email(user.email, f"{settings.protocol}://linguisage/auth?token={token}")
        print(f"sent to: {settings.protocol}://linguisage/auth?token={token}")


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(db_user_dependency),
):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(db_access_token_dependency),
) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=60 * 60 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_database_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user_dependency = fastapi_users.current_user(active=True, verified=True)
