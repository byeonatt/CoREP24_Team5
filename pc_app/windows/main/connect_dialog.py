# connect_dialog.py

from PySide6.QtWidgets import QDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path

import serial.tools.list_ports
from windows.main.loading_dialog import LoadingDialog


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
            text = f"{port.device} - {port.description}"
            self.dialog.cmbPort.addItem(text, {
                "port": port.device,
                "device": port.description
            })

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
        port_info = self.dialog.cmbPort.currentData()
        port = port_info["port"]
        device = port_info["device"]

        baudrate = int(self.dialog.cmbBaudrate.currentText())

        self.loading_dialog = LoadingDialog("연결 중입니다...")
        self.loading_dialog.show()

        if self.serial_manager:
            result = self.serial_manager.connect(port, baudrate, device)
            if result : 
                self.serial_manager.device = device
                self.dialog.accept()
            else : self.serial_manager.error_occurred.emit("연결 실패")

        self.loading_dialog.close()