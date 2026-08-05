from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path

from communication.serial_manager import SerialManager
from communication.protocol import Command, create_command


class SettingsDialog:

    def __init__(self, current_mode="OD", serial_manager=None):
        self.measure_mode = current_mode
        self.serial_manager = serial_manager

        ui_path = Path(__file__).parent / "settings.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(
                f"Cannot open {ui_path}"
            )

        self.dialog = QUiLoader().load(ui_file)
        ui_file.close()
        self.dialog.setWindowTitle("Settings")

        if self.measure_mode == "OD":
            self.dialog.radioButton_1.setChecked(True)
        else:
            self.dialog.radioButton_2.setChecked(True)

        self.connect_signal()

    def connect_signal(self):
        self.dialog.applyButton.clicked.connect(self.apply_setting)
        self.dialog.radioButton_1.toggled.connect(self.mode_changed)
        self.dialog.radioButton_2.toggled.connect(self.mode_changed)
        self.dialog.pushButton_Zero.clicked.connect(self.zero_calibration)

    def apply_setting(self):
        if self.dialog.radioButton_1.isChecked():
            self.measure_mode = "OD"
        elif self.dialog.radioButton_2.isChecked():
            self.measure_mode = "ID"

        self.dialog.accept()

    def mode_changed(self):
        if self.dialog.radioButton_1.isChecked():
            self.measure_mode = "OD"
            command = create_command(Command.MODE_OD)
        elif self.dialog.radioButton_2.isChecked():
            self.measure_mode = "ID"
            command = create_command(Command.MODE_ID)
        else:
            return

        if self.serial_manager:
            self.serial_manager.send_data(command)

    def zero_calibration(self):
        reply = QMessageBox.question(
            self.dialog,
            "영점 설정",
            "현재 값으로 영점을 재설정합니다."
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        command = create_command(Command.ZERO)

        if self.serial_manager.send_data(command):
            QMessageBox.information(
                self.dialog,
                "영점 설정",
                "설정을 완료했습니다."
            )

        else:
            QMessageBox.warning(
                self.dialog,
                "오류",
                "ZERO 명령 전송 실패"
            )