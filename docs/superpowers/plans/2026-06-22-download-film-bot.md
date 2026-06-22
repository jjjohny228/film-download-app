# DownloadFilmBot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that searches HdRezka and delivers direct download links via rotating proxies.

**Architecture:** Layered (handlers → services → database). HdRezkaApi (sync) runs in `ThreadPoolExecutor(max_workers=1)` with proxy injected via env vars. Peewee models accessed via `run_in_executor` wrappers.

**Tech Stack:** Python 3.11+, aiogram 3.x, peewee 3.x, pydantic-settings, HdRezkaApi (git), uv, ruff

## Global Constraints

- Python >= 3.11
- aiogram >= 3.7.0, peewee >= 3.17.0, pydantic-settings >= 2.0.0
- ruff line-length = 100, target = py311
- SQLite at `DB_PATH` (default `data/bot.db`), all Peewee calls via `run_in_executor`
- HdRezkaApi runs in `ThreadPoolExecutor(max_workers=1)` — serialises calls, env vars safe
- Bot interface: Russian
- ADMIN_IDS from .env as comma-separated integers

---

## File Map

```
DownloadFilmBot/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── data/                        # created at runtime
├── tests/
│   ├── test_proxy_service.py
│   ├── test_config.py
│   └── test_keyboards.py
└── bot/
    ├── main.py
    ├── config.py
    ├── database/
    │   ├── __init__.py
    │   ├── models.py
    │   └── db.py
    ├── services/
    │   ├── __init__.py
    │   ├── proxy.py
    │   └── rezka.py
    ├── handlers/
    │   ├── __init__.py
    │   ├── user.py
    │   └── admin.py
    ├── keyboards/
    │   ├── __init__.py
    │   ├── reply.py
    │   └── inline.py
    ├── states/
    │   ├── __init__.py
    │   └── states.py
    └── middlewares/
        ├── __init__.py
        └── user.py
```

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: all `__init__.py` stubs + empty handler/service/keyboard/state/middleware files

**Interfaces:**
- Produces: runnable `uv sync`, importable `bot` package

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "download-film-bot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "aiogram>=3.7.0",
    "pydantic-settings>=2.0.0",
    "peewee>=3.17.0",
    "aiohttp>=3.9.0",
    "HdRezkaApi @ git+https://github.com/SuperZombi/HdRezkaApi.git",
]

