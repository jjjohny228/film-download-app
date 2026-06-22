# DownloadFilm Desktop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Полностью заменить Telegram-бот на десктопное PySide6-приложение для поиска и скачивания фильмов/сериалов с HdRezka.

**Architecture:** Три слоя — `core/` (бизнес-логика, синхронный Python, запускается в QThread), `ui/` (PySide6-виджеты, только отрисовка), `utils/` (QSettings). Сигналы Qt соединяют слои.

**Tech Stack:** Python 3.11+, PySide6, HdRezkaApi 11.x, httpx, PyInstaller, uv, pytest, pytest-qt

## Global Constraints

- Python >= 3.11
- PySide6 (не PyQt6)
- HdRezkaApi >= 11.0.0 (уже в зависимостях)
- httpx для скачивания (заменяет aiohttp — нет asyncio в UI)
- Никаких прокси, никакой БД, никакого Telegram
- `uv run pytest` должен работать
- Папка `bot/` полностью удаляется

---

## File Map

| Путь | Роль |
|------|------|
| `app/main.py` | Точка входа, QApplication |
| `app/ui/main_window.py` | Главное окно, компоновка панелей |
| `app/ui/search_panel.py` | Строка поиска + список результатов |
| `app/ui/detail_panel.py` | Переводы, сезон/серия, качество, кнопка скачать |
| `app/ui/download_panel.py` | Таблица загрузок с прогресс-барами |
| `app/core/rezka.py` | Синхронная обёртка HdRezkaApi |
| `app/core/downloader.py` | DownloadWorker(QThread) |
| `app/utils/settings.py` | QSettings обёртка |
| `tests/test_rezka.py` | Тесты core/rezka.py (с mock) |
| `tests/test_downloader.py` | Тесты DownloadWorker |
| `tests/test_settings.py` | Тесты settings |
| `pyproject.toml` | Обновлённые зависимости |
| `download_film.spec` | PyInstaller spec |

---

### Task 1: Project setup — зависимости, структура, удаление bot/

**Files:**
- Modify: `pyproject.toml`
- Create: `app/__init__.py`, `app/core/__init__.py`, `app/ui/__init__.py`, `app/utils/__init__.py`
- Delete: `bot/` (весь каталог), `main.py`, `data/bot.db`

- [ ] **Step 1: Обновить pyproject.toml**

```toml
[project]
name = "download-film"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "PySide6>=6.7.0",
    "hdrezkaapi>=11.0.0",
    "httpx>=0.27.0",
]

[dependency-groups]
dev = [
    "ruff>=0.4.0",
    "pytest>=8.0.0",
    "pytest-qt>=4.4.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Создать структуру каталогов**

```bash
mkdir -p app/core app/ui app/utils
touch app/__init__.py app/core/__init__.py app/ui/__init__.py app/utils/__init__.py
```

- [ ] **Step 3: Удалить bot/, main.py, data/**

```bash
rm -rf bot/ main.py data/
```

- [ ] **Step 4: Установить зависимости**

```bash
uv sync
```

- [ ] **Step 5: Убедиться что PySide6 импортируется**

```bash
uv run python -c "from PySide6.QtWidgets import QApplication; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: replace bot project with desktop app scaffold"
```

---

### Task 2: core/rezka.py — обёртка HdRezkaApi

**Files:**
- Create: `app/core/rezka.py`
- Create: `tests/test_rezka.py`

**Interfaces:**
- Produces:
  - `SearchResult(title: str, url: str, year: str, is_series: bool)`
  - `FilmInfo(name: str, is_series: bool, translators: dict[str, str], seasons: dict[int, list[int]])`
  - `search(query: str, base_url: str) -> list[SearchResult]`
  - `get_film_info(url: str) -> FilmInfo`
  - `get_stream_url(url: str, translator_id: str, quality: str, season: int, episode: int) -> str`
  - `DEFAULT_URL: str = "https://hdrezka.ag"`

- [ ] **Step 1: Написать тесты (они падут — модуль не создан)**

Создать `tests/test_rezka.py`:

```python
from unittest.mock import MagicMock, patch

from app.core.rezka import (
    DEFAULT_URL,
    FilmInfo,
    SearchResult,
    get_film_info,
    get_stream_url,
    search,
)


def _make_search_item(title="Inception", url="https://hdrezka.ag/films/1/"):
    item = MagicMock()
    item.__getitem__ = lambda self, k: {
        "title": title,
        "url": url,
        "year": "2010",
        "category": "Фильмы",
    }[k]
    item.get = lambda k, d=None: {
        "title": title,
        "url": url,
        "year": "2010",
        "category": "Фильмы",
    }.get(k, d)
    return item


