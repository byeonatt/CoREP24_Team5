from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, Qt
from pathlib import Path

from communication.serial_manager import SerialManager
from communication.protocol import Command, create_command


class SettingsDialog:

    def __init__(self, current_mode="MODE_OD", save_directory=None, serial_manager=None):
        self.measure_mode = current_mode
        self.save_directory = save_directory
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

        self.dialog.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.dialog.setFixedSize(self.dialog.size())

        if self.measure_mode == "MODE_OD":
            self.dialog.radioButton_1.setChecked(True)
        else:
            self.dialog.radioButton_2.setChecked(True)
        self.dialog.txtSavePath.setText(save_directory)

        if save_directory:
            self.dialog.txtSavePath.setText(str(save_directory))
        else:
            self.dialog.txtSavePath.setText(str(Path.home()/"Documents"/"GripForceData"))

        self.connect_signal()

    def connect_signal(self):
        self.dialog.applyButton.clicked.connect(self.apply_setting)
        self.dialog.btnBrowse.clicked.connect(self.select_folder)
        self.dialog.btnResetPath.clicked.connect(self.reset_path)
        self.dialog.radioButton_1.toggled.connect(self.mode_changed)
        self.dialog.radioButton_2.toggled.connect(self.mode_changed)
        self.dialog.pushButton_Zero.clicked.connect(self.zero_calibration)

    def apply_setting(self):
        if self.dialog.radioButton_1.isChecked():
            self.measure_mode = "MODE_OD"
        elif self.dialog.radioButton_2.isChecked():
            self.measure_mode = "MODE_ID_2"
        elif self.dialog.radioButton_3.isChecked():
            self.measure_mode = "MODE_ID_3"
        else : return
        self.save_directory = (self.dialog.txtSavePath.text())

        self.dialog.accept()

    def mode_changed(self, checked):
        if not checked:
            return
        
        if self.dialog.radioButton_1.isChecked():
            self.measure_mode = "MODE_OD"
            command = create_command(Command.MODE_OD)
        elif self.dialog.radioButton_2.isChecked():
            self.measure_mode = "MODE_ID_2"
            command = create_command(Command.MODE_ID_2)
        elif self.dialog.radioButton_3.isChecked():
            self.measure_mode = "MODE_ID_3"
            command = create_command(Command.MODE_ID_3)
        else : return

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

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(None, "저장 폴더 선택")
        if folder:
            self.dialog.txtSavePath.setText(folder)

    def reset_path(self):
        self.dialog.txtSavePath.setText(str(Path.home()/"Documents"/"GripForceData"))