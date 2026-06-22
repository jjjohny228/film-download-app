# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run the app
uv run python -m app.main

# Lint (check)
uv run ruff check app/ tests/

# Lint (fix)
uv run ruff check app/ tests/ --fix

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_rezka.py -v

# Run a single test by name
uv run pytest tests/test_rezka.py::test_search_returns_list -v

# Build distributable (produces dist/DownloadFilm or dist/DownloadFilm.app on macOS)
uv run pyinstaller download_film.spec
```

## Architecture

This is a PySide6 desktop app (not a Telegram bot — the README is outdated). Entry point: `app/main.py`.

### Thread model

All HdRezkaApi and httpx calls run on `QThread` workers — never on the main thread. Signals carry results back to the UI. The pattern used throughout:

```
QThread subclass → run() does blocking work → emits signal → UI slot updates widgets
```

Workers in play:
- `_SearchWorker` — calls `rezka.search()`
- `_PosterWorker` — downloads poster image via httpx
- `_InfoWorker` — calls `rezka.get_film_info()`
- `_ResolveWorker` — calls `rezka.get_stream_url()` to get the CDN link
- `DownloadWorker` — streams the file via httpx with pause/resume via `threading.Event`

### Download flow

`DetailPanel` emits `download_requested(url, translator_id, quality, season, episode, save_path)` → `DownloadPanel.add_download()` creates a `_ResolveWorker` first (to get the CDN stream URL), then on success creates a `DownloadWorker`. The `_workers` list tracks `(row, worker)` tuples and prunes finished/cancelled entries to avoid leaks.

### Key HdRezka quirks

- `get_stream_url()` guard: use `if season > 0 and episode > 0:` not `if season and episode:` — season 1 episode 0 is a valid edge case.
- `film.translators` returns `{int_id: {"name": str, "premium": bool}}` — convert to `{name: str(id)}` for the UI.
- `film.seriesInfo` structure: `{translator_id: {"seasons": {str: str}, "episodes": {str_season: {str_ep: str}}}}`.

### i18n

`app/i18n.py` has a `t(key, **kwargs) -> str` function. Language (en/ru/uk) is stored via `QSettings` and loaded at startup via `i18n.init()`. When language changes, `MainWindow._change_language()` calls `retranslate_ui()` on all three panels. All user-visible strings must go through `t()`.

### Settings persistence

`app/utils/settings.py` wraps `QSettings` with org/app name `"MovieDownloader"`. Module-level `_ORG` and `_APP` constants exist for test isolation (monkeypatching them in tests uses a separate QSettings namespace).

### Packaging

`download_film.spec` (PyInstaller 6.x) builds a single-file executable. No `cipher=` param — that was removed in PyInstaller 6. macOS gets a `.app` bundle via `BUNDLE`. `console=False` suppresses the terminal window.
