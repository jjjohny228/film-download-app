from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def carousel_kb(idx: int, total: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀", callback_data="nav:prev"),
            InlineKeyboardButton(text=f"{idx}/{total}", callback_data="nav:noop"),
            InlineKeyboardButton(text="▶", callback_data="nav:next"),
        ],
        [InlineKeyboardButton(text="🎬 Скачать", callback_data="dl_start")],
    ])


def translators_kb(translators: dict[str, str]) -> InlineKeyboardMarkup:
    """translators: {name: id_str}"""
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"tr:{idx}")]
        for idx, name in enumerate(translators.keys())
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quality_kb() -> InlineKeyboardMarkup:
    qualities = ["480p", "720p", "1080p"]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=q, callback_data=f"q:{q}") for q in qualities]
    ])


def seasons_kb(seasons: dict[int, list[int]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for season_num in sorted(seasons.keys()):
        row.append(InlineKeyboardButton(
            text=f"Сезон {season_num}", callback_data=f"s:{season_num}"
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def episodes_kb(episodes: list[int], season: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for ep in sorted(episodes):
        row.append(InlineKeyboardButton(
            text=str(ep), callback_data=f"ep:{season}:{ep}"
        ))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
