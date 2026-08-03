# connect_dialog.py

from PySide6.QtWidgets import QDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path

import serial.tools.list_ports


class ConnectDialog:

    def __init__(self, serial_manager=None):
        self.serial_manager = serial_manager

        ui_path = Path(__file__).parent / "connect_dialog.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(ui_path)
        
        self.dialog = QUiLoader().load(ui_file)
        ui_file.close()

        self.load_ports()
        self.load_baudrates()
        self.dialog.btnConnect.clicked.connect(self.connect_device)

    def load_ports(self):
        self.dialog.cmbPort.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.dialog.cmbPort.addItem(port.device)

    def load_baudrates(self):
        baudrates = [
            9600, 19200,
            38400, 57600,
            115200
        ]
        self.dialog.cmbBaudrate.clear()
        for baudrate in baudrates:
            self.dialog.cmbBaudrate.addItem(str(baudrate))
            

    def exec(self):
        self.dialog.exec()

    def connect_device(self):
        port = self.dialog.cmbPort.currentText()
        baudrate = int(self.dialog.cmbBaudrate.currentText())

        if self.serial_manager:
            result = self.serial_manager.connect(port, baudrate)
            if result: self.dialog.accept()
            else: self.serial_manager.error_occurred.emit("연결 실패")