[dependency-groups]
dev = [
    "ruff>=0.4.0",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create .env.example**

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
REZKA_URL=https://hdrezka.ag
DB_PATH=data/bot.db
```

- [ ] **Step 3: Create .gitignore**

```
.env
data/
__pycache__/
.venv/
*.pyc
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 4: Create folder structure and empty __init__.py files**

```bash
mkdir -p bot/database bot/services bot/handlers bot/keyboards bot/states bot/middlewares tests data
touch bot/__init__.py bot/database/__init__.py bot/services/__init__.py
touch bot/handlers/__init__.py bot/keyboards/__init__.py bot/states/__init__.py bot/middlewares/__init__.py
touch bot/main.py bot/config.py
touch bot/database/models.py bot/database/db.py
touch bot/services/proxy.py bot/services/rezka.py
touch bot/handlers/user.py bot/handlers/admin.py
touch bot/keyboards/reply.py bot/keyboards/inline.py
touch bot/states/states.py bot/middlewares/user.py
touch tests/__init__.py tests/test_proxy_service.py tests/test_config.py tests/test_keyboards.py
```

- [ ] **Step 5: Install dependencies**

```bash
uv sync
```

Expected: resolves all packages including HdRezkaApi from git, no errors.

---

### Task 2: Config + Database

**Files:**
- Create: `bot/config.py`
- Create: `bot/database/models.py`
- Create: `bot/database/db.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `settings: Settings` singleton with `.BOT_TOKEN`, `.ADMIN_IDS`, `.REZKA_URL`, `.DB_PATH`
  - `User`, `Proxy` Peewee models
  - `init_db(path: str) -> None`
  - `run_sync(fn: Callable, *args, **kwargs) -> Awaitable`

- [ ] **Step 1: Write failing test for config**

```python
# tests/test_config.py
import os
import pytest

def test_admin_ids_parsed_from_string(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("ADMIN_IDS", "111,222,333")
    monkeypatch.setenv("REZKA_URL", "https://hdrezka.ag")
    monkeypatch.setenv("DB_PATH", "data/test.db")

    # Re-import with fresh env
    import importlib
    import bot.config as cfg_module
    importlib.reload(cfg_module)
    from bot.config import Settings
    s = Settings()
    assert s.ADMIN_IDS == [111, 222, 333]

def test_admin_ids_empty_by_default(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.delenv("ADMIN_IDS", raising=False)
    from bot.config import Settings
    s = Settings()
    assert s.ADMIN_IDS == []
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Implement bot/config.py**

```python
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    REZKA_URL: str = "https://hdrezka.ag"
    DB_PATH: str = "data/bot.db"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: object) -> list[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v  # type: ignore[return-value]


settings = Settings()
```

- [ ] **Step 4: Implement bot/database/models.py**

```python
from datetime import datetime

from peewee import (
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    Model,
    SqliteDatabase,
)

db = SqliteDatabase(None)  # initialised in db.py


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    tg_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    full_name = CharField()
    joined_at = DateTimeField(default=datetime.now)
    search_count = IntegerField(default=0)
    dl_count = IntegerField(default=0)
    is_banned = BooleanField(default=False)


class Proxy(BaseModel):
    host = CharField()
    port = IntegerField()
    login = CharField(null=True)
    password = CharField(null=True)
    protocol = CharField(default="http")
    is_active = BooleanField(default=True)
    fail_count = IntegerField(default=0)
    added_at = DateTimeField(default=datetime.now)
    last_used = DateTimeField(null=True)

    def to_url(self) -> str:
        if self.login and self.password:
            return f"{self.protocol}://{self.login}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
```

- [ ] **Step 5: Implement bot/database/db.py**

```python
import asyncio
from pathlib import Path
from typing import Callable, TypeVar

from .models import Proxy, User, db

T = TypeVar("T")


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db.init(db_path)
    db.connect(reuse_if_open=True)
    db.create_tables([User, Proxy], safe=True)


async def run_sync(fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
uv run pytest tests/test_config.py -v
```

Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .env.example .gitignore bot/ tests/test_config.py
git commit -m "feat: scaffold project, config, and database models"
```

---

### Task 3: Proxy service

**Files:**
- Create: `bot/services/proxy.py`
- Test: `tests/test_proxy_service.py`

**Interfaces:**
- Produces:
  - `NoProxyAvailable(Exception)`
  - `parse_proxy_line(line: str) -> ParsedProxy`
  - `ProxyService.get_next() -> Proxy`
  - `ProxyService.mark_failed(proxy_id: int) -> bool`
  - `ProxyService.add_proxies(lines: list[str]) -> int`
  - `ProxyService.get_stats() -> dict`
  - `ProxyService.register_no_proxy_callback(cb: Callable) -> None`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_proxy_service.py
import pytest
from bot.services.proxy import parse_proxy_line, ParsedProxy, NoProxyAvailable


def test_parse_full_proxy():
    result = parse_proxy_line("http 85.195.81.148:10772:WUkKKj:fXx0qQ")
    assert result == ParsedProxy(
        protocol="http",
        host="85.195.81.148",
        port=10772,
        login="WUkKKj",
        password="fXx0qQ",
    )


def test_parse_proxy_no_auth():
    result = parse_proxy_line("socks5 1.2.3.4:1080")
    assert result == ParsedProxy(
        protocol="socks5",
        host="1.2.3.4",
        port=1080,
        login=None,
        password=None,
    )


def test_parse_proxy_invalid_raises():
    with pytest.raises(ValueError):
        parse_proxy_line("notaproxy")


def test_no_proxy_available_is_exception():
    assert issubclass(NoProxyAvailable, Exception)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run pytest tests/test_proxy_service.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement bot/services/proxy.py**

```python
import random
from dataclasses import dataclass
from typing import Callable

from bot.database.db import run_sync
from bot.database.models import Proxy


class NoProxyAvailable(Exception):
    pass


@dataclass
class ParsedProxy:
    protocol: str
    host: str
    port: int
    login: str | None
    password: str | None


def parse_proxy_line(line: str) -> ParsedProxy:
    """Parse 'protocol host:port[:login:password]' format."""
    parts = line.strip().split(" ", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid proxy line: {line!r}")
    protocol = parts[0].lower()
    addr = parts[1].split(":")
    if len(addr) == 2:
        host, port_s = addr
        login = password = None
    elif len(addr) == 4:
        host, port_s, login, password = addr
    else:
        raise ValueError(f"Invalid proxy address: {parts[1]!r}")
    return ParsedProxy(
        protocol=protocol,
        host=host,
        port=int(port_s),
        login=login or None,
        password=password or None,
    )


_no_proxy_callbacks: list[Callable] = []


class ProxyService:
    @staticmethod
    def register_no_proxy_callback(cb: Callable) -> None:
        _no_proxy_callbacks.append(cb)

    @staticmethod
    async def get_next() -> Proxy:
        def _query() -> Proxy:
            active = list(Proxy.select().where(Proxy.is_active == True))  # noqa: E712
            if not active:
                raise NoProxyAvailable
            return random.choice(active)

        try:
            return await run_sync(_query)
        except NoProxyAvailable:
            for cb in _no_proxy_callbacks:
                await cb()
            raise

    @staticmethod
    async def mark_failed(proxy_id: int) -> bool:
        """Increments fail_count. Deactivates at >= 3. Returns True if deactivated."""

        def _mark() -> bool:
            p = Proxy.get_by_id(proxy_id)
            p.fail_count += 1
            if p.fail_count >= 3:
                p.is_active = False
            p.save()
            return not p.is_active

        deactivated = await run_sync(_mark)
        if deactivated:
            remaining = await run_sync(
                lambda: Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
            )
            if remaining == 0:
                for cb in _no_proxy_callbacks:
                    await cb()
        return deactivated

    @staticmethod
    async def add_proxies(lines: list[str]) -> int:
        added = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                p = parse_proxy_line(line)
            except ValueError:
                continue

            def _upsert(parsed: ParsedProxy = p) -> None:
                Proxy.get_or_create(
                    host=parsed.host,
                    port=parsed.port,
                    protocol=parsed.protocol,
                    defaults={
                        "login": parsed.login,
                        "password": parsed.password,
                        "is_active": True,
                        "fail_count": 0,
                    },
                )

            await run_sync(_upsert)
            added += 1
        return added

    @staticmethod
    async def get_stats() -> dict:
        def _q() -> dict:
            total = Proxy.select().count()
            active = Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
            return {"total": total, "active": active}

        return await run_sync(_q)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
uv run pytest tests/test_proxy_service.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add bot/services/proxy.py tests/test_proxy_service.py
git commit -m "feat: proxy service with rotation and failure tracking"
```

---

### Task 4: Rezka service

**Files:**
- Create: `bot/services/rezka.py`

**Interfaces:**
- Consumes: `ProxyService.get_next()`, `ProxyService.mark_failed()`, `NoProxyAvailable`
- Produces:
  - `SearchResult(name, url, year, type_, poster)`
  - `FilmInfo(name, poster, type_, translators, seasons)`
  - `RezkaService(rezka_url: str)`
  - `RezkaService.search(query: str) -> list[SearchResult]`
  - `RezkaService.get_film_info(url: str) -> FilmInfo`
  - `RezkaService.get_stream_url(url, translation, quality, season, episode) -> str`

- [ ] **Step 1: Implement bot/services/rezka.py**

```python
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from bot.services.proxy import NoProxyAvailable, ProxyService

_executor = ThreadPoolExecutor(max_workers=1)


@dataclass
class SearchResult:
    name: str
    url: str
    year: str
    type_: str
    poster: str


@dataclass
class FilmInfo:
    name: str
    poster: str
    type_: str
    translators: dict[str, str] = field(default_factory=dict)
    seasons: dict[int, list[int]] = field(default_factory=dict)

    @property
    def is_series(self) -> bool:
        return "series" in self.type_.lower() or "cartoon" in self.type_.lower()


def _inject_proxy(proxy_url: str | None) -> None:
    if proxy_url:
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)


def _sync_search(query: str) -> list[SearchResult]:
    from HdRezkaApi import search as hdrezka_search  # imported inside executor thread

    results = []
    for r in hdrezka_search(query):
        results.append(
            SearchResult(
                name=str(getattr(r, "name", getattr(r, "title", ""))),
                url=str(getattr(r, "url", "")),
                year=str(getattr(r, "year", "")),
                type_=str(getattr(r, "type", "")),
                poster=str(getattr(r, "poster", getattr(r, "thumbnail", ""))),
            )
        )
    return results


def _sync_get_film_info(url: str) -> FilmInfo:
    from HdRezkaApi import HdRezkaApi

    film = HdRezkaApi(url)
    translators: dict[str, str] = {}
    if hasattr(film, "translators") and film.translators:
        translators = {str(k): str(v) for k, v in film.translators.items()}

    type_ = str(getattr(film, "type", "films"))
    seasons: dict[int, list[int]] = {}

    if "series" in type_.lower() and translators:
        first_tr_name = next(iter(translators))
        try:
            stream = film.getStream(translation=first_tr_name)
            raw_seasons = getattr(stream, "seasons", {})
            seasons = {int(s): list(eps) for s, eps in raw_seasons.items()}
        except Exception:
            pass

    return FilmInfo(
        name=str(getattr(film, "name", "")),
        poster=str(getattr(film, "thumbnail", getattr(film, "poster", ""))),
        type_=type_,
        translators=translators,
        seasons=seasons,
    )


def _sync_get_stream_url(
    url: str, translation: str, quality: str, season: int = 0, episode: int = 0
) -> str:
    from HdRezkaApi import HdRezkaApi

    film = HdRezkaApi(url)
    if season and episode:
        stream = film.getStream(translation=translation, season=season, episode=episode)
    else:
        stream = film.getStream(translation=translation)
    return stream(quality)


class RezkaService:
    def __init__(self, rezka_url: str) -> None:
        self.rezka_url = rezka_url

    async def _run(self, fn, *args, max_retries: int = 3):
        loop = asyncio.get_event_loop()
        last_err: Exception | None = None

        for _ in range(max_retries):
            try:
                proxy = await ProxyService.get_next()
                proxy_url = proxy.to_url()
            except NoProxyAvailable:
                raise

            try:
                result = await loop.run_in_executor(
                    _executor,
                    lambda pu=proxy_url: (
                        _inject_proxy(pu) or None,
                        fn(*args),
                    )[1],
                )
                _inject_proxy(None)
                return result
            except Exception as e:
                _inject_proxy(None)
                msg = str(e)
                if "403" in msg or "503" in msg:
                    await ProxyService.mark_failed(proxy.id)
                    last_err = e
                else:
                    raise

        raise last_err  # type: ignore[misc]

    async def search(self, query: str) -> list[SearchResult]:
        return await self._run(_sync_search, query)

    async def get_film_info(self, url: str) -> FilmInfo:
        return await self._run(_sync_get_film_info, url)

    async def get_stream_url(
        self,
        url: str,
        translation: str,
        quality: str,
        season: int = 0,
        episode: int = 0,
    ) -> str:
        return await self._run(_sync_get_stream_url, url, translation, quality, season, episode)
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from bot.services.rezka import RezkaService, SearchResult, FilmInfo; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/services/rezka.py
git commit -m "feat: rezka service wrapping HdRezkaApi with proxy rotation"
```

---

### Task 5: States + Keyboards

**Files:**
- Create: `bot/states/states.py`
- Create: `bot/keyboards/reply.py`
- Create: `bot/keyboards/inline.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: `FilmInfo`, `SearchResult`
- Produces:
  - `SearchStates`, `AdminStates` FSM groups
  - `main_menu_kb(is_admin: bool) -> ReplyKeyboardMarkup`
  - `carousel_kb(idx: int, total: int) -> InlineKeyboardMarkup`
  - `translators_kb(translators: dict) -> InlineKeyboardMarkup`
  - `quality_kb() -> InlineKeyboardMarkup`
  - `seasons_kb(seasons: dict) -> InlineKeyboardMarkup`
  - `episodes_kb(episodes: list[int]) -> InlineKeyboardMarkup`

- [ ] **Step 1: Write failing keyboard tests**

```python
# tests/test_keyboards.py
from bot.keyboards.reply import main_menu_kb
from bot.keyboards.inline import carousel_kb, quality_kb


def test_main_menu_user_has_two_buttons():
    kb = main_menu_kb(is_admin=False)
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert "🔍 Найти фильм" in buttons
    assert "👤 Профиль" in buttons
    assert "📢 Рассылка" not in buttons


def test_main_menu_admin_has_admin_buttons():
    kb = main_menu_kb(is_admin=True)
    buttons = [btn.text for row in kb.keyboard for btn in row]
    assert "📢 Рассылка" in buttons
    assert "📊 Статистика" in buttons
    assert "🌐 Загрузить прокси" in buttons


def test_carousel_kb_shows_correct_counter():
    kb = carousel_kb(idx=2, total=8)
    all_text = [btn.text for row in kb.inline_keyboard for btn in row]
    assert "◀ 2/8 ▶" in all_text or any("2/8" in t for t in all_text)


def test_quality_kb_has_three_options():
    kb = quality_kb()
    buttons = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("480" in t for t in buttons)
    assert any("720" in t for t in buttons)
    assert any("1080" in t for t in buttons)
```

- [ ] **Step 2: Run — expect FAIL**

```bash
uv run pytest tests/test_keyboards.py -v
```

Expected: ImportError

- [ ] **Step 3: Implement bot/states/states.py**

```python
from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_title = State()
    browsing_results = State()
    selecting_translation = State()
    selecting_season = State()
    selecting_episode = State()
    selecting_quality = State()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_proxy = State()
```

- [ ] **Step 4: Implement bot/keyboards/reply.py**

```python
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
```

- [ ] **Step 5: Implement bot/keyboards/inline.py**

```python
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
    rows = []
    row = []
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
    rows = []
    row = []
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
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
uv run pytest tests/test_keyboards.py -v
```

Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add bot/states/ bot/keyboards/ tests/test_keyboards.py
git commit -m "feat: FSM states and keyboard builders"
```

---

### Task 6: User middleware + Admin filter

**Files:**
- Create: `bot/middlewares/user.py`

**Interfaces:**
- Consumes: `User` model, `run_sync`, `settings.ADMIN_IDS`
- Produces:
  - `UserMiddleware` (auto-registers user, increments search_count on FSM title input)
  - `AdminFilter` (aiogram Filter, passes if user in ADMIN_IDS)

- [ ] **Step 1: Implement bot/middlewares/user.py**

```python
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
        if isinstance(event, Update) and event.message:
            msg = event.message
            if msg.from_user:
                user = await run_sync(self._get_or_create, msg.from_user)
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
        # keep name fresh
        if user.full_name != tg_user.full_name or user.username != tg_user.username:
            user.full_name = tg_user.full_name
            user.username = tg_user.username
            user.save()
        return user


class AdminFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id in settings.ADMIN_IDS
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from bot.middlewares.user import UserMiddleware, AdminFilter; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/middlewares/user.py
git commit -m "feat: user auto-registration middleware and admin filter"
```

---

### Task 7: User handlers

**Files:**
- Create: `bot/handlers/user.py`

**Interfaces:**
- Consumes: all keyboards, states, `RezkaService`, `User` model, `run_sync`
- Produces: `user_router: Router` with all user-facing handlers registered

**In-memory cache:** `_search_cache: dict[int, list[SearchResult]]` — keyed by `user_id`, holds current search results for carousel.

- [ ] **Step 1: Implement bot/handlers/user.py**

```python
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InputMediaPhoto,
    Message,
)

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


# ── /start ──────────────────────────────────────────────────────────────────

@user_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    is_admin = message.from_user.id in settings.ADMIN_IDS
    await message.answer(
        "👋 Привет! Я помогу найти фильм и получить ссылку для скачивания.",
        reply_markup=main_menu_kb(is_admin=is_admin),
    )


# ── Профиль ─────────────────────────────────────────────────────────────────

@user_router.message(F.text == "👤 Профиль")
async def show_profile(message: Message) -> None:
    user: User = await run_sync(User.get, User.tg_id == message.from_user.id)
    await message.answer(
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user.tg_id}</code>\n"
        f"📛 Имя: {user.full_name}\n"
        f"📅 Дата регистрации: {user.joined_at.strftime('%d.%m.%Y')}\n"
        f"🔍 Поисков: {user.search_count}\n"
        f"📥 Скачиваний: {user.dl_count}",
        parse_mode="HTML",
    )


# ── Поиск — запрос ──────────────────────────────────────────────────────────

@user_router.message(F.text == "🔍 Найти фильм")
async def start_search(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_title)
    await message.answer("🔎 Введите название фильма или сериала:")


@user_router.message(SearchStates.waiting_title)
async def handle_search_query(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    if not query:
        await message.answer("Пожалуйста, введите название.")
        return

    await message.answer("⏳ Ищу...")

    # increment search count
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
            "⚠️ Прокси временно закончились. Подождите — администраторы скоро добавят новые."
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


async def _send_carousel(message: Message, results: list[SearchResult], idx: int) -> None:
    r = results[idx]
    caption = f"🎬 <b>{r.name}</b>\n📅 {r.year}  |  🎭 {r.type_}"
    kb = carousel_kb(idx + 1, len(results))
    if r.poster:
        await message.answer_photo(photo=r.poster, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


# ── Карусель — навигация ─────────────────────────────────────────────────────

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

    if direction == "prev":
        idx = (idx - 1) % len(results)
    else:
        idx = (idx + 1) % len(results)

    await state.update_data(idx=idx)
    r = results[idx]
    caption = f"🎬 <b>{r.name}</b>\n📅 {r.year}  |  🎭 {r.type_}"
    kb = carousel_kb(idx + 1, len(results))

    try:
        if r.poster:
            await call.message.edit_media(
                media=InputMediaPhoto(media=r.poster, caption=caption, parse_mode="HTML"),
                reply_markup=kb,
            )
        else:
            await call.message.edit_caption(caption=caption, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await call.answer()


# ── Скачать — начало ─────────────────────────────────────────────────────────

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
            "⚠️ Прокси временно закончились. Подождите — администраторы скоро добавят новые."
        )
        return
    except Exception as e:
        await call.message.answer(f"❌ Ошибка: {e}")
        return

    await state.update_data(film_url=film_url)
    await state.set_state(SearchStates.selecting_translation)

    if info.translators:
        await call.message.answer(
            "🌐 Выберите перевод:", reply_markup=translators_kb(info.translators)
        )
    else:
        # No translators — skip straight to quality/season
        await state.update_data(translation="")
        if info.is_series and info.seasons:
            await state.set_state(SearchStates.selecting_season)
            await call.message.answer("📺 Выберите сезон:", reply_markup=seasons_kb(info.seasons))
        else:
            await state.set_state(SearchStates.selecting_quality)
            await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор перевода ───────────────────────────────────────────────────────────

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
            # Try to load seasons now with this translator
            try:
                fresh = await get_rezka().get_film_info(film_url)
                info = fresh
                _film_info_cache[film_url] = fresh
            except Exception:
                pass

        if info.seasons:
            await state.set_state(SearchStates.selecting_season)
            await call.message.answer("📺 Выберите сезон:", reply_markup=seasons_kb(info.seasons))
        else:
            await state.set_state(SearchStates.selecting_quality)
            await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())
    else:
        await state.set_state(SearchStates.selecting_quality)
        await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор сезона ─────────────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("s:"), SearchStates.selecting_season)
async def select_season(call: CallbackQuery, state: FSMContext) -> None:
    season = int(call.data.split(":")[1])
    await state.update_data(season=season)

    data = await state.get_data()
    film_url: str = data["film_url"]
    info = _film_info_cache.get(film_url)

    if info is None or season not in info.seasons:
        await call.answer("Сезон недоступен.")
        return

    await call.answer(f"Сезон {season}")
    await state.set_state(SearchStates.selecting_episode)
    await call.message.answer(
        f"📺 Сезон {season} — выберите серию:",
        reply_markup=episodes_kb(info.seasons[season], season),
    )


# ── Выбор серии ──────────────────────────────────────────────────────────────

@user_router.callback_query(F.data.startswith("ep:"), SearchStates.selecting_episode)
async def select_episode(call: CallbackQuery, state: FSMContext) -> None:
    _, season_s, ep_s = call.data.split(":")
    await state.update_data(season=int(season_s), episode=int(ep_s))
    await call.answer(f"Серия {ep_s}")
    await state.set_state(SearchStates.selecting_quality)
    await call.message.answer("📊 Выберите качество:", reply_markup=quality_kb())


# ── Выбор качества + получение ссылки ────────────────────────────────────────

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
            "⚠️ Прокси временно закончились. Подождите — администраторы скоро добавят новые."
        )
        await state.clear()
        return
    except Exception as e:
        await call.message.answer(f"❌ Не удалось получить ссылку: {e}")
        await state.clear()
        return

    # increment download counter
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
        f"<i>Ссылка может быть временной. Скачайте сразу.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await state.clear()
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from bot.handlers.user import user_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/user.py
git commit -m "feat: user handlers — search FSM, carousel, download flow"
```

---

### Task 8: Admin handlers

**Files:**
- Create: `bot/handlers/admin.py`

**Interfaces:**
- Consumes: `AdminFilter`, `ProxyService`, `User`, `run_sync`, `AdminStates`
- Produces: `admin_router: Router`

- [ ] **Step 1: Implement bot/handlers/admin.py**

```python
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.db import run_sync
from bot.database.models import Proxy, User
from bot.middlewares.user import AdminFilter
from bot.services.proxy import ProxyService
from bot.states.states import AdminStates

