from app.utils.settings import get_language
from app.utils.settings import set_language as _save_language

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "search_placeholder": "Search for movies, series…",
        "search_btn": "Search",
        "search_results": "Search Results",
        "now_selecting": "NOW SELECTING",
        "dubbing_label": "Dubbing / Translation",
        "quality": "Quality",
        "season": "Season",
        "episode": "Episode",
        "season_n": "Season {n}",
        "episode_n": "Episode {n}",
        "save_to": "Save to:",
        "change": "Change",
        "download_now": "⬇  Download Now",
        "active_downloads": "ACTIVE DOWNLOADS ({n})",
        "clear_finished": "Clear Finished",
        "searching": "Searching…",
        "nothing_found": "Nothing found",
        "found": "Found: {n}",
        "loading_info": "Loading info…",
        "ready": "Ready",
        "error_msg": "Error: {msg}",
        "waiting": "WAITING",
        "downloading": "DOWNLOADING",
        "paused": "PAUSED",
        "done": "DONE",
        "cancelled": "Cancelled",
        "downloaded": "Downloaded: {name}",
        "link_error": "Link error: {msg}",
        "fetching_link": "Fetching link for {name}…",
        "select_folder": "Select download folder",
        "error": "ERROR",
    },
    "ru": {
        "search_placeholder": "Введите название фильма или сериала…",
        "search_btn": "Найти",
        "search_results": "Результаты поиска",
        "now_selecting": "ВЫБРАНО",
        "dubbing_label": "Озвучка / Перевод",
        "quality": "Качество",
        "season": "Сезон",
        "episode": "Серия",
        "season_n": "Сезон {n}",
        "episode_n": "Серия {n}",
        "save_to": "Сохранить в:",
        "change": "Изменить",
        "download_now": "⬇  Скачать",
        "active_downloads": "АКТИВНЫЕ ЗАГРУЗКИ ({n})",
        "clear_finished": "Очистить завершённые",
        "searching": "Поиск…",
        "nothing_found": "Ничего не найдено",
        "found": "Найдено: {n}",
        "loading_info": "Загрузка информации…",
        "ready": "Готово",
        "error_msg": "Ошибка: {msg}",
        "waiting": "ОЖИДАНИЕ",
        "downloading": "ЗАГРУЗКА",
        "paused": "ПАУЗА",
        "done": "ГОТОВО",
        "cancelled": "Отменено",
        "downloaded": "Скачано: {name}",
        "link_error": "Ошибка ссылки: {msg}",
        "fetching_link": "Получение ссылки для {name}…",
        "select_folder": "Выберите папку для загрузки",
        "error": "ОШИБКА",
    },
    "uk": {
        "search_placeholder": "Введіть назву фільму або серіалу…",
        "search_btn": "Знайти",
        "search_results": "Результати пошуку",
        "now_selecting": "ОБРАНО",
        "dubbing_label": "Озвучення / Переклад",
        "quality": "Якість",
        "season": "Сезон",
        "episode": "Серія",
        "season_n": "Сезон {n}",
        "episode_n": "Серія {n}",
        "save_to": "Зберегти в:",
        "change": "Змінити",
        "download_now": "⬇  Завантажити",
        "active_downloads": "АКТИВНІ ЗАВАНТАЖЕННЯ ({n})",
        "clear_finished": "Очистити завершені",
        "searching": "Пошук…",
        "nothing_found": "Нічого не знайдено",
        "found": "Знайдено: {n}",
        "loading_info": "Завантаження інформації…",
        "ready": "Готово",
        "error_msg": "Помилка: {msg}",
        "waiting": "ОЧІКУВАННЯ",
        "downloading": "ЗАВАНТАЖЕННЯ",
        "paused": "ПАУЗА",
        "done": "ГОТОВО",
        "cancelled": "Скасовано",
        "downloaded": "Завантажено: {name}",
        "link_error": "Помилка посилання: {msg}",
        "fetching_link": "Отримання посилання для {name}…",
        "select_folder": "Виберіть папку для завантаження",
        "error": "ПОМИЛКА",
    },
}

_lang: str = "en"


def init() -> None:
    global _lang
    _lang = get_language()


def set_language(lang: str) -> None:
    global _lang
    if lang in _STRINGS:
        _lang = lang
        _save_language(lang)


def current() -> str:
    return _lang


def t(key: str, **kwargs: object) -> str:
    row = _STRINGS.get(_lang, _STRINGS["en"])
    s = row.get(key, _STRINGS["en"].get(key, key))
    return s.format(**kwargs) if kwargs else s
