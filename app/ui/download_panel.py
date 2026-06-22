import os
from collections.abc import Callable

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
        layout.setContentsMargins(8, 6, 8, 6)

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

    def connect_cancel(self, slot: "Callable") -> None:
        self._cancel_btn.clicked.connect(slot)


class DownloadPanel(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._workers: list[tuple[_DownloadRow, DownloadWorker | _ResolveWorker]] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)
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
        filename = os.path.basename(save_path)
        row = _DownloadRow(filename)
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

        resolver = _ResolveWorker(page_url, translator_id, quality, season, episode, save_path)

        def on_url_ready(stream_url: str, sp: str) -> None:
            # Disconnect to prevent double-emit
            resolver.url_ready.disconnect(on_url_ready)

            dl = DownloadWorker(stream_url, sp)
            dl.progress.connect(row.set_progress)

            def _on_finished(p: str) -> None:
                row.set_done()
                self.status_message.emit(f"Скачано: {os.path.basename(p)}")
                self._workers[:] = [(r, w) for r, w in self._workers if w is not dl]

            def _on_error(msg: str) -> None:
                row.set_error(msg)
                self._workers[:] = [(r, w) for r, w in self._workers if w is not dl]

            dl.finished.connect(_on_finished)
            dl.error.connect(_on_error)
            self._workers.append((row, dl))
            row.connect_cancel(dl.cancel)
            dl.start()

        def on_error(msg: str) -> None:
            row.set_error(msg)
            self.status_message.emit(f"Ошибка получения ссылки: {msg}")
            self._workers[:] = [(r, w) for r, w in self._workers if w is not resolver]

        resolver.url_ready.connect(on_url_ready)
        resolver.error.connect(on_error)
        self._workers.append((row, resolver))
        resolver.start()
        self.status_message.emit(f"Получение ссылки для {filename}…")
