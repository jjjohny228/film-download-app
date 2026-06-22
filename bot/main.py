import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.database.db import init_db
from bot.handlers.admin import admin_router
from bot.handlers.user import user_router
from bot.middlewares.user import UserMiddleware
from bot.services.proxy import ProxyService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def _notify_no_proxy(bot: Bot) -> None:
    """Broadcast no-proxy error to all users + alert admins."""
    from bot.database.db import run_sync
    from bot.database.models import User

    users: list[User] = await run_sync(
        lambda: list(User.select().where(User.is_banned == False))  # noqa: E712
    )
    user_msg = (
        "⚠️ Прокси временно закончились.\n"
        "Подождите — администраторы скоро добавят новые."
    )
    for user in users:
        try:
            await bot.send_message(user.tg_id, user_msg)
        except Exception:
            pass

    admin_msg = (
        "🚨 Все прокси исчерпаны!\n"
        "Добавьте новые через бот (🌐 Загрузить прокси)."
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, admin_msg)
        except Exception:
            pass


async def main() -> None:
    init_db(settings.DB_PATH)
    log.info("Database initialised at %s", settings.DB_PATH)

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    ProxyService.register_no_proxy_callback(lambda: _notify_no_proxy(bot))

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(UserMiddleware())

    # Admin router first — its filter rejects non-admins early
    dp.include_router(admin_router)
    dp.include_router(user_router)

    log.info("Starting polling…")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
