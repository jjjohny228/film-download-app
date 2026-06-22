import httpx
from PySide6.QtCore import QRect, Qt, QThread, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.rezka import SearchResult, search
from app.utils.settings import get_rezka_url

CARD_W = 180
CARD_H = 270
CARD_RADIUS = 12
POSTER_PLACEHOLDER = "#1e1e26"


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
    pixmap_ready = Signal(int, QPixmap)

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


class _FilmCard(QWidget):
    clicked = Signal(int)

    def __init__(self, index: int, result: SearchResult, parent=None) -> None:
        super().__init__(parent)
        self._index = index
        self._result = result
        self._pixmap: QPixmap | None = None
        self._selected = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_pixmap(self, px: QPixmap) -> None:
        self._pixmap = px.scaled(
            CARD_W, CARD_H,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.update()

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._index)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)

        path = QPainterPath()
        path.addRoundedRect(rect, CARD_RADIUS, CARD_RADIUS)
        p.setClipPath(path)

        # background
        p.fillRect(rect, QColor(POSTER_PLACEHOLDER))

        # poster image
        if self._pixmap:
            x = (self._pixmap.width() - rect.width()) // 2
            y = (self._pixmap.height() - rect.height()) // 2
            p.drawPixmap(
                rect,
                self._pixmap,
                QRect(x, y, rect.width(), rect.height()),
            )
        else:
            # placeholder icon
            p.setPen(QColor("#3a3a4a"))
            icon_font = QFont()
            icon_font.setPointSize(32)
            p.setFont(icon_font)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎬")

        # bottom gradient overlay
        grad = QLinearGradient(0, rect.height() * 0.45, 0, rect.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 230))
        p.fillRect(rect, grad)

        # year (small, muted)
        if self._result.year:
            p.setClipping(False)
            yr_font = QFont()
            yr_font.setPointSize(9)
            p.setFont(yr_font)
            p.setPen(QColor("#9ca3af"))
            yr_rect = QRect(rect.left() + 10, rect.bottom() - 58, rect.width() - 20, 18)
            p.drawText(yr_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       self._result.year)

        # title
        p.setClipping(False)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(QColor("#ffffff"))
        title_rect = QRect(rect.left() + 10, rect.bottom() - 48, rect.width() - 20, 44)
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap
        p.drawText(title_rect, flags, self._result.title)

        # selected border
        p.setClipping(False)
        if self._selected:
            pen = QPen(QColor("#3b82f6"), 3)
        else:
            pen = QPen(QColor("#2a2a3a"), 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        full_rect = self.rect().adjusted(1, 1, -1, -1)
        p.drawRoundedRect(full_rect, CARD_RADIUS + 1, CARD_RADIUS + 1)


class SearchPanel(QWidget):
    result_selected = Signal(object)   # SearchResult
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[SearchResult] = []
        self._cards: list[_FilmCard] = []
        self._selected_idx: int = -1
        self._worker: _SearchWorker | None = None
        self._poster_workers: list[_PosterWorker] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        # Search bar
        bar = QFrame()
        bar.setObjectName("searchBar")
        bar.setFixedHeight(48)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 0, 8, 0)
        bar_layout.setSpacing(8)

        icon_lbl = QLabel("🔍")
        icon_lbl.setFixedWidth(20)
        bar_layout.addWidget(icon_lbl)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Search for movies, series…")
        self._input.setFrame(False)
        self._input.setObjectName("searchInput")
        self._input.returnPressed.connect(self._do_search)
        bar_layout.addWidget(self._input)

        self._btn = QPushButton("Search")
        self._btn.setObjectName("searchBtn")
        self._btn.setFixedHeight(34)
        self._btn.clicked.connect(self._do_search)
        bar_layout.addWidget(self._btn)

        layout.addWidget(bar)

        # Heading
        self._heading = QLabel("Search Results")
        self._heading.setObjectName("sectionHeading")
        self._heading.setVisible(False)
        layout.addWidget(self._heading)

        # Cards scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._cards_container = QWidget()
        self._cards_layout = _FlowLayout(self._cards_container, h_spacing=14, v_spacing=14)
        self._scroll.setWidget(self._cards_container)
        layout.addWidget(self._scroll)

    def _clear_cards(self) -> None:
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._selected_idx = -1

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
        self._clear_cards()
        self._stop_poster_workers()
        self._results = []
        self.status_message.emit("Searching…")

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
        self._clear_cards()

        if not results:
            self._heading.setVisible(False)
            self.status_message.emit("Nothing found")
            return

        self._heading.setVisible(True)

        for i, r in enumerate(results):
            card = _FilmCard(i, r)
            card.clicked.connect(self._on_card_clicked)
            self._cards_layout.addWidget(card)
            self._cards.append(card)

            if r.poster:
                pw = _PosterWorker(i, r.poster)
                pw.pixmap_ready.connect(self._on_pixmap)
                self._poster_workers.append(pw)
                pw.start()

        self.status_message.emit(f"Found: {len(results)}")

    def _on_pixmap(self, index: int, px: QPixmap) -> None:
        if 0 <= index < len(self._cards):
            self._cards[index].set_pixmap(px)

    def _on_card_clicked(self, index: int) -> None:
        if self._selected_idx >= 0 and self._selected_idx < len(self._cards):
            self._cards[self._selected_idx].set_selected(False)
        self._selected_idx = index
        self._cards[index].set_selected(True)
        self.result_selected.emit(self._results[index])

    def _on_error(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.status_message.emit(f"Error: {msg}")


class _FlowLayout(QVBoxLayout):
    """Simple wrapping grid layout using multiple QHBoxLayout rows."""

    def __init__(self, parent: QWidget, h_spacing: int = 10, v_spacing: int = 10) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(v_spacing)
        self._h_spacing = h_spacing
        self._widgets: list[QWidget] = []
        self._row_layouts: list[QHBoxLayout] = []
        self._build_row()

    def _build_row(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(self._h_spacing)
        row.setContentsMargins(0, 0, 0, 0)
        self._row_layouts.append(row)
        self.addLayout(row)

    def addWidget(self, widget: QWidget) -> None:  # noqa: N802
        self._widgets.append(widget)
        self._relayout()

    def removeWidget(self, widget: QWidget) -> None:  # noqa: N802
        if widget in self._widgets:
            self._widgets.remove(widget)

    def _relayout(self) -> None:
        # Clear rows
        for row in self._row_layouts:
            while row.count():
                item = row.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)  # type: ignore[arg-type]
        for i in reversed(range(len(self._row_layouts))):
            row = self._row_layouts.pop(i)
            self.removeItem(row)

        self._row_layouts.clear()
        self._build_row()

        # Distribute widgets across rows (4 per row)
        cols = 4
        for idx, widget in enumerate(self._widgets):
            if idx > 0 and idx % cols == 0:
                self._build_row()
            self._row_layouts[-1].addWidget(widget)

        # Fill last row with stretch
        if self._row_layouts:
            self._row_layouts[-1].addStretch()

        self.addStretch()