admin_router = Router()
admin_router.message.filter(AdminFilter())


# ── Рассылка ─────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer(
        "📢 Отправьте сообщение для рассылки (текст, фото или видео).\n"
        "Для отмены напишите /cancel"
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


# ── Статистика ───────────────────────────────────────────────────────────────

@admin_router.message(F.text == "📊 Статистика")
async def show_stats(message: Message) -> None:
    def _q():
        total_users = User.select().count()
        total_searches = User.select(User.search_count).scalar(convert=True) or 0
        total_downloads = User.select(User.dl_count).scalar(convert=True) or 0
        # sum via raw query
        import peewee
        total_searches = User.select(peewee.fn.SUM(User.search_count)).scalar() or 0
        total_downloads = User.select(peewee.fn.SUM(User.dl_count)).scalar() or 0
        active_proxies = Proxy.select().where(Proxy.is_active == True).count()  # noqa: E712
        total_proxies = Proxy.select().count()
        return total_users, total_searches, total_downloads, active_proxies, total_proxies

    total_users, total_searches, total_dl, active_p, total_p = await run_sync(_q)

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"🔍 Поисков всего: {total_searches}\n"
        f"📥 Скачиваний всего: {total_dl}\n"
        f"🌐 Активных прокси: {active_p} / {total_p}",
        parse_mode="HTML",
    )