def test_search_returns_list():
    mock_page = [_make_search_item()]
    mock_results = MagicMock()
    mock_results.get_page.return_value = mock_page

    mock_searcher_instance = MagicMock(return_value=mock_results)

    with patch("app.core.rezka.HdRezkaSearch", return_value=mock_searcher_instance):
        results = search("Inception", base_url=DEFAULT_URL)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "Inception"


def test_search_empty_returns_empty_list():
    mock_results = MagicMock()
    mock_results.get_page.return_value = []
    mock_searcher_instance = MagicMock(return_value=mock_results)

    with patch("app.core.rezka.HdRezkaSearch", return_value=mock_searcher_instance):
        results = search("xyzxyz_not_found", base_url=DEFAULT_URL)

    assert results == []


def test_get_film_info_movie():
    from HdRezkaApi import Film

    mock_film = MagicMock()
    mock_film.name = "Inception"
    mock_film.type = Film
    mock_film.translators = {1: {"name": "Дублированный", "premium": False}}
    mock_film.thumbnail = "https://example.com/poster.jpg"

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        info = get_film_info("https://hdrezka.ag/films/1/")

    assert isinstance(info, FilmInfo)
    assert info.name == "Inception"
    assert info.is_series is False
    assert "Дублированный" in info.translators
    assert info.seasons == {}


def test_get_film_info_series():
    from HdRezkaApi import TVSeries

    mock_film = MagicMock()
    mock_film.name = "Breaking Bad"
    mock_film.type = TVSeries
    mock_film.translators = {1: {"name": "Дублированный", "premium": False}}
    mock_film.thumbnail = "https://example.com/poster.jpg"
    mock_film.seriesInfo = {
        "1": {
            "seasons": {"1": "Season 1", "2": "Season 2"},
            "episodes": {
                "1": {"1": "E1", "2": "E2"},
                "2": {"1": "E1"},
            },
        }
    }

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        info = get_film_info("https://hdrezka.ag/series/1/")

    assert info.is_series is True
    assert 1 in info.seasons
    assert info.seasons[1] == [1, 2]
    assert info.seasons[2] == [1]


def test_get_stream_url_movie():
    mock_stream = MagicMock()
    mock_stream.return_value = ["https://cdn.example.com/video.mp4"]

    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        url = get_stream_url(
            "https://hdrezka.ag/films/1/",
            translator_id="1",
            quality="1080p",
            season=0,
            episode=0,
        )

    assert url == "https://cdn.example.com/video.mp4"
    mock_film.getStream.assert_called_once_with(translation="1")


def test_get_stream_url_series_episode():
    mock_stream = MagicMock()
    mock_stream.return_value = ["https://cdn.example.com/s01e01.mp4"]

    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        url = get_stream_url(
            "https://hdrezka.ag/series/1/",
            translator_id="1",
            quality="720p",
            season=1,
            episode=1,
        )

    assert url == "https://cdn.example.com/s01e01.mp4"
    mock_film.getStream.assert_called_once_with(season=1, episode=1, translation="1")


def test_get_stream_url_raises_on_empty():
    mock_stream = MagicMock(return_value=[])
    mock_film = MagicMock()
    mock_film.getStream.return_value = mock_stream

    import pytest

    with patch("app.core.rezka.HdRezkaApi", return_value=mock_film):
        with pytest.raises(ValueError, match="No stream URLs"):
            get_stream_url("https://hdrezka.ag/films/1/", "1", "1080p", 0, 0)
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
uv run pytest tests/test_rezka.py -v
```

Ожидаемый вывод: `ModuleNotFoundError: No module named 'app.core.rezka'`

- [ ] **Step 3: Реализовать app/core/rezka.py**

```python
from dataclasses import dataclass, field

from HdRezkaApi import HdRezkaApi, HdRezkaSearch, TVSeries

DEFAULT_URL = "https://hdrezka.ag"


@dataclass
class SearchResult:
    title: str
    url: str
    year: str
    is_series: bool


@dataclass
class FilmInfo:
    name: str
    is_series: bool
    translators: dict[str, str] = field(default_factory=dict)  # {name: id_str}
    seasons: dict[int, list[int]] = field(default_factory=dict)  # {season: [episodes]}


def search(query: str, base_url: str = DEFAULT_URL) -> list[SearchResult]:
    searcher = HdRezkaSearch(base_url)
    results_obj = searcher(query, find_all=True)
    items = results_obj.get_page(1) or []
    output = []
    for item in items:
        category = item.get("category", "")
        is_series = "сериал" in str(category).lower() or "аниме" in str(category).lower()
        output.append(
            SearchResult(
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                year=str(item.get("year", "")),
                is_series=is_series,
            )
        )
    return output


