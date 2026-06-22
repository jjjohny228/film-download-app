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