# ── Прокси ───────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "🌐 Загрузить прокси")
async def start_proxy_upload(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_proxy)
    await message.answer(
        "🌐 Отправьте список прокси (каждый с новой строки):\n\n"
        "<code>http 85.195.81.148:10772:login:password\n"
        "socks5 1.2.3.4:1080:user:pass</code>\n\n"
        "Для отмены напишите /cancel",
        parse_mode="HTML",
    )


@admin_router.message(AdminStates.waiting_proxy)
async def handle_proxy_upload(message: Message, state: FSMContext) -> None:
    await state.clear()
    lines = (message.text or "").strip().splitlines()
    added = await ProxyService.add_proxies(lines)
    await message.answer(f"✅ Добавлено прокси: {added}")


# ── /cancel ───────────────────────────────────────────────────────────────────

@admin_router.message(F.text == "/cancel")
async def cancel_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.")
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from bot.handlers.admin import admin_router; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bot/handlers/admin.py
git commit -m "feat: admin handlers — broadcast, stats, proxy upload"
```

---

### Task 9: Main entrypoint

**Files:**
- Create: `bot/main.py`

**Interfaces:**
- Consumes: all routers, middleware, db init, ProxyService, settings
- Produces: runnable bot via `uv run python -m bot.main`

- [ ] **Step 1: Implement bot/main.py**

```python
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def notify_no_proxy(bot: Bot) -> None:
    """Broadcast to all users + alert admins when proxies run out."""
    from bot.database.db import run_sync
    from bot.database.models import User

    users: list[User] = await run_sync(
        lambda: list(User.select().where(User.is_banned == False))  # noqa: E712
    )
    msg = (
        "⚠️ Прокси временно закончились.\n"
        "Подождите — администраторы скоро добавят новые."
    )
    for user in users:
        try:
            await bot.send_message(user.tg_id, msg)
        except Exception:
            pass

    admin_msg = "🚨 Все прокси исчерпаны! Необходимо добавить новые через бот (🌐 Загрузить прокси)."
    for admin_id in settings.ADMIN_IDS:
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

    # Register no-proxy callback with reference to bot
    ProxyService.register_no_proxy_callback(lambda: notify_no_proxy(bot))

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(UserMiddleware())

    dp.include_router(admin_router)
    dp.include_router(user_router)

    log.info("Starting polling...")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify bot starts (needs real .env)**

