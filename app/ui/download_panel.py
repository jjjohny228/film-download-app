import os
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app import i18n
from app.core.downloader import DownloadWorker
from app.core.rezka import get_stream_url


class _ResolveWorker(QThread):
    url_ready = Signal(str, str)  # stream_url, save_path
    error = Signal(str)

    def __init__(self, page_url: str, translator_id: str, quality: str,
                 season: int, episode: int, save_path: str) -> None:
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
                self._page_url, self._translator_id, self._quality,
                self._season, self._episode,
            )
            self.url_ready.emit(stream_url, self._save_path)
        except Exception as e:
            self.error.emit(str(e))


class _DownloadRow(QWidget):
    cancel_clicked = Signal()

    def __init__(self, filename: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadRow")
        self._is_done = False
        self._badge_key = "waiting"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(10)

        self._name_lbl = QLabel(filename)
        self._name_lbl.setObjectName("dlFilename")
        self._name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(self._name_lbl, 1)

        self._status_badge = QLabel(i18n.t("waiting"))
        self._status_badge.setObjectName("dlBadge")
        self._status_badge.setFixedHeight(22)
        top.addWidget(self._status_badge)

        self._size_lbl = QLabel("")
        self._size_lbl.setObjectName("dlSize")
        top.addWidget(self._size_lbl)

        self._pause_btn = QPushButton("⏸")
        self._pause_btn.setObjectName("dlActionBtn")
        self._pause_btn.setFixedSize(28, 28)
        self._pause_btn.setToolTip("Pause / Resume")
        top.addWidget(self._pause_btn)

        self._cancel_btn = QPushButton("✕")
        self._cancel_btn.setObjectName("dlCancelBtn")
        self._cancel_btn.setFixedSize(28, 28)
        self._cancel_btn.clicked.connect(self.cancel_clicked)
        top.addWidget(self._cancel_btn)

        outer.addLayout(top)

        self._bar = QProgressBar()
        self._bar.setObjectName("dlBar")
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(4)
        self._bar.setTextVisible(False)
        outer.addWidget(self._bar)

    def _apply_badge(self, key: str, obj_name: str) -> None:
        self._badge_key = key
        self._status_badge.setText(i18n.t(key))
        self._status_badge.setObjectName(obj_name)
        self._status_badge.style().unpolish(self._status_badge)
        self._status_badge.style().polish(self._status_badge)

    def set_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            self._bar.setValue(int(downloaded / total * 100))
        mb_d = downloaded / 1024 / 1024
        mb_t = total / 1024 / 1024
        self._size_lbl.setText(f"{mb_d:.1f} / {mb_t:.1f} MB")
        self._apply_badge("downloading", "dlBadgeActive")

    def set_paused(self, paused: bool) -> None:
        self._pause_btn.setText("▶" if paused else "⏸")
        if paused:
            self._apply_badge("paused", "dlBadgePaused")
        else:
            self._apply_badge("downloading", "dlBadgeActive")

    def set_done(self) -> None:
        self._is_done = True
        self._bar.setValue(100)
        self._apply_badge("done", "dlBadgeDone")
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

    def set_error(self, msg: str) -> None:
        self._apply_badge("error", "dlBadgeError")
        self._name_lbl.setText(f"{self._name_lbl.text()} — {msg}")
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

    def retranslate_ui(self) -> None:
        if self._badge_key in ("waiting", "downloading", "paused", "done"):
            self._status_badge.setText(i18n.t(self._badge_key))

    def connect_pause(self, slot: "Callable") -> None:
        self._pause_btn.clicked.connect(slot)

    @property
    def is_done(self) -> bool:
        return self._is_done


class DownloadPanel(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("downloadPanel")
        self._workers: list[tuple[_DownloadRow, DownloadWorker | _ResolveWorker]] = []
        self._rows: list[_DownloadRow] = []
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 12, 20, 12)
        outer.setSpacing(8)

        header = QHBoxLayout()
        self._header_lbl = QLabel(i18n.t("active_downloads", n=0))
        self._header_lbl.setObjectName("dlHeader")
        header.addWidget(self._header_lbl)
        header.addStretch()
        self._clear_btn = QPushButton(i18n.t("clear_finished"))
        self._clear_btn.setObjectName("linkBtn")
        self._clear_btn.setFlat(True)
        self._clear_btn.clicked.connect(self._clear_finished)
        header.addWidget(self._clear_btn)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        self._rows_layout = QVBoxLayout(container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        self._rows_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def retranslate_ui(self) -> None:
        self._update_header()
        self._clear_btn.setText(i18n.t("clear_finished"))
        for row in self._rows:
            row.retranslate_ui()

    def _update_header(self) -> None:
        active = sum(
            1 for _, w in self._workers
            if isinstance(w, DownloadWorker) and w.isRunning() and not w.is_paused
        )
        self._header_lbl.setText(i18n.t("active_downloads", n=active))

    def _clear_finished(self) -> None:
        for row, _ in list(self._workers):
            if row.is_done:
                self._rows_layout.removeWidget(row)
                row.deleteLater()
                if row in self._rows:
                    self._rows.remove(row)
        self._workers = [(r, w) for r, w in self._workers if not r.is_done]

    def add_download(self, page_url: str, translator_id: str, quality: str,
                     season: int, episode: int, save_path: str) -> None:
        filename = os.path.basename(save_path)
        row = _DownloadRow(filename)
        self._rows.append(row)
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)

        resolver = _ResolveWorker(page_url, translator_id, quality, season, episode, save_path)

        def on_url_ready(stream_url: str, sp: str) -> None:
            resolver.url_ready.disconnect(on_url_ready)

            dl = DownloadWorker(stream_url, sp)
            dl.progress.connect(row.set_progress)
            dl.progress.connect(lambda *_: self._update_header())

            def _on_finished(p: str) -> None:
                row.set_done()
                self.status_message.emit(i18n.t("downloaded", name=os.path.basename(p)))
                self._workers[:] = [(r, w) for r, w in self._workers if w is not dl]
                self._update_header()

            def _on_error(msg: str) -> None:
                row.set_error(msg)
                self._workers[:] = [(r, w) for r, w in self._workers if w is not dl]
                self._update_header()

            dl.finished.connect(_on_finished)
            dl.error.connect(_on_error)
            self._workers.append((row, dl))

            def _toggle_pause() -> None:
                if dl.is_paused:
                    dl.resume()
                    row.set_paused(False)
                else:
                    dl.pause()
                    row.set_paused(True)
                self._update_header()

            row.connect_pause(_toggle_pause)

            def _on_cancel() -> None:
                dl.cancel()
                row.set_error(i18n.t("cancelled"))
                self._workers[:] = [(r, w) for r, w in self._workers if w is not dl]
                self._update_header()

            row.cancel_clicked.connect(_on_cancel)
            dl.start()
            self._update_header()

        def on_error(msg: str) -> None:
            row.set_error(msg)
            self.status_message.emit(i18n.t("link_error", msg=msg))
            self._workers[:] = [(r, w) for r, w in self._workers if w is not resolver]
            self._update_header()

        resolver.url_ready.connect(on_url_ready)
        resolver.error.connect(on_error)
        self._workers.append((row, resolver))
        resolver.start()
        self.status_message.emit(i18n.t("fetching_link", name=filename))
        self._update_header()