def get_film_info(url: str) -> FilmInfo:
    film = HdRezkaApi(url)
    translators = {v["name"]: str(k) for k, v in film.translators.items()}
    is_series = film.type == TVSeries
    seasons: dict[int, list[int]] = {}

    if is_series:
        try:
            series_info = film.seriesInfo
            if series_info:
                first_tr_data = next(iter(series_info.values()))
                eps_dict = first_tr_data.get("episodes", {})
                for season_str in first_tr_data.get("seasons", {}).keys():
                    s = int(season_str)
                    seasons[s] = [int(e) for e in eps_dict.get(season_str, {}).keys()]
        except Exception:
            pass

    return FilmInfo(
        name=film.name,
        is_series=is_series,
        translators=translators,
        seasons=seasons,
    )


def get_stream_url(
    url: str,
    translator_id: str,
    quality: str,
    season: int = 0,
    episode: int = 0,
) -> str:
    film = HdRezkaApi(url)
    if season and episode:
        stream = film.getStream(season=season, episode=episode, translation=translator_id)
    else:
        stream = film.getStream(translation=translator_id)
    urls = stream(quality)
    if not urls:
        raise ValueError(f"No stream URLs for quality {quality!r}")
    return urls[0]
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
uv run pytest tests/test_rezka.py -v
```

Ожидаемый вывод: все тесты `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/core/rezka.py tests/test_rezka.py
git commit -m "feat: add core rezka wrapper with tests"
```

---

### Task 3: core/downloader.py — DownloadWorker(QThread)

**Files:**
- Create: `app/core/downloader.py`
- Create: `tests/test_downloader.py`

**Interfaces:**
- Consumes: ничего из предыдущих задач
- Produces:
  - `class DownloadWorker(QThread):`
    - `__init__(self, url: str, save_path: str) -> None`
    - `progress = Signal(int, int)` — (downloaded_bytes, total_bytes)
    - `finished = Signal(str)` — абсолютный путь к файлу
    - `error = Signal(str)` — сообщение об ошибке
    - `cancel()` — остановить скачивание

- [ ] **Step 1: Написать тесты**

Создать `tests/test_downloader.py`:

```python
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from app.core.downloader import DownloadWorker


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    return app


def test_download_worker_emits_finished(qapp, tmp_path):
    save_path = str(tmp_path / "test.mp4")
    worker = DownloadWorker("https://example.com/test.mp4", save_path)

    finished_paths = []
    errors = []
    worker.finished.connect(finished_paths.append)
    worker.error.connect(errors.append)

    chunk = b"x" * 1024
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = iter([chunk])
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert errors == []
    assert finished_paths == [save_path]
    assert os.path.exists(save_path)


def test_download_worker_emits_progress(qapp, tmp_path):
    save_path = str(tmp_path / "prog.mp4")
    worker = DownloadWorker("https://example.com/prog.mp4", save_path)

    progress_calls = []
    worker.progress.connect(lambda d, t: progress_calls.append((d, t)))

    chunk = b"y" * 512
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = iter([chunk, chunk])
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert len(progress_calls) == 2
    assert progress_calls[0] == (512, 1024)
    assert progress_calls[1] == (1024, 1024)


def test_download_worker_emits_error_on_failure(qapp, tmp_path):
    save_path = str(tmp_path / "err.mp4")
    worker = DownloadWorker("https://example.com/err.mp4", save_path)

    errors = []
    finished_paths = []
    worker.error.connect(errors.append)
    worker.finished.connect(finished_paths.append)

    with patch("app.core.downloader.httpx.Client", side_effect=Exception("Network error")):
        worker.run()

    assert finished_paths == []
    assert len(errors) == 1
    assert "Network error" in errors[0]


def test_cancel_stops_download(qapp, tmp_path):
    save_path = str(tmp_path / "cancel.mp4")
    worker = DownloadWorker("https://example.com/cancel.mp4", save_path)

    finished_paths = []
    worker.finished.connect(finished_paths.append)

    def cancelled_chunks():
        worker.cancel()
        yield b"z" * 512

    mock_response = MagicMock()
    mock_response.headers = {"content-length": "1024"}
    mock_response.iter_bytes.return_value = cancelled_chunks()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    mock_client = MagicMock()
    mock_client.stream.return_value = mock_response
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.core.downloader.httpx.Client", return_value=mock_client):
        worker.run()

    assert finished_paths == []
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
uv run pytest tests/test_downloader.py -v
```

Ожидаемый вывод: `ModuleNotFoundError: No module named 'app.core.downloader'`

- [ ] **Step 3: Реализовать app/core/downloader.py**

```python
import httpx
from PySide6.QtCore import QThread, Signal


