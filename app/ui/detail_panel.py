import os

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
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
        self._build_ui()
        self._set_enabled(False)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._title_label = QLabel("—")
        form.addRow("Название:", self._title_label)

        self._translator_combo = QComboBox()
        self._translator_combo.currentIndexChanged.connect(self._on_translator_changed)
        form.addRow("Перевод:", self._translator_combo)

        self._season_combo = QComboBox()
        self._season_combo.currentIndexChanged.connect(self._on_season_changed)
        self._season_label = QLabel("Сезон:")
        form.addRow(self._season_label, self._season_combo)

        self._episode_combo = QComboBox()
        self._episode_label = QLabel("Серия:")
        form.addRow(self._episode_label, self._episode_combo)

        layout.addLayout(form)

        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Качество:"))
        self._quality_group = QButtonGroup(self)
        for q in QUALITIES:
            rb = QRadioButton(q)
            if q == "1080p":
                rb.setChecked(True)
            self._quality_group.addButton(rb)
            quality_layout.addWidget(rb)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)

        folder_layout = QHBoxLayout()
        self._folder_label = QLabel(get_download_folder())
        self._folder_label.setWordWrap(True)
        folder_btn = QPushButton("Изменить…")
        folder_btn.clicked.connect(self._pick_folder)
        folder_layout.addWidget(QLabel("Папка:"))
        folder_layout.addWidget(self._folder_label, 1)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)

        self._download_btn = QPushButton("▼ Скачать")
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
        self.status_message.emit("Загрузка информации…")

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
        self._season_label.setVisible(has_seasons)
        self._season_combo.setVisible(has_seasons)
        self._episode_label.setVisible(has_seasons)
        self._episode_combo.setVisible(has_seasons)

        if has_seasons:
            self._season_combo.clear()
            for s in sorted(info.seasons):
                self._season_combo.addItem(str(s), s)
            self._on_season_changed(0)

        self._set_enabled(True)
        self.status_message.emit("Готово")

    def _on_error(self, msg: str) -> None:
        self.status_message.emit(f"Ошибка: {msg}")

    def _on_translator_changed(self, _: int) -> None:
        pass  # future: reload seasons per translator if needed

    def _on_season_changed(self, _: int) -> None:
        if self._info is None:
            return
        season = self._season_combo.currentData()
        if season is None:
            return
        self._episode_combo.clear()
        for ep in sorted(self._info.seasons.get(season, [])):
            self._episode_combo.addItem(str(ep), ep)

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку для загрузки", get_download_folder()
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
