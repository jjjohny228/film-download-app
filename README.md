# MovieDownloader

Десктопное приложение для поиска и скачивания фильмов/сериалов с HdRezka.

## Стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ |
| PySide6 | UI фреймворк |
| HdRezkaApi | 11.x |
| httpx | HTTP-клиент |
| uv | пакетный менеджер |
| ruff | линтер |

## Быстрый старт

```bash
# 1. Клонировать репо
git clone <repo> && cd DownloadFilmBot

# 2. Установить зависимости
uv sync

# 3. Запустить
uv run python -m app.main
```

## Разработка

```bash
# Линтинг (проверка)
uv run ruff check app/ tests/

# Линтинг (автофикс)
uv run ruff check app/ tests/ --fix

# Тесты
uv run pytest

# Тесты с подробным выводом
uv run pytest -v
```

## Сборка дистрибутива

### Исполняемый файл (Windows / macOS)

```bash
uv run pyinstaller download_film.spec
```

Результат:
- macOS → `dist/MovieDownloader.app`
- Windows → `dist/MovieDownloader.exe`

### DMG-образ для macOS

После успешной сборки `.app`:

```bash
# Установить create-dmg (однократно)
brew install create-dmg

# Собрать DMG
create-dmg \
  --volname "MovieDownloader" \
  --volicon "icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "MovieDownloader.app" 175 190 \
  --hide-extension "MovieDownloader.app" \
  --app-drop-link 425 190 \
  "MovieDownloader.dmg" \
  "dist/MovieDownloader.app"
```

Либо через встроенный `hdiutil` без сторонних зависимостей:

```bash
# Создать временную папку для содержимого образа
mkdir -p dmg_staging
cp -r dist/MovieDownloader.app dmg_staging/

# Создать DMG
hdiutil create \
  -volname "MovieDownloader" \
  -srcfolder dmg_staging \
  -ov -format UDZO \
  MovieDownloader.dmg

# Убрать временную папку
rm -rf dmg_staging
```

## Структура проекта

```
DownloadFilmBot/
├── app/
│   ├── main.py              # точка входа
│   ├── i18n.py              # интернационализация (en/ru/uk)
│   ├── ui/
│   │   ├── main_window.py   # главное окно
│   │   ├── search_panel.py  # поиск фильмов
│   │   ├── detail_panel.py  # детали / выбор качества
│   │   └── download_panel.py# очередь загрузок
│   └── utils/
│       └── settings.py      # обёртка QSettings
├── tests/
├── download_film.spec       # конфиг PyInstaller
├── pyproject.toml
└── README.md
```
