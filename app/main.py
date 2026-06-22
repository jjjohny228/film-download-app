import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow

STYLESHEET = """
/* ── Base ───────────────────────────────────────────── */
QWidget {
    background-color: #0d0d0f;
    color: #e5e7eb;
    font-family: -apple-system, "Segoe UI", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

/* ── Top bar ─────────────────────────────────────────── */
QWidget#topBar {
    background-color: #0d0d0f;
    border-bottom: 1px solid #1f1f27;
}
QLabel#logoIcon  { color: #3b82f6; }
QLabel#logoText  { color: #ffffff; }

/* ── Search bar frame ────────────────────────────────── */
QFrame#searchBar {
    background-color: #1a1a24;
    border: 1px solid #2a2a38;
    border-radius: 24px;
}
QLineEdit#searchInput {
    background: transparent;
    border: none;
    color: #ffffff;
    font-size: 14px;
    padding: 0px;
    selection-background-color: #3b82f6;
}
QLineEdit#searchInput::placeholder { color: #6b7280; }

/* ── Buttons ─────────────────────────────────────────── */
QPushButton#searchBtn {
    background: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 18px;
    padding: 0px 20px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#searchBtn:hover   { background: #2563eb; }
QPushButton#searchBtn:pressed { background: #1d4ed8; }
QPushButton#searchBtn:disabled { background: #1f2937; color: #4b5563; }

QPushButton#downloadBtn {
    background: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    font-size: 15px;
}
QPushButton#downloadBtn:hover   { background: #2563eb; }
QPushButton#downloadBtn:pressed { background: #1d4ed8; }
QPushButton#downloadBtn:disabled { background: #1f2937; color: #4b5563; }

QPushButton#linkBtn {
    background: transparent;
    color: #3b82f6;
    border: none;
    font-size: 12px;
    padding: 0px 4px;
}
QPushButton#linkBtn:hover { color: #60a5fa; }

/* ── Quality pill buttons ────────────────────────────── */
QPushButton#qualityBtn {
    background: transparent;
    color: #9ca3af;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 0px 10px;
    font-weight: 500;
}
QPushButton#qualityBtn:checked {
    background: #3b82f6;
    border-color: #3b82f6;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#qualityBtn:hover:!checked { border-color: #4b5563; color: #d1d5db; }

/* ── Detail card ─────────────────────────────────────── */
QWidget#detailCard {
    background-color: #13131a;
    border-left: 1px solid #1f1f2e;
}
QLabel#nowSelecting {
    color: #3b82f6;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#detailTitle { color: #ffffff; }
QLabel#fieldLabel  { color: #9ca3af; font-size: 12px; font-weight: 600; }
QLabel#folderPath  { color: #d1d5db; font-size: 11px; }

/* ── Dropdowns ───────────────────────────────────────── */
QComboBox#detailCombo {
    background: #1a1a24;
    border: 1px solid #2a2a38;
    border-radius: 10px;
    padding: 0px 14px;
    color: #ffffff;
    font-size: 13px;
}
QComboBox#detailCombo::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 24px;
    border: none;
}
QComboBox#detailCombo::down-arrow { image: none; width: 0; }
QComboBox#detailCombo:hover { border-color: #374151; }
QComboBox QAbstractItemView {
    background: #1a1a24;
    border: 1px solid #2a2a38;
    border-radius: 8px;
    color: #ffffff;
    selection-background-color: #3b82f6;
    padding: 4px;
}

/* ── Download panel ──────────────────────────────────── */
QWidget#downloadPanel {
    background-color: #0d0d0f;
    border-top: 1px solid #1f1f27;
}
QLabel#dlHeader {
    color: #6b7280;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}
QWidget#downloadRow {
    background-color: #13131a;
    border: 1px solid #1f1f2e;
    border-radius: 8px;
}
QLabel#dlFilename { color: #e5e7eb; font-size: 12px; }
QLabel#dlSize     { color: #9ca3af; font-size: 11px; }

/* Status badges */
QLabel#dlBadge {
    background: #1f2937;
    color: #6b7280;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#dlBadgeActive {
    background: #1e3a5f;
    color: #60a5fa;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#dlBadgePaused {
    background: #2d1f00;
    color: #f59e0b;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#dlBadgeDone {
    background: #052e16;
    color: #34d399;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}
QLabel#dlBadgeError {
    background: #3b0764;
    color: #c084fc;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}

/* Download action buttons */
QPushButton#dlActionBtn {
    background: #1f2937;
    color: #9ca3af;
    border: none;
    border-radius: 6px;
    font-size: 12px;
}
QPushButton#dlActionBtn:hover { background: #374151; color: #ffffff; }

QPushButton#dlCancelBtn {
    background: transparent;
    color: #4b5563;
    border: none;
    border-radius: 6px;
    font-size: 13px;
}
QPushButton#dlCancelBtn:hover { color: #ef4444; }

/* Progress bar */
QProgressBar#dlBar {
    background: #1f2937;
    border: none;
    border-radius: 2px;
}
QProgressBar#dlBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #6366f1);
    border-radius: 2px;
}

/* ── Section heading ─────────────────────────────────── */
QLabel#sectionHeading {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
}

/* ── Scrollbars ──────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a2a38;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #374151; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #2a2a38;
    border-radius: 3px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #374151; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Splitter ────────────────────────────────────────── */
QSplitter::handle { background: #1f1f27; }

/* ── Status bar ──────────────────────────────────────── */
QStatusBar {
    background: #0d0d0f;
    color: #4b5563;
    font-size: 11px;
    border-top: 1px solid #1f1f27;
}
"""


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("DownloadFilm")
    app.setOrganizationName("DownloadFilm")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
