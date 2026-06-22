from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QStatusBar

from app.ui.detail_panel import DetailPanel
from app.ui.download_panel import DownloadPanel
from app.ui.search_panel import SearchPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DownloadFilm")
        self.setMinimumSize(900, 600)
        self._build_ui()

    def _build_ui(self) -> None:
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self._search = SearchPanel()
        self._detail = DetailPanel()
        self._downloads = DownloadPanel()

        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self._search)
        top_splitter.addWidget(self._detail)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 1)

        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self._downloads)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)

        self.setCentralWidget(main_splitter)

        self._search.result_selected.connect(self._detail.load)
        self._search.status_message.connect(status_bar.showMessage)
        self._detail.status_message.connect(status_bar.showMessage)
        self._detail.download_requested.connect(self._on_download_requested)
        self._downloads.status_message.connect(status_bar.showMessage)

    def _on_download_requested(
        self,
        url: str,
        translator_id: str,
        quality: str,
        season: int,
        episode: int,
        save_path: str,
    ) -> None:
        self._downloads.add_download(url, translator_id, quality, season, episode, save_path)