Copy `.env.example` to `.env`, fill in `BOT_TOKEN`, then:

```bash
uv run python -m bot.main
```

Expected: `Starting polling...` log line, no errors.

- [ ] **Step 3: Commit**

```bash
git add bot/main.py
git commit -m "feat: main entrypoint wiring bot, routers, middleware"
```

---

### Task 10: README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# DownloadFilmBot

Telegram-бот для поиска фильмов и сериалов на HdRezka с выдачей прямых ссылок для скачивания.

## Стек

- **Python 3.11+** + **uv** (пакетный менеджер)
- **aiogram 3.x** — Telegram Bot Framework
- **Peewee** — ORM, SQLite
- **HdRezkaApi** — парсинг HdRezka
- **ruff** — линтер

## Установка

```bash
# Клонировать репо
git clone <repo> && cd DownloadFilmBot

# Создать .env
cp .env.example .env
# Заполнить BOT_TOKEN и ADMIN_IDS

# Установить зависимости
uv sync

# Запустить
uv run python -m bot.main
```

## Конфигурация (.env)

| Переменная | Описание | По умолчанию |
|-----------|---------|-------------|
| `BOT_TOKEN` | Токен Telegram-бота | — |
| `ADMIN_IDS` | ID администраторов через запятую | — |
| `REZKA_URL` | Зеркало HdRezka | `https://hdrezka.ag` |
| `DB_PATH` | Путь к SQLite базе | `data/bot.db` |

