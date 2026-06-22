from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from bot.config import settings
from bot.database.db import run_sync
from bot.database.models import User
from bot.keyboards.inline import (
    carousel_kb,
    episodes_kb,
    quality_kb,
    seasons_kb,
    translators_kb,
)
from bot.keyboards.reply import main_menu_kb
from bot.services.proxy import NoProxyAvailable
from bot.services.rezka import FilmInfo, RezkaService, SearchResult
from bot.states.states import SearchStates

user_router = Router()

_search_cache: dict[int, list[SearchResult]] = {}
_film_info_cache: dict[str, FilmInfo] = {}

_rezka: RezkaService | None = None


def get_rezka() -> RezkaService:
    global _rezka
    if _rezka is None:
        _rezka = RezkaService(settings.REZKA_URL)
    return _rezka


# ── /start ───────────────────────────────────────────────────────────────────

@user_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    is_admin = message.from_user.id in settings.admin_ids
    await message.answer(
        "👋 Привет! Я помогу найти фильм и получить ссылку для скачивания.",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )


# ── Профиль ──────────────────────────────────────────────────────────────────

@user_router.message(F.text == "👤 Профиль")
async def show_profile(message: Message) -> None:
    user: User = await run_sync(
        lambda: User.get(User.tg_id == message.from_user.id)
    )
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user.tg_id}</code>\n"
        f"📛 Имя: {user.full_name}\n"
        f"📅 Дата регистрации: {user.joined_at.strftime('%d.%m.%Y')}\n"
        f"🔍 Поисков: {user.search_count}\n"
        f"📥 Скачиваний: {user.dl_count}",
        parse_mode="HTML",
    )


# ── Поиск ─────────────────────────────────────────────────────────────────────

@user_router.message(F.text == "🔍 Найти фильм")
async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_title)
    await message.answer("🔎 Введите название фильма или сериала:")


@user_router.message(SearchStates.waiting_title)
async def handle_search_query(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Пожалуйста, введите название.")
        return

    await message.answer("⏳ Ищу...")

    await run_sync(
        lambda: User.update(search_count=User.search_count + 1)
        .where(User.tg_id == message.from_user.id)
        .execute()
    )

    try:
        results = await get_rezka().search(query)
    except NoProxyAvailable:
        await state.clear()
        await message.answer(
            "⚠️ Прокси временно закончились.\n"
            "Подождите — администраторы скоро добавят новые."
        )
        return
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ Ошибка поиска: {e}")
        return

    if not results:
        await state.clear()
        await message.answer("😔 Ничего не найдено. Попробуйте другой запрос.")
        return

    uid = message.from_user.id
    _search_cache[uid] = results
    await state.set_state(SearchStates.browsing_results)
    await state.update_data(idx=0)
    await _send_carousel(message, results, idx=0)


async def _send_carousel(
    message: Message, results: list[SearchResult], idx: int
) -> None:
    r = results[idx]
    caption = f"🎬 <b>{r.name}</b>"
    if r.year:
        caption += f"\n📅 {r.year}"
    if r.type_:
        caption += f"  |  🎭 {r.type_}"
    kb = carousel_kb(idx + 1, len(results))

    if r.poster:
        await message.answer_photo(
            photo=r.poster, caption=caption, reply_markup=kb, parse_mode="HTML"
        )
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


# ── Карусель: навигация ───────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("nav:"), SearchStates.browsing_results)
async def carousel_navigate(call: CallbackQuery, state: FSMContext) -> None:
    direction = call.data.split(":")[1]
    if direction == "noop":
        await call.answer()
        return

    data = await state.get_data()
    idx: int = data.get("idx", 0)
    uid = call.from_user.id
    results = _search_cache.get(uid, [])

    if not results:
        await call.answer("Сессия истекла. Начните поиск заново.")
        return

    idx = (idx - 1) % len(results) if direction == "prev" else (idx + 1) % len(results)
    await state.update_data(idx=idx)

    r = results[idx]
    caption = f"🎬 <b>{r.name}</b>"
    if r.year:
        caption += f"\n📅 {r.year}"
    if r.type_:
        caption += f"  |  🎭 {r.type_}"
    kb = carousel_kb(idx + 1, len(results))

    try:
        if r.poster:
            await call.message.edit_media(
                media=InputMediaPhoto(media=r.poster, caption=caption, parse_mode="HTML"),
                reply_markup=kb,
            )
        else:
            await call.message.edit_caption(
                caption=caption, reply_markup=kb, parse_mode="HTML"
            )
    except Exception:
        pass
    await call.answer()


# ── Скачать: старт ────────────────────────────────────────────────────────────

@user_router.callback_query(F.data == "dl_start", SearchStates.browsing_results)
async def dl_start(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx: int = data.get("idx", 0)
    uid = call.from_user.id
    results = _search_cache.get(uid, [])

    if not results:
        await call.answer("Сессия истекла.")
        return

    film_url = results[idx].url
    await call.answer("⏳ Загружаю информацию...")

    try:
        info = await get_rezka().get_film_info(film_url)
        _film_info_cache[film_url] = info
    except NoProxyAvailable:
        await call.message.answer(
            "⚠️ Прокси временно закончились.\n"
            "Подождите — администраторы скоро добавят новые."
        )
        return
    except Exception as e:
        await call.message.answer(f"❌ Ошибка загрузки: {e}")
        return

    await state.update_data(film_url=film_url)

    if info.translators:
        await state.set_state(SearchStates.selecting_translation)
        await call.message.answer(
            "🌐 Выберите перевод:", reply_markup=translators_kb(info.translators)
        )
    else:
        await state.update_data(translation="")
        if info.is_series and info.seasons:
            await state.set_state(SearchStates.selecting_season)
            await call.message.answer(
                "📺 Выберите сезон:", reply_markup=seasons_kb(info.seasons)
            )
        else:
            await state.set_state(SearchStates.selecting_quality)
            await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор перевода ────────────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("tr:"), SearchStates.selecting_translation)
async def select_translation(call: CallbackQuery, state: FSMContext) -> None:
    idx = int(call.data.split(":")[1])
    data = await state.get_data()
    film_url: str = data["film_url"]
    info = _film_info_cache.get(film_url)

    if info is None:
        await call.answer("Сессия истекла.")
        return

    translation = list(info.translators.keys())[idx]
    await state.update_data(translation=translation)
    await call.answer(translation)

    if info.is_series:
        if not info.seasons:
            try:
                fresh = await get_rezka().get_film_info(film_url)
                _film_info_cache[film_url] = fresh
                info = fresh
            except Exception:
                pass

        if info.seasons:
            await state.set_state(SearchStates.selecting_season)
            await call.message.answer(
                "📺 Выберите сезон:", reply_markup=seasons_kb(info.seasons)
            )
        else:
            await state.set_state(SearchStates.selecting_quality)
            await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())
    else:
        await state.set_state(SearchStates.selecting_quality)
        await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор сезона ──────────────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("s:"), SearchStates.selecting_season)
