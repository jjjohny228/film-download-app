import httpx
from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.rezka import SearchResult, search
from app.utils.settings import get_rezka_url

POSTER_W = 90
POSTER_H = 130
ITEM_H = POSTER_H + 10


class _SearchWorker(QThread):
    results_ready = Signal(list)
    error = Signal(str)

    def __init__(self, query: str, base_url: str) -> None:
        super().__init__()
        self._query = query
        self._base_url = base_url

    def run(self) -> None:
        try:
            self.results_ready.emit(search(self._query, self._base_url))
        except Exception as e:
            self.error.emit(str(e))


class _PosterWorker(QThread):
    pixmap_ready = Signal(int, QPixmap)  # index, pixmap

    def __init__(self, index: int, url: str) -> None:
        super().__init__()
        self._index = index
        self._url = url

    def run(self) -> None:
        try:
            resp = httpx.get(self._url, follow_redirects=True, timeout=10)
            px = QPixmap()
            px.loadFromData(resp.content)
            if not px.isNull():
                self.pixmap_ready.emit(self._index, px)
        except Exception:
            pass


class SearchPanel(QWidget):
    result_selected = Signal(object)  # SearchResult
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[SearchResult] = []
        self._worker: _SearchWorker | None = None
        self._poster_workers: list[_PosterWorker] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(8)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Введите название фильма или сериала…")
        self._input.setMinimumHeight(36)
        self._input.returnPressed.connect(self._do_search)
        self._btn = QPushButton("Найти")
        self._btn.setMinimumHeight(36)
        self._btn.setMinimumWidth(80)
        self._btn.clicked.connect(self._do_search)
        row.addWidget(self._input)
        row.addWidget(self._btn)
        layout.addLayout(row)

        self._list = QListWidget()
        self._list.setIconSize(QSize(POSTER_W, POSTER_H))
        self._list.setSpacing(4)
        self._list.setUniformItemSizes(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

    def _stop_poster_workers(self) -> None:
        for w in self._poster_workers:
            if w.isRunning():
                w.quit()
                w.wait()
        self._poster_workers.clear()

    def _do_search(self) -> None:
        query = self._input.text().strip()
        if not query:
            return
        self._btn.setEnabled(False)
        self._list.clear()
        self._results = []
        self._stop_poster_workers()
        self.status_message.emit("Поиск…")

        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

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

        for i, r in enumerate(results):
            tag = "📺" if r.is_series else "🎬"
            year = f" ({r.year})" if r.year else ""
            item = QListWidgetItem(f"{tag} {r.title}{year}")
            item.setSizeHint(QSize(0, ITEM_H))
            self._list.addItem(item)

            if r.poster:
                pw = _PosterWorker(i, r.poster)
                pw.pixmap_ready.connect(self._on_pixmap)
                self._poster_workers.append(pw)
                pw.start()

        self.status_message.emit(f"Найдено: {len(results)}")

    def _on_pixmap(self, index: int, px: QPixmap) -> None:
        if 0 <= index < self._list.count():
            scaled = px.scaled(
                POSTER_W, POSTER_H,
                aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                mode=Qt.TransformationMode.SmoothTransformation,
            )
            self._list.item(index).setIcon(QIcon(scaled))

    def _on_error(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.status_message.emit(f"Ошибка: {msg}")

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        idx = self._list.row(item)
        if 0 <= idx < len(self._results):
            self.result_selected.emit(self._results[idx])