class DownloadWorker(QThread):
    progress = Signal(int, int)   # downloaded_bytes, total_bytes
    finished = Signal(str)        # absolute save_path
    error = Signal(str)           # error message

    def __init__(self, url: str, save_path: str) -> None:
        super().__init__()
        self._url = url
        self._save_path = save_path
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                with client.stream("GET", self._url) as response:
                    total = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    with open(self._save_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            if self._cancelled:
                                return
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.progress.emit(downloaded, total)
            self.finished.emit(self._save_path)
        except Exception as e:
            self.error.emit(str(e))
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
uv run pytest tests/test_downloader.py -v
```

Ожидаемый вывод: все тесты `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/core/downloader.py tests/test_downloader.py
git commit -m "feat: add DownloadWorker QThread with tests"
```

---

### Task 4: utils/settings.py — сохранение настроек

**Files:**
- Create: `app/utils/settings.py`
- Create: `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `get_download_folder() -> str` — возвращает сохранённую папку (default: ~/Downloads)
  - `set_download_folder(path: str) -> None`
  - `get_rezka_url() -> str` — возвращает base URL (default: "https://hdrezka.ag")
  - `set_rezka_url(url: str) -> None`

- [ ] **Step 1: Написать тесты**

Создать `tests/test_settings.py`:

```python
import os

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from app.utils.settings import get_download_folder, get_rezka_url, set_download_folder, set_rezka_url


@pytest.fixture(scope="session")
def qapp():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture(autouse=True)
def clean_settings(qapp):
    s = QSettings("DownloadFilmTest", "DownloadFilmTest")
    s.clear()
    yield
    s.clear()


def test_get_download_folder_default(qapp, monkeypatch):
    monkeypatch.setenv("HOME", "/tmp/testhome")
    # Use a fresh isolated settings by patching ORG/APP names
    import app.utils.settings as m
    orig_org, orig_app = m._ORG, m._APP
    m._ORG, m._APP = "DownloadFilmTest", "DownloadFilmTest"
    try:
        folder = get_download_folder()
        assert folder.endswith("Downloads") or folder == os.path.expanduser("~/Downloads")
    finally:
        m._ORG, m._APP = orig_org, orig_app


def test_set_and_get_download_folder(qapp):
    import app.utils.settings as m
    orig_org, orig_app = m._ORG, m._APP
    m._ORG, m._APP = "DownloadFilmTest", "DownloadFilmTest"
    try:
        set_download_folder("/tmp/mymovies")
        assert get_download_folder() == "/tmp/mymovies"
    finally:
        m._ORG, m._APP = orig_org, orig_app


def test_get_rezka_url_default(qapp):
    import app.utils.settings as m
    orig_org, orig_app = m._ORG, m._APP
    m._ORG, m._APP = "DownloadFilmTest", "DownloadFilmTest"
    try:
        url = get_rezka_url()
        assert url == "https://hdrezka.ag"
    finally:
        m._ORG, m._APP = orig_org, orig_app


def test_set_and_get_rezka_url(qapp):
    import app.utils.settings as m
    orig_org, orig_app = m._ORG, m._APP
    m._ORG, m._APP = "DownloadFilmTest", "DownloadFilmTest"
    try:
        set_rezka_url("https://hdrezka.me")
        assert get_rezka_url() == "https://hdrezka.me"
    finally:
        m._ORG, m._APP = orig_org, orig_app
```

- [ ] **Step 2: Запустить тесты — убедиться что падают**

```bash
uv run pytest tests/test_settings.py -v
```

Ожидаемый вывод: `ModuleNotFoundError: No module named 'app.utils.settings'`

- [ ] **Step 3: Реализовать app/utils/settings.py**

```python
import os

from PySide6.QtCore import QSettings

_ORG = "DownloadFilm"
_APP = "DownloadFilm"


def _s() -> QSettings:
    return QSettings(_ORG, _APP)


def get_download_folder() -> str:
    return _s().value("download_folder", os.path.expanduser("~/Downloads"))


def set_download_folder(path: str) -> None:
    _s().setValue("download_folder", path)


def get_rezka_url() -> str:
    return _s().value("rezka_url", "https://hdrezka.ag")


def set_rezka_url(url: str) -> None:
    _s().setValue("rezka_url", url)
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
uv run pytest tests/test_settings.py -v
```

Ожидаемый вывод: все тесты `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/utils/settings.py tests/test_settings.py
git commit -m "feat: add QSettings wrapper with tests"
```

---

### Task 5: ui/search_panel.py — поиск и список результатов

**Files:**
- Create: `app/ui/search_panel.py`

**Interfaces:**
- Consumes:
  - `search(query, base_url) -> list[SearchResult]` из `app.core.rezka`
  - `get_rezka_url() -> str` из `app.utils.settings`
- Produces:
  - `class SearchPanel(QWidget):`
    - `result_selected = Signal(SearchResult)` — когда пользователь кликает на результат
    - `status_message = Signal(str)` — строка статуса для статус-бара

- [ ] **Step 1: Реализовать app/ui/search_panel.py**

```python
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.rezka import SearchResult, search
from app.utils.settings import get_rezka_url


class _SearchWorker(QThread):
    results_ready = Signal(list)
    error = Signal(str)

    def __init__(self, query: str, base_url: str) -> None:
        super().__init__()
        self._query = query
        self._base_url = base_url

    def run(self) -> None:
        try:
            results = search(self._query, self._base_url)
            self.results_ready.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class SearchPanel(QWidget):
    result_selected = Signal(object)   # SearchResult
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[SearchResult] = []
        self._worker: _SearchWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Введите название фильма или сериала…")
        self._input.returnPressed.connect(self._do_search)
        self._btn = QPushButton("Найти")
        self._btn.clicked.connect(self._do_search)
        row.addWidget(self._input)
        row.addWidget(self._btn)
        layout.addLayout(row)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

    def _do_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            return
        self._btn.setEnabled(False)
        self._list.clear()
        self._results = []
        self.status_message.emit("Поиск…")

        self._worker = _SearchWorker(query, get_rezka_url())
        self._worker.results_ready.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_results(self, results: list[SearchResult]) -> None:
        self._btn.setEnabled(True)
        self._results = results
        self._list.clear()
        if not results:
            self.status_message.emit("Ничего не найдено")
            return
        for r in results:
            tag = "📺" if r.is_series else "🎬"
            year = f" ({r.year})" if r.year else ""
            item = QListWidgetItem(f"{tag} {r.title}{year}")
            self._list.addItem(item)
        self.status_message.emit(f"Найдено: {len(results)}")

    def _on_error(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.status_message.emit(f"Ошибка: {msg}")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        idx = self._list.row(item)
        if 0 <= idx < len(self._results):
            self.result_selected.emit(self._results[idx])
```

- [ ] **Step 2: Smoke-тест (ручной)**

```bash
uv run python -c "
from PySide6.QtWidgets import QApplication
from app.ui.search_panel import SearchPanel
import sys
app = QApplication(sys.argv)
w = SearchPanel()
w.show()
sys.exit(app.exec())
"
```

Ожидаемый результат: окно с полем поиска и кнопкой «Найти» открывается без ошибок.

- [ ] **Step 3: Commit**

```bash
git add app/ui/search_panel.py
git commit -m "feat: add SearchPanel with async search worker"
```

---

### Task 6: ui/detail_panel.py — выбор перевода, сезона/серии, качества

**Files:**
- Create: `app/ui/detail_panel.py`

**Interfaces:**
- Consumes:
  - `SearchResult` из `app.core.rezka`
  - `FilmInfo` из `app.core.rezka`
  - `get_film_info(url) -> FilmInfo` из `app.core.rezka`
  - `get_download_folder() -> str` из `app.utils.settings`
  - `set_download_folder(path) -> None` из `app.utils.settings`
- Produces:
  - `class DetailPanel(QWidget):`
    - `download_requested = Signal(str, str, str, int, int, str)` — (url, translator_id, quality, season, episode, save_path)
    - `status_message = Signal(str)`
    - `load(result: SearchResult) -> None` — загружает информацию о фильме

- [ ] **Step 1: Реализовать app/ui/detail_panel.py**

```python
import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.core.rezka import FilmInfo, SearchResult, get_film_info
from app.utils.settings import get_download_folder, set_download_folder

QUALITIES = ["1080p", "720p", "480p", "360p"]


class _InfoWorker(QThread):
    info_ready = Signal(object)  # FilmInfo
    error = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            self.info_ready.emit(get_film_info(self._url))
        except Exception as e:
            self.error.emit(str(e))


class DetailPanel(QWidget):
    download_requested = Signal(str, str, str, int, int, str)
    # url, translator_id, quality, season, episode, save_path
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_url: str = ""
        self._info: FilmInfo | None = None
        self._worker: _InfoWorker | None = None
        self._build_ui()
        self._set_enabled(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._title_label = QLabel("—")
        form.addRow("Название:", self._title_label)

        self._translator_combo = QComboBox()
        self._translator_combo.currentIndexChanged.connect(self._on_translator_changed)
        form.addRow("Перевод:", self._translator_combo)

        self._season_combo = QComboBox()
        self._season_combo.currentIndexChanged.connect(self._on_season_changed)
        self._season_label = QLabel("Сезон:")
        form.addRow(self._season_label, self._season_combo)

        self._episode_combo = QComboBox()
        self._episode_label = QLabel("Серия:")
        form.addRow(self._episode_label, self._episode_combo)

        layout.addLayout(form)

        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Качество:"))
        self._quality_group = QButtonGroup(self)
        for q in QUALITIES:
            rb = QRadioButton(q)
            if q == "1080p":
                rb.setChecked(True)
            self._quality_group.addButton(rb)
            quality_layout.addWidget(rb)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)

        folder_layout = QHBoxLayout()
        self._folder_label = QLabel(get_download_folder())
        self._folder_label.setWordWrap(True)
        folder_btn = QPushButton("Изменить…")
        folder_btn.clicked.connect(self._pick_folder)
        folder_layout.addWidget(QLabel("Папка:"))
        folder_layout.addWidget(self._folder_label, 1)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)

        self._download_btn = QPushButton("▼ Скачать")
        self._download_btn.clicked.connect(self._on_download)
        layout.addWidget(self._download_btn)
        layout.addStretch()

    def _set_enabled(self, enabled: bool) -> None:
        for w in [self._translator_combo, self._season_combo,
                  self._episode_combo, self._download_btn]:
            w.setEnabled(enabled)
        for btn in self._quality_group.buttons():
            btn.setEnabled(enabled)

    def load(self, result: SearchResult) -> None:
        self._set_enabled(False)
        self._current_url = result.url
        self._title_label.setText(result.title)
        self._translator_combo.clear()
        self._season_combo.clear()
        self._episode_combo.clear()
        self.status_message.emit("Загрузка информации…")

        self._worker = _InfoWorker(result.url)
        self._worker.info_ready.connect(self._on_info_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_info_ready(self, info: FilmInfo) -> None:
        self._info = info
        self._translator_combo.clear()
        for name in info.translators:
            self._translator_combo.addItem(name)

        has_seasons = info.is_series and bool(info.seasons)
        self._season_label.setVisible(has_seasons)
        self._season_combo.setVisible(has_seasons)
        self._episode_label.setVisible(has_seasons)
        self._episode_combo.setVisible(has_seasons)

        if has_seasons:
            self._season_combo.clear()
            for s in sorted(info.seasons):
                self._season_combo.addItem(str(s), s)
            self._on_season_changed(0)

        self._set_enabled(True)
        self.status_message.emit("Готово")

    def _on_error(self, msg: str) -> None:
        self.status_message.emit(f"Ошибка: {msg}")

    def _on_translator_changed(self, _: int) -> None:
        pass  # future: reload seasons per translator if needed

    def _on_season_changed(self, _: int) -> None:
        if self._info is None:
            return
        season = self._season_combo.currentData()
        if season is None:
            return
        self._episode_combo.clear()
        for ep in sorted(self._info.seasons.get(season, [])):
            self._episode_combo.addItem(str(ep), ep)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для загрузки", get_download_folder()
        )
        if folder:
            set_download_folder(folder)
            self._folder_label.setText(folder)

    def _selected_quality(self) -> str:
        btn = self._quality_group.checkedButton()
        return btn.text() if btn else "720p"

    def _on_download(self) -> None:
        if self._info is None:
            return
        translator_name = self._translator_combo.currentText()
        translator_id = self._info.translators.get(translator_name, "")
        quality = self._selected_quality()
        season = self._season_combo.currentData() or 0
        episode = self._episode_combo.currentData() or 0
        folder = get_download_folder()

        if self._info.is_series and season and episode:
            filename = f"{self._info.name}_S{season:02d}E{episode:02d}_{quality}.mp4"
        else:
            filename = f"{self._info.name}_{quality}.mp4"

        filename = "".join(c if c.isalnum() or c in " _-.()" else "_" for c in filename)
        save_path = os.path.join(folder, filename)

        self.download_requested.emit(
            self._current_url, translator_id, quality, season, episode, save_path
        )
```

- [ ] **Step 2: Smoke-тест (ручной)**

```bash
uv run python -c "
from PySide6.QtWidgets import QApplication
from app.ui.detail_panel import DetailPanel
import sys
app = QApplication(sys.argv)
w = DetailPanel()
w.show()
sys.exit(app.exec())
"
```

Ожидаемый результат: панель с полями (переводы, сезон, серия, качество, папка, кнопка скачать).

- [ ] **Step 3: Commit**

```bash
git add app/ui/detail_panel.py
git commit -m "feat: add DetailPanel with translator/season/quality selection"
```

---

### Task 7: ui/download_panel.py — очередь загрузок

**Files:**
- Create: `app/ui/download_panel.py`

**Interfaces:**
- Consumes:
  - `DownloadWorker` из `app.core.downloader`
  - `get_stream_url(url, translator_id, quality, season, episode) -> str` из `app.core.rezka`
- Produces:
  - `class DownloadPanel(QWidget):`
    - `add_download(url, translator_id, quality, season, episode, save_path) -> None`
    - `status_message = Signal(str)`

- [ ] **Step 1: Реализовать app/ui/download_panel.py**

```python
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.downloader import DownloadWorker
from app.core.rezka import get_stream_url


class _ResolveWorker(QThread):
    """Resolves stream URL (network call) then hands off to DownloadWorker."""

    url_ready = Signal(str, str)  # stream_url, save_path
    error = Signal(str)

    def __init__(
        self,
        page_url: str,
        translator_id: str,
        quality: str,
        season: int,
        episode: int,
        save_path: str,
    ) -> None:
        super().__init__()
        self._page_url = page_url
        self._translator_id = translator_id
        self._quality = quality
        self._season = season
        self._episode = episode
        self._save_path = save_path

    def run(self) -> None:
        try:
            stream_url = get_stream_url(
                self._page_url,
                self._translator_id,
                self._quality,
                self._season,
                self._episode,
            )
            self.url_ready.emit(stream_url, self._save_path)
        except Exception as e:
            self.error.emit(str(e))


class _DownloadRow(QWidget):
    def __init__(self, filename: str, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        self._label = QLabel(filename)
        self._label.setMinimumWidth(200)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._status = QLabel("Ожидание…")
        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setFixedWidth(30)

        layout.addWidget(self._label)
        layout.addWidget(self._bar, 1)
        layout.addWidget(self._status)
        layout.addWidget(self._cancel_btn)

    def set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self._bar.setValue(int(downloaded / total * 100))
        mb_down = downloaded / 1024 / 1024
        mb_total = total / 1024 / 1024
        self._status.setText(f"{mb_down:.1f}/{mb_total:.1f} MB")

    def set_done(self) -> None:
        self._bar.setValue(100)
        self._status.setText("Готово ✓")
        self._cancel_btn.setEnabled(False)

    def set_error(self, msg: str) -> None:
        self._status.setText(f"Ошибка: {msg}")
        self._cancel_btn.setEnabled(False)

    def connect_cancel(self, slot) -> None:
        self._cancel_btn.clicked.connect(slot)


class DownloadPanel(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._workers: list[tuple[_DownloadRow, DownloadWorker | _ResolveWorker]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(QLabel("Загрузки:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._rows_layout = QVBoxLayout(container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def add_download(
        self,
        page_url: str,
        translator_id: str,
        quality: str,
        season: int,
        episode: int,
        save_path: str,
    ) -> None:
        import os

        filename = os.path.basename(save_path)
        row = _DownloadRow(filename)
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

        resolver = _ResolveWorker(page_url, translator_id, quality, season, episode, save_path)

        def on_url_ready(stream_url: str, sp: str) -> None:
            dl = DownloadWorker(stream_url, sp)
            dl.progress.connect(row.set_progress)
            dl.finished.connect(lambda _: row.set_done())
            dl.finished.connect(lambda p: self.status_message.emit(f"Скачано: {os.path.basename(p)}"))
            dl.error.connect(row.set_error)
            self._workers.append((row, dl))
            row.connect_cancel(dl.cancel)
            dl.start()

        def on_error(msg: str) -> None:
            row.set_error(msg)
            self.status_message.emit(f"Ошибка получения ссылки: {msg}")

        resolver.url_ready.connect(on_url_ready)
        resolver.error.connect(on_error)
        self._workers.append((row, resolver))
        resolver.start()
        self.status_message.emit(f"Получение ссылки для {filename}…")
```

- [ ] **Step 2: Commit**

```bash
git add app/ui/download_panel.py
git commit -m "feat: add DownloadPanel with progress rows and cancel support"
```

---

### Task 8: ui/main_window.py + app/main.py — сборка приложения

**Files:**
- Create: `app/ui/main_window.py`
- Create: `app/main.py`

**Interfaces:**
- Consumes: `SearchPanel`, `DetailPanel`, `DownloadPanel`
- Produces: запускаемое приложение

- [ ] **Step 1: Реализовать app/ui/main_window.py**

```python
from PySide6.QtWidgets import QMainWindow, QSplitter, QStatusBar, QWidget
from PySide6.QtCore import Qt

from app.ui.search_panel import SearchPanel
from app.ui.detail_panel import DetailPanel
from app.ui.download_panel import DownloadPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DownloadFilm")
        self.setMinimumSize(900, 600)
        self._build_ui()

    def _build_ui(self) -> None:
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._search = SearchPanel()
        self._detail = DetailPanel()
        self._downloads = DownloadPanel()

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self._search)
        top_splitter.addWidget(self._detail)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self._downloads)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)

        self.setCentralWidget(main_splitter)

        self._search.result_selected.connect(self._detail.load)
        self._search.status_message.connect(status_bar.showMessage)
        self._detail.status_message.connect(status_bar.showMessage)
        self._detail.download_requested.connect(self._on_download_requested)
        self._downloads.status_message.connect(status_bar.showMessage)

    def _on_download_requested(
        self,
        url: str,
        translator_id: str,
        quality: str,
        season: int,
        episode: int,
        save_path: str,
    ) -> None:
        self._downloads.add_download(url, translator_id, quality, season, episode, save_path)
```

- [ ] **Step 2: Реализовать app/main.py**

```python
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DownloadFilm")
    app.setOrganizationName("DownloadFilm")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Запустить приложение**

```bash
uv run python -m app.main
```

Ожидаемый результат: окно приложения открывается, поиск работает, детали фильма загружаются.

- [ ] **Step 4: Commit**

```bash
git add app/ui/main_window.py app/main.py
git commit -m "feat: add MainWindow and app entry point — app is functional"
```

---

### Task 9: PyInstaller spec — сборка в исполняемый файл

**Files:**
- Create: `download_film.spec`

**Interfaces:**
- Consumes: `app/main.py`
- Produces: `dist/DownloadFilm` (Mac) или `dist/DownloadFilm.exe` (Windows)

- [ ] **Step 1: Установить PyInstaller**

Добавить в `pyproject.toml` в `[dependency-groups] dev`:

```toml
[dependency-groups]
dev = [
    "ruff>=0.4.0",
    "pytest>=8.0.0",
    "pytest-qt>=4.4.0",
    "pyinstaller>=6.0.0",
]
```

```bash
uv sync
```

- [ ] **Step 2: Создать download_film.spec**

```python
# download_film.spec
block_cipher = None

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "HdRezkaApi",
        "httpx",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["aiogram", "peewee", "aiohttp"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DownloadFilm",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Mac: wrap in .app bundle
import sys
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="DownloadFilm.app",
        bundle_identifier="com.downloadfilm.app",
    )
```

- [ ] **Step 3: Собрать приложение**

```bash
uv run pyinstaller download_film.spec
```

Ожидаемый вывод: `dist/DownloadFilm` (Mac) или `dist/DownloadFilm.exe` (Windows) создан.

- [ ] **Step 4: Запустить собранный бинарник**

Mac:
```bash
open dist/DownloadFilm.app
```

Windows:
```
dist\DownloadFilm.exe
```

Ожидаемый результат: приложение запускается без ошибок.

- [ ] **Step 5: Добавить dist/ в .gitignore**

```bash
echo "dist/" >> .gitignore
echo "build/" >> .gitignore
```

- [ ] **Step 6: Commit**

```bash
git add download_film.spec .gitignore pyproject.toml
git commit -m "build: add PyInstaller spec for Windows and macOS packaging"
```

---

## Self-Review

### Spec coverage
- ✅ Поиск фильма → результаты
- ✅ Выбор перевода
- ✅ Выбор сезона/серии (сериалы)
- ✅ Выбор качества (480/720/1080p)
- ✅ Скачивание с прогрессом
- ✅ Папка загрузки (запоминается)
- ✅ Windows + Mac через PyInstaller
- ✅ Никаких прокси/БД/Telegram

### Placeholder scan
- Нет TBD, TODO, placeholder-текстов — всё с реальным кодом.

### Type consistency
- `SearchResult`, `FilmInfo` определены в Task 2, используются в Tasks 5–7 с теми же именами.
- `DownloadWorker` определён в Task 3, используется в Task 7.
- `download_requested` Signal: `(str, str, str, int, int, str)` — одинаковый в Tasks 6, 8.
