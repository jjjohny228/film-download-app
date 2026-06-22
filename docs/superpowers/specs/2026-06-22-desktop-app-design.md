# DownloadFilm Desktop — Design Spec

**Date:** 2026-06-22  
**Status:** Approved

## Overview

Десктопное приложение для Windows и macOS. Пользователь ищет фильм или сериал на HdRezka, выбирает перевод/качество/(сезон/серию для сериалов), приложение скачивает файл на компьютер.

Никакого Telegram, никаких прокси, никакой админки.

## Stack

| Компонент | Решение |
|-----------|---------|
| UI | PySide6 |
| Парсинг HdRezka | HdRezkaApi |
| HTTP-скачивание | httpx (streaming) |
| Настройки | QSettings |
| Packaging | PyInstaller |

## Architecture

```
app/
├── main.py                  # QApplication, запуск MainWindow
├── ui/
│   ├── main_window.py       # главное окно, компоновка панелей
│   ├── search_panel.py      # строка поиска, список результатов
│   ├── detail_panel.py      # переводы, сезон, серия, качество, кнопка скачать
│   └── download_panel.py    # таблица загрузок с прогресс-барами
├── core/
│   ├── rezka.py             # обёртка HdRezkaApi: search, get_stream_url
│   └── downloader.py        # DownloadWorker(QThread): скачивание + прогресс
└── utils/
    └── settings.py          # сохранение папки загрузки через QSettings
```

## UI Layout

```
┌─────────────────────────────────────────────────────┐
│  [🔍 Поиск фильма...              ] [Найти]          │
├──────────────────────┬──────────────────────────────┤
│ Результаты:          │ Перевод: [Дублированный ▼]   │
│                      │                              │
│ 🎬 Название (2023)   │ Сезон:  [1 ▼]  Серия: [3 ▼] │
│ 🎬 Название 2 (2021) │ (только для сериалов)        │
│ ...                  │                              │
│                      │ Качество: [480p][720p][1080p]│
│                      │                              │
│                      │ Папка: /Downloads [Изменить] │
│                      │                              │
│                      │        [▼ Скачать]           │
├──────────────────────┴──────────────────────────────┤
│ Загрузки:                                           │
│ Название.mp4  ████████░░  72%  3.2 MB/s  ETA 00:45 │
│ Другой.mp4   ██░░░░░░░░  18%  1.1 MB/s  ETA 03:20 │
└─────────────────────────────────────────────────────┘
```

## Threading Model

- **Главный поток** — UI, только отрисовка
- **SearchWorker(QThread)** — вызов HdRezkaApi.search(), результат через сигнал `results_ready`
- **DownloadWorker(QThread)** — httpx streaming, сигналы `progress(int, int)` и `finished(str)`
- Несколько DownloadWorker могут работать параллельно (очередь)

## Core Logic

### rezka.py

```python
# search(query: str) -> list[SearchResult]
# get_translators(film_id) -> list[Translator]
# get_seasons(film_id, translator_id) -> dict[int, list[int]]
# get_stream_url(film_id, translator_id, quality, season?, episode?) -> str
```

### downloader.py

```python
class DownloadWorker(QThread):
    progress = Signal(int, int)   # downloaded_bytes, total_bytes
    finished = Signal(str)        # filepath
    error = Signal(str)           # error message

    # Скачивает через httpx с chunk_size=1MB
    # Сохраняет в save_dir / filename
```

## Settings

Хранятся через QSettings (OS-нативно: реестр на Windows, plist на Mac):
- `download_folder` — папка сохранения (default: ~/Downloads)

## Packaging

```bash
# Windows
pyinstaller --onefile --windowed --name DownloadFilm app/main.py

# Mac
pyinstaller --onefile --windowed --name DownloadFilm app/main.py
# + hdiutil для .dmg
```

## What's Removed

- Весь код `bot/` (aiogram, handlers, middlewares, keyboards, FSM)
- SQLite база данных
- Прокси-система
- Telegram Bot Token
- Админ-панель

## Success Criteria

1. Поиск фильма возвращает результаты за < 5с
2. Выбор сезона/серии для сериала работает корректно
3. Файл скачивается с прогресс-баром в реальном времени
4. Приложение собирается в один файл на Windows и Mac
5. Папка сохранения запоминается между запусками
