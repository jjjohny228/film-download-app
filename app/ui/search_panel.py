from PySide6.QtCore import QThread, Signal
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
