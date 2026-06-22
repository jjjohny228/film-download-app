# DownloadFilmBot — Design Spec
_Date: 2026-06-22_

## Overview

Telegram bot that lets users search films/series on HdRezka and receive direct download links. Built with aiogram 3.x, uv, ruff, Peewee ORM (SQLite), HdRezkaApi.

---

## Stack

| Tool | Purpose |
|------|---------|
| aiogram 3.x | Telegram bot framework |
| uv | Package manager |
| ruff | Linter/formatter |
| Peewee | ORM (sync, called via run_in_executor) |
| SQLite | Database |
| HdRezkaApi | Film search + stream URLs |

---

## Project Structure

```
DownloadFilmBot/
├── pyproject.toml
├── .env.example
├── README.md
├── bot/
│   ├── main.py             # entry point — setup dp/bot/middleware/routers
│   ├── config.py           # pydantic Settings from .env
│   ├── database/
│   │   ├── models.py       # Peewee models
│   │   └── db.py           # init DB, run_sync helper (run_in_executor)
│   ├── services/
│   │   ├── rezka.py        # HdRezkaApi async wrapper
│   │   └── proxy.py        # ProxyService
│   ├── handlers/
│   │   ├── user.py         # all user handlers + router registration
│   │   └── admin.py        # all admin handlers + router registration
│   ├── keyboards/
│   │   ├── reply.py        # ReplyKeyboardMarkup builders
│   │   └── inline.py       # InlineKeyboardMarkup builders
│   ├── states/
│   │   └── states.py       # FSM StatesGroup
│   └── middlewares/
│       └── user.py         # auto-register user + update counters
```

---

## Database Models (Peewee)

### User
```python
tg_id        BigIntegerField(unique=True)
username     CharField(null=True)
full_name    CharField()
joined_at    DateTimeField(default=datetime.now)
search_count IntegerField(default=0)
dl_count     IntegerField(default=0)
is_banned    BooleanField(default=False)
```

### Proxy
```python
host       CharField()
port       IntegerField()
login      CharField(null=True)
password   CharField(null=True)
protocol   CharField(default="http")   # http / socks5
is_active  BooleanField(default=True)
fail_count IntegerField(default=0)     # >= 3 → deactivate
added_at   DateTimeField(default=datetime.now)
last_used  DateTimeField(null=True)
```

---

## FSM States

```python
class SearchStates(StatesGroup):
    waiting_title     # user types film name
    browsing_results  # carousel active

class AdminStates(StatesGroup):
    waiting_broadcast  # admin sends media/text
    waiting_proxy      # admin sends proxy list
```

---

## User Flow

### Main menu (/start)
Reply keyboard:
- `🔍 Найти фильм`
- `👤 Профиль`

Admins see additional reply keyboard:
- `📢 Рассылка`
- `📊 Статистика`
- `🌐 Загрузить прокси`

### Search flow
1. User presses `🔍 Найти фильм` → FSM enters `waiting_title`
2. User sends film name → HdRezkaApi search → results cached in memory keyed by `user_id`
3. Carousel shown: one photo message with inline keyboard
   - Caption: `{name} | {year} | {type}`
   - Buttons: `← [2/8] →` + `🎬 Скачать`
   - Navigation uses `edit_message_media` (no new messages)
4. User presses `🎬 Скачать`:
   - **Film:** select translation → select quality (480p/720p/1080p) → link sent
   - **Series:** select translation → select season → select episode → select quality → link sent
5. Each download increments `User.dl_count`

### Profile
Shows:
```
👤 Профиль
ID: 123456789
Имя: John Doe
Дата регистрации: 2026-06-22
🔍 Поисков: 42
📥 Скачиваний: 18
```

---

## Callback Data Format

All fit within Telegram's 64-byte limit:

| Callback | Meaning |
|----------|---------|
| `nav:prev` / `nav:next` | carousel navigation |
| `dl_start` | download button pressed |
| `tr:{idx}` | translation selected |
| `s:{num}` | season selected |
| `ep:{num}` | episode selected |
| `q:{quality}` | quality selected (480/720/1080) |

Selection state (current film URL, chosen translation, season, episode) stored in `FSMContext.data`.

---

## Admin Panel

### Access
`ADMIN_IDS=123,456` in `.env`. Middleware/filter checks `tg_id`.

### Broadcast
1. Admin presses `📢 Рассылка` → FSM `waiting_broadcast`
2. Admin sends message (text / photo / video)
3. Bot iterates all non-banned users, calls `copy_to`
4. Reports: `✅ Отправлено: 142 | ❌ Ошибок: 3`

### Statistics
Inline message:
```
👥 Всего юзеров: 150
🔍 Поисков всего: 420
📥 Скачиваний всего: 180
🌐 Активных прокси: 7 / 12
```

### Proxy upload
1. Admin presses `🌐 Загрузить прокси` → FSM `waiting_proxy`
2. Admin sends multiline list:
   ```
   http 85.195.81.148:10772:WUkKKj:fXx0qQ
   socks5 91.108.4.1:1080:user:pass
   ```
3. Bot parses each line: `protocol host:port:login:password`
4. Saves to DB, responds: `✅ Добавлено 5 прокси`

---

## Proxy Service

```python
get_next()       # returns random active Proxy, or raises NoProxyError
mark_failed(id)  # fail_count += 1; if >= 3 → is_active=False
                 # if no active proxies → broadcast_no_proxy() to all users + alert admins
```

`RezkaService` catches `403`/`503` from HdRezkaApi → calls `ProxyService.mark_failed()` → retries with new proxy (max 3 retries).

---

## RezkaService

Wraps HdRezkaApi (sync) via `asyncio.get_event_loop().run_in_executor()` with `ThreadPoolExecutor(max_workers=2)`.

Proxy injected via env vars (`HTTP_PROXY` / `HTTPS_PROXY`) with a threading lock (executor serializes calls).

```python
async def search(query: str) -> list[SearchResult]
async def get_film_info(url: str) -> FilmInfo       # name, poster, type, translators, seasons
async def get_stream_url(url, translation, quality, season, episode) -> str
```

---

## Configuration (.env)

```env
BOT_TOKEN=...
ADMIN_IDS=123456,789012
REZKA_URL=https://hdrezka.ag
DB_PATH=data/bot.db
```

---

## Error Handling

| Error | Action |
|-------|--------|
| 403/504 from HdRezka | rotate proxy, retry (max 3x) |
| No active proxies | user gets "прокси временно закончились" message; admins get alert |
| Film has no stream | user gets "ссылка недоступна" message |
| Search returns 0 results | user gets "ничего не найдено" message |