## Прокси

Формат: `protocol host:port:login:password`

Пример: `http 85.195.81.148:10772:WUkKKj:fXx0qQ`

Загружаются через меню бота: **🌐 Загрузить прокси** (доступно администраторам).

При ошибках 403/504 прокси автоматически меняются. Если активных нет — все пользователи получают уведомление, администраторам приходит алерт.

## Пользовательский сценарий

1. `/start` → главное меню
2. **🔍 Найти фильм** → ввести название → карусель результатов (←/→)
3. **🎬 Скачать** → выбор перевода → сезон/серия (для сериалов) → качество (480/720/1080p) → ссылка

## Линтинг

```bash
uv run ruff check .
uv run ruff format .
```

## Тесты

```bash
uv run pytest
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

## Self-Review

**Spec coverage:**
- ✅ /start + keyboard
- ✅ FSM search flow
- ✅ Carousel with ←/→ navigation (edit_message_media)
- ✅ Photo + title + year display
- ✅ Translation selection
- ✅ Film: translation → quality → link
- ✅ Series: translation → season → episode → quality → link
- ✅ Profile (ID, name, join date, search/dl counts)
- ✅ Admin: broadcast (text + photo + video via copy_to)
- ✅ Admin: statistics
- ✅ Admin: proxy upload
- ✅ Proxy format parsing
- ✅ Proxy rotation on 403/503 (mark_failed → deactivate at 3 fails)
- ✅ No-proxy notification to all users + admin alert
- ✅ SQLite via Peewee
- ✅ HdRezkaApi for search + getStream
- ✅ uv + ruff
- ✅ README

**Placeholder scan:** None found.

**Type consistency:** `SearchResult.type_`, `FilmInfo.type_`, `FilmInfo.is_series` — consistent across tasks 4, 7. `carousel_kb(idx+1, total)` uses 1-based display, counter shows `1/8` not `0/8`. ✅