async def select_season(call: CallbackQuery, state: FSMContext) -> None:
    season = int(call.data.split(":")[1])
    data = await state.get_data()
    film_url: str = data["film_url"]
    info = _film_info_cache.get(film_url)

    if info is None or season not in info.seasons:
        await call.answer("Сезон недоступен.")
        return

    await state.update_data(season=season)
    await call.answer(f"Сезон {season}")
    await state.set_state(SearchStates.selecting_episode)
    await call.message.answer(
        f"📺 Сезон {season} — выберите серию:",
        reply_markup=episodes_kb(info.seasons[season], season),
    )


# ── Выбор серии ───────────────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("ep:"), SearchStates.selecting_episode)
async def select_episode(call: CallbackQuery, state: FSMContext) -> None:
    _, season_s, ep_s = call.data.split(":")
    await state.update_data(season=int(season_s), episode=int(ep_s))
    await call.answer(f"Серия {ep_s}")
    await state.set_state(SearchStates.selecting_quality)
    await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор качества + ссылка ───────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("q:"), SearchStates.selecting_quality)
async def select_quality(call: CallbackQuery, state: FSMContext) -> None:
    quality = call.data.split(":")[1]
    data = await state.get_data()
    film_url: str = data["film_url"]
    translation: str = data.get("translation", "")
    season: int = data.get("season", 0)
    episode: int = data.get("episode", 0)

    await call.answer("⏳ Получаю ссылку...")

    try:
        url = await get_rezka().get_stream_url(
            url=film_url,
            translation=translation,
            quality=quality,
            season=season,
            episode=episode,
        )
    except NoProxyAvailable:
        await call.message.answer(
            "⚠️ Прокси временно закончились.\n"
            "Подождите — администраторы скоро добавят новые."
        )
        await state.clear()
        return
    except Exception as e:
        await call.message.answer(f"❌ Не удалось получить ссылку: {e}")
        await state.clear()
        return

    await run_sync(
        lambda: User.update(dl_count=User.dl_count + 1)
        .where(User.tg_id == call.from_user.id)
        .execute()
    )

    info = _film_info_cache.get(film_url)
    title = info.name if info else "Фильм"
    episode_str = f" | С{season}Е{episode}" if season and episode else ""

    await call.message.answer(
        f"✅ <b>{title}</b>{episode_str} [{quality}]\n\n"
        f"🔗 <a href='{url}'>Ссылка для скачивания</a>\n\n"
        f"<i>Ссылка временная — скачайте сразу.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await state.clear()
