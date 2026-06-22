import peewee
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.db import run_sync
from bot.database.models import Proxy, User
from bot.middlewares.user import AdminFilter
from bot.services.proxy import ProxyService
from bot.states.states import AdminStates

admin_router = Router()
admin_router.message.filter(AdminFilter())


# ── Рассылка ──────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer(
        "📢 Отправьте сообщение для рассылки (текст, фото или видео).\n"
        "Для отмены — /cancel"
    )


@admin_router.message(AdminStates.waiting_broadcast)
async def do_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    users: list[User] = await run_sync(
        lambda: list(User.select().where(User.is_banned == False))  # noqa: E712
    )
    sent = 0
    failed = 0
    for user in users:
        try:
            await message.copy_to(chat_id=user.tg_id)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")


# ── Статистика ────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "📊 Статистика")
async def show_stats(message: Message) -> None:
    def _query() -> tuple:
        total_users = User.select().count()
        total_searches = User.select(peewee.fn.SUM(User.search_count)).scalar() or 0
        total_dl = User.select(peewee.fn.SUM(User.dl_count)).scalar() or 0
        active_proxies = Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
        total_proxies = Proxy.select().count()
        return total_users, total_searches, total_dl, active_proxies, total_proxies

    total_users, total_searches, total_dl, active_p, total_p = await run_sync(_query)
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔍 Поисков всего: {total_searches}\n"
        f"📥 Скачиваний всего: {total_dl}\n"
        f"🌐 Активных прокси: {active_p} / {total_p}",
        parse_mode="HTML",
    )


# ── Прокси ────────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "🌐 Загрузить прокси")
async def start_proxy_upload(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_proxy)
    await message.answer(
        "🌐 Отправьте список прокси (каждый с новой строки):\n\n"
        "<code>http 85.195.81.148:10772:login:password\n"
        "socks5 1.2.3.4:1080:user:pass</code>\n\n"
        "Для отмены — /cancel",
        parse_mode="HTML",
    )


@admin_router.message(AdminStates.waiting_proxy)
async def handle_proxy_upload(message: Message, state: FSMContext) -> None:
    await state.clear()
    lines = (message.text or "").strip().splitlines()
    added = await ProxyService.add_proxies(lines)
    await message.answer(f"✅ Добавлено прокси: {added}")


# ── /cancel ───────────────────────────────────────────────────────────────────

@admin_router.message(Command("cancel"))
async def cancel_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.")
