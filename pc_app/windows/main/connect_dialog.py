from PySide6.QtWidgets import QDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path

import serial.tools.list_ports


class ConnectDialog(QDialog):

    def __init__(self, serial_manager=None):
        super().__init__()
        self.serial_manager = serial_manager
        self.setWindowTitle("Connecting")
        self.setFixedSize(400, 200)

        # UI 로드
        ui_path = Path(__file__).parent / "connect_dialog.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(ui_path)
        
        self.ui = QUiLoader().load(ui_file)
        ui_file.close()

        self.load_ports()

    def load_ports(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.ui.cmbPort.addItem(port.device)