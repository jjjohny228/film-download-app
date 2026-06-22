import pytest


def test_admin_ids_parsed_from_string(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.setenv("ADMIN_IDS", "111,222,333")
    from bot.config import Settings
    s = Settings()
    assert s.admin_ids == [111, 222, 333]


def test_admin_ids_empty_by_default(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    monkeypatch.delenv("ADMIN_IDS", raising=False)
    from bot.config import Settings
    s = Settings()
    assert s.admin_ids == []


def test_rezka_url_default(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test:token")
    from bot.config import Settings
    s = Settings()
    assert s.REZKA_URL == "https://hdrezka.ag"
