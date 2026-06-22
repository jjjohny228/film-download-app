from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🔍 Найти фильм"), KeyboardButton(text="👤 Профиль")],
    ]
    if is_admin:
        rows.append([
            KeyboardButton(text="📢 Рассылка"),
            KeyboardButton(text="📊 Статистика"),
        ])
        rows.append([KeyboardButton(text="🌐 Загрузить прокси")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
