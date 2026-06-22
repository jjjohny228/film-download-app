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

from app import i18n
from app.core.rezka import SearchResult, search
from app.utils.settings import get_rezka_url

CARD_W = 180
CARD_H = 270
CARD_RADIUS = 12
POSTER_PLACEHOLDER = "#1e1e26"
GRID_COLS = 4
GRID_H_SPACING = 14
GRID_V_SPACING = 14


class _MagnifierWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(20, 20)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#6b7280"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(2, 2, 12, 12)
        p.drawLine(12, 12, 18, 18)


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

        p.fillRect(rect, QColor(POSTER_PLACEHOLDER))

        if self._pixmap:
            x = (self._pixmap.width() - rect.width()) // 2
            y = (self._pixmap.height() - rect.height()) // 2
            p.drawPixmap(
                rect,
                self._pixmap,
                QRect(x, y, rect.width(), rect.height()),
            )
        else:
            p.setPen(QColor("#3a3a4a"))
            icon_font = QFont()
            icon_font.setPointSize(32)
            p.setFont(icon_font)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "🎬")

        grad = QLinearGradient(0, rect.height() * 0.45, 0, rect.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 230))
        p.fillRect(rect, grad)

        if self._result.year:
            p.setClipping(False)
            yr_font = QFont()
            yr_font.setPointSize(9)
            p.setFont(yr_font)
            p.setPen(QColor("#9ca3af"))
            yr_rect = QRect(rect.left() + 10, rect.bottom() - 58, rect.width() - 20, 18)
            p.drawText(yr_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       self._result.year)

        p.setClipping(False)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        p.setFont(title_font)
        p.setPen(QColor("#ffffff"))
        title_rect = QRect(rect.left() + 10, rect.bottom() - 48, rect.width() - 20, 44)
        flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom | Qt.TextFlag.TextWordWrap
        p.drawText(title_rect, flags, self._result.title)

        p.setClipping(False)
        pen = QPen(QColor("#3b82f6"), 3) if self._selected else QPen(QColor("#2a2a3a"), 1)
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

        # Search row: [frame: icon + input] [Search button]
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        bar = QFrame()
        bar.setObjectName("searchBar")
        bar.setFixedHeight(48)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 0, 16, 0)
        bar_layout.setSpacing(8)
        bar_layout.addWidget(_MagnifierWidget())

        self._input = QLineEdit()
        self._input.setPlaceholderText(i18n.t("search_placeholder"))
        self._input.setFrame(False)
        self._input.setObjectName("searchInput")
        self._input.returnPressed.connect(self._do_search)
        bar_layout.addWidget(self._input)

        search_row.addWidget(bar, 1)

        self._btn = QPushButton(i18n.t("search_btn"))
        self._btn.setObjectName("searchBtn")
        self._btn.setFixedHeight(48)
        self._btn.clicked.connect(self._do_search)
        search_row.addWidget(self._btn)

        layout.addLayout(search_row)

        self._heading = QLabel(i18n.t("search_results"))
        self._heading.setObjectName("sectionHeading")
        self._heading.setVisible(False)
        layout.addWidget(self._heading)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._cards_container = QWidget()
        self._cards_vbox = QVBoxLayout(self._cards_container)
        self._cards_vbox.setContentsMargins(0, 0, 0, 0)
        self._cards_vbox.setSpacing(GRID_V_SPACING)
        self._cards_vbox.addStretch()
        self._scroll.setWidget(self._cards_container)
        layout.addWidget(self._scroll)

    def retranslate_ui(self) -> None:
        self._input.setPlaceholderText(i18n.t("search_placeholder"))
        self._btn.setText(i18n.t("search_btn"))
        self._heading.setText(i18n.t("search_results"))

    # ── Grid management ─────────────────────────────────────────

    def _clear_layout(self) -> None:
        """Remove all row QHBoxLayouts and stretches from the VBoxLayout."""
        while self._cards_vbox.count():
            item = self._cards_vbox.takeAt(0)
            sub = item.layout()
            if sub:
                while sub.count():
                    sub.takeAt(0)

    def _rebuild_grid(self) -> None:
        self._clear_layout()
        current_row: QHBoxLayout | None = None
        for i, card in enumerate(self._cards):
            if i % GRID_COLS == 0:
                current_row = QHBoxLayout()
                current_row.setSpacing(GRID_H_SPACING)
                current_row.setContentsMargins(0, 0, 0, 0)
                self._cards_vbox.addLayout(current_row)
            current_row.addWidget(card)  # type: ignore[union-attr]
        if current_row is not None:
            current_row.addStretch()
        self._cards_vbox.addStretch()

    def _clear_cards(self) -> None:
        self._clear_layout()
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self._selected_idx = -1
        self._cards_vbox.addStretch()

    # ── Workers ──────────────────────────────────────────────────

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
        self.status_message.emit(i18n.t("searching"))

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
            self.status_message.emit(i18n.t("nothing_found"))
            return

        self._heading.setVisible(True)

        for i, r in enumerate(results):
            card = _FilmCard(i, r)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            if r.poster:
                pw = _PosterWorker(i, r.poster)
                pw.pixmap_ready.connect(self._on_pixmap)
                self._poster_workers.append(pw)
                pw.start()

        self._rebuild_grid()
        self.status_message.emit(i18n.t("found", n=len(results)))

    def _on_pixmap(self, index: int, px: QPixmap) -> None:
        if 0 <= index < len(self._cards):
            self._cards[index].set_pixmap(px)

    def _on_card_clicked(self, index: int) -> None:
        if 0 <= self._selected_idx < len(self._cards):
            self._cards[self._selected_idx].set_selected(False)
        self._selected_idx = index
        self._cards[index].set_selected(True)
        self.result_selected.emit(self._results[index])

    def _on_error(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.status_message.emit(i18n.t("error_msg", msg=msg))
