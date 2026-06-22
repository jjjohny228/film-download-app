from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.filters import Filter
from aiogram.types import Message, TelegramObject, Update

from bot.config import settings
from bot.database.db import run_sync
from bot.database.models import User


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Update) and event.message and event.message.from_user:
            user = await run_sync(self._get_or_create, event.message.from_user)
            data["db_user"] = user
        return await handler(event, data)

    @staticmethod
    def _get_or_create(tg_user) -> User:
        user, _ = User.get_or_create(
            tg_id=tg_user.id,
            defaults={
                "username": tg_user.username,
                "full_name": tg_user.full_name,
            },
        )
        if user.full_name != tg_user.full_name or user.username != tg_user.username:
            user.full_name = tg_user.full_name
            user.username = tg_user.username
            user.save()
        return user


class AdminFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        return (
            message.from_user is not None
            and message.from_user.id in settings.admin_ids
        )
