"""Modeless offline help window for the measurement application."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTextBrowser

from windows.help.help_content import (
    ABOUT_TEXT,
    APP_NAME,
    APP_VERSION,
    CALIBRATION_HTML,
    COMMUNICATION_HTML,
    MEASUREMENT_HTML,
    STORAGE_HTML,
)


class HelpWindow(QMainWindow):
    """Single reusable help window with four section tabs."""

    COMMUNICATION = 0
    MEASUREMENT = 1
    CALIBRATION = 2
    STORAGE = 3

    SECTION_INDEX = {
        "communication": COMMUNICATION,
        "measurement": MEASUREMENT,
        "calibration": CALIBRATION,
        "storage": STORAGE,
    }

    TAB_TITLES = (
        "통신",
        "측정",
        "캘리브레이션",
        "저장",
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = Path(__file__).resolve().parent / "help.ui"
        ui_file = QFile(str(ui_path))

        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(f"Cannot open {ui_path}")

        loaded_ui = QUiLoader().load(ui_file)
        ui_file.close()

        if loaded_ui is None:
            raise RuntimeError(f"Cannot load {ui_path}")

        self.ui = loaded_ui
        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setMinimumSize(self.ui.minimumSize())
        self.setWindowTitle(f"{APP_NAME} - 사용 설명서")

        # Parent가 있어도 독립적인 모델리스 창으로 동작한다.
        self.setWindowFlag(Qt.Window, True)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._browsers: tuple[QTextBrowser, ...] = (
            self.ui.communicationBrowser,
            self.ui.measurementBrowser,
            self.ui.calibrationBrowser,
            self.ui.storageBrowser,
        )

        self._load_content()
        self._connect_signals()
        self._update_footer(0)

    def _load_content(self) -> None:
        contents = (
            COMMUNICATION_HTML,
            MEASUREMENT_HTML,
            CALIBRATION_HTML,
            STORAGE_HTML,
        )

        for browser, html in zip(self._browsers, contents):
            browser.setOpenExternalLinks(False)
            browser.setHtml(html)

    def _connect_signals(self) -> None:
        self.ui.closeButton.clicked.connect(self.close)
        self.ui.helpTabWidget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        self._update_footer(index)

    def _update_footer(self, index: int) -> None:
        if 0 <= index < len(self.TAB_TITLES):
            section = self.TAB_TITLES[index]
        else:
            section = "사용 설명서"

        self.ui.sectionLabel.setText(f"현재 항목: {section}")
        self.ui.versionLabel.setText(f"{APP_NAME}  v{APP_VERSION}")

    def show_section(self, section: int | str = COMMUNICATION) -> None:
        """Open the window and move directly to the requested section."""

        if isinstance(section, str):
            index = self.SECTION_INDEX.get(section.lower(), self.COMMUNICATION)
        else:
            try:
                index = int(section)
            except (TypeError, ValueError):
                index = self.COMMUNICATION

        if not 0 <= index < self.ui.helpTabWidget.count():
            index = self.COMMUNICATION

        self.ui.helpTabWidget.setCurrentIndex(index)
        self._browsers[index].verticalScrollBar().setValue(0)

        self.show()
        self.raise_()
        self.activateWindow()

    @staticmethod
    def show_about(parent=None) -> None:
        QMessageBox.about(
            parent,
            "프로그램 정보",
            ABOUT_TEXT,
        )
