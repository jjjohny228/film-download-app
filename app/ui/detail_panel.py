import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.rezka import FilmInfo, SearchResult, get_film_info
from app.utils.settings import get_download_folder, set_download_folder

QUALITIES = ["1080p", "720p", "480p", "360p"]


class _InfoWorker(QThread):
    info_ready = Signal(object)  # FilmInfo
    error = Signal(str)

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url

    def run(self) -> None:
        try:
            self.info_ready.emit(get_film_info(self._url))
        except Exception as e:
            self.error.emit(str(e))


class DetailPanel(QWidget):
    download_requested = Signal(str, str, str, int, int, str)
    # url, translator_id, quality, season, episode, save_path
    status_message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_url: str = ""
        self._info: FilmInfo | None = None
        self._worker: _InfoWorker | None = None
        self.setObjectName("detailCard")
        self.setFixedWidth(380)
        self._build_ui()
        self._set_enabled(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        # "NOW SELECTING" header
        now_label = QLabel("NOW SELECTING")
        now_label.setObjectName("nowSelecting")
        layout.addWidget(now_label)
        layout.addSpacing(6)

        # Title
        self._title_label = QLabel("—")
        self._title_label.setObjectName("detailTitle")
        self._title_label.setWordWrap(True)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        layout.addWidget(self._title_label)
        layout.addSpacing(20)

        # Translator
        tr_label = QLabel("Dubbing / Translation")
        tr_label.setObjectName("fieldLabel")
        layout.addWidget(tr_label)
        layout.addSpacing(6)
        self._translator_combo = QComboBox()
        self._translator_combo.setObjectName("detailCombo")
        self._translator_combo.setFixedHeight(44)
        layout.addWidget(self._translator_combo)
        layout.addSpacing(16)

        # Season + Episode side by side
        se_row = QHBoxLayout()
        se_row.setSpacing(12)

        season_col = QVBoxLayout()
        self._season_label = QLabel("Season")
        self._season_label.setObjectName("fieldLabel")
        self._season_combo = QComboBox()
        self._season_combo.setObjectName("detailCombo")
        self._season_combo.setFixedHeight(44)
        self._season_combo.currentIndexChanged.connect(self._on_season_changed)
        season_col.addWidget(self._season_label)
        season_col.addSpacing(6)
        season_col.addWidget(self._season_combo)

        episode_col = QVBoxLayout()
        self._episode_label = QLabel("Episode")
        self._episode_label.setObjectName("fieldLabel")
        self._episode_combo = QComboBox()
        self._episode_combo.setObjectName("detailCombo")
        self._episode_combo.setFixedHeight(44)
        episode_col.addWidget(self._episode_label)
        episode_col.addSpacing(6)
        episode_col.addWidget(self._episode_combo)

        se_row.addLayout(season_col)
        se_row.addLayout(episode_col)
        self._se_widget = QWidget()
        self._se_widget.setLayout(se_row)
        layout.addWidget(self._se_widget)
        layout.addSpacing(16)

        # Quality
        q_label = QLabel("Quality")
        q_label.setObjectName("fieldLabel")
        layout.addWidget(q_label)
        layout.addSpacing(8)

        q_row = QHBoxLayout()
        q_row.setSpacing(8)
        self._quality_group = QButtonGroup(self)
        self._quality_btns: dict[str, QPushButton] = {}
        for q in QUALITIES:
            btn = QPushButton(q)
            btn.setObjectName("qualityBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            if q == "1080p":
                btn.setChecked(True)
            self._quality_group.addButton(btn)
            self._quality_btns[q] = btn
            q_row.addWidget(btn)
        layout.addLayout(q_row)
        layout.addSpacing(20)

        # Save path row
        save_row = QHBoxLayout()
        save_label = QLabel("Save to:")
        save_label.setObjectName("fieldLabel")
        self._folder_label = QLabel(get_download_folder())
        self._folder_label.setObjectName("folderPath")
        self._folder_label.setWordWrap(False)
        change_btn = QPushButton("Change")
        change_btn.setObjectName("linkBtn")
        change_btn.setFlat(True)
        change_btn.clicked.connect(self._pick_folder)
        save_row.addWidget(save_label)
        save_row.addWidget(self._folder_label, 1)
        save_row.addWidget(change_btn)
        layout.addLayout(save_row)
        layout.addSpacing(16)

        # Download button
        self._download_btn = QPushButton("⬇  Download Now")
        self._download_btn.setObjectName("downloadBtn")
        self._download_btn.setFixedHeight(52)
        self._download_btn.clicked.connect(self._on_download)
        layout.addWidget(self._download_btn)
        layout.addStretch()

    def _set_enabled(self, enabled: bool) -> None:
        for w in [self._translator_combo, self._season_combo,
                  self._episode_combo, self._download_btn]:
            w.setEnabled(enabled)
        for btn in self._quality_group.buttons():
            btn.setEnabled(enabled)

    def load(self, result: SearchResult) -> None:
        self._set_enabled(False)
        self._current_url = result.url
        self._title_label.setText(result.title)
        self._translator_combo.clear()
        self._season_combo.clear()
        self._episode_combo.clear()
        self.status_message.emit("Loading info…")

        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait()

        self._worker = _InfoWorker(result.url)
        self._worker.info_ready.connect(self._on_info_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_info_ready(self, info: FilmInfo) -> None:
        self._info = info
        self._translator_combo.clear()
        for name in info.translators:
            self._translator_combo.addItem(name)

        has_seasons = info.is_series and bool(info.seasons)
        self._se_widget.setVisible(has_seasons)

        if has_seasons:
            self._season_combo.clear()
            for s in sorted(info.seasons):
                self._season_combo.addItem(f"Season {s}", s)
            self._on_season_changed(0)

        self._set_enabled(True)
        self.status_message.emit("Ready")

    def _on_error(self, msg: str) -> None:
        self.status_message.emit(f"Error: {msg}")

    def _on_season_changed(self, _: int) -> None:
        if self._info is None:
            return
        season = self._season_combo.currentData()
        if season is None:
            return
        self._episode_combo.clear()
        for ep in sorted(self._info.seasons.get(season, [])):
            self._episode_combo.addItem(f"Episode {ep}", ep)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select download folder", get_download_folder()
        )
        if folder:
            set_download_folder(folder)
            self._folder_label.setText(folder)

    def _selected_quality(self) -> str:
        btn = self._quality_group.checkedButton()
        return btn.text() if btn else "720p"

    def _on_download(self) -> None:
        if self._info is None:
            return
        translator_name = self._translator_combo.currentText()
        translator_id = self._info.translators.get(translator_name, "")
        quality = self._selected_quality()
        season = self._season_combo.currentData() or 0
        episode = self._episode_combo.currentData() or 0
        folder = get_download_folder()

        if self._info.is_series and season and episode:
            filename = f"{self._info.name}_S{season:02d}E{episode:02d}_{quality}.mp4"
        else:
            filename = f"{self._info.name}_{quality}.mp4"

        filename = "".join(c if c.isalnum() or c in " _-.()" else "_" for c in filename)
        save_path = os.path.join(folder, filename)

        self.download_requested.emit(
            self._current_url, translator_id, quality, season, episode, save_path
        )
