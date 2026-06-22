from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.detail_panel import DetailPanel
from app.ui.download_panel import DownloadPanel
from app.ui.search_panel import SearchPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DownloadFilm")
        self.setMinimumSize(1000, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(56)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 0, 20, 0)
        top_bar_layout.addStretch()

        logo_icon = QLabel("⬇")
        logo_icon.setObjectName("logoIcon")
        logo_font = QFont()
        logo_font.setPointSize(16)
        logo_icon.setFont(logo_font)

        logo_text = QLabel("DownloadFilm")
        logo_text.setObjectName("logoText")
        logo_font2 = QFont()
        logo_font2.setPointSize(15)
        logo_font2.setBold(True)
        logo_text.setFont(logo_font2)

        top_bar_layout.addWidget(logo_icon)
        top_bar_layout.addSpacing(6)
        top_bar_layout.addWidget(logo_text)

        root_layout.addWidget(top_bar)

        # ── Content area ─────────────────────────────────────────
        self._search = SearchPanel()
        self._detail = DetailPanel()
        self._detail.setVisible(False)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._search, 1)
        content_layout.addWidget(self._detail)

        # ── Downloads ────────────────────────────────────────────
        self._downloads = DownloadPanel()
        self._downloads.setFixedHeight(190)

        # ── Splitter: content / downloads ────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(content)
        splitter.addWidget(self._downloads)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 190])
        splitter.setHandleWidth(1)

        root_layout.addWidget(splitter, 1)
        self.setCentralWidget(root)

        # ── Signals ──────────────────────────────────────────────
        self._search.result_selected.connect(self._on_result_selected)
        self._search.status_message.connect(status_bar.showMessage)
        self._detail.status_message.connect(status_bar.showMessage)
        self._detail.download_requested.connect(self._on_download_requested)
        self._downloads.status_message.connect(status_bar.showMessage)

    def _on_result_selected(self, result) -> None:
        if not self._detail.isVisible():
            self._detail.setVisible(True)
        self._detail.load(result)

    def _on_download_requested(self, url: str, translator_id: str, quality: str,
                               season: int, episode: int, save_path: str) -> None:
        self._downloads.add_download(url, translator_id, quality, season, episode, save_path)
