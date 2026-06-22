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
