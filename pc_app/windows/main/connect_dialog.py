# connect_dialog.py

import threading

from PySide6.QtWidgets import QDialog, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QObject, Signal
from pathlib import Path

from windows.main.loading_dialog import LoadingDialog



class UsbScanSignals(QObject):
    finished = Signal(list)

class ConnectDialog:

    def __init__(self, serial_manager=None):
        self.serial_manager = serial_manager

        ui_path = Path(__file__).parent / "connect_dialog.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(ui_path)
        
        self.dialog = QUiLoader().load(ui_file)
        ui_file.close()

        self.usb_scan_signals = UsbScanSignals()
        self.usb_scan_signals.finished.connect(self.add_usb_candidates)
        self.load_baudrates()
        self.load_ports()

        self.dialog.btnConnect.clicked.connect(self.connect_device)
        if self.serial_manager:
            self.serial_manager.connect_finished.connect(self.handle_connect_finished)
        self.start_usb_scan()


    def load_ports(self):
        self.dialog.cmbPort.clear()

        if not self.serial_manager: return
        ports = self.serial_manager.find_ports()

        for port in ports:
            description = (port["description"] or "Serial Device")
            text = (f'{port["port"]} - 'f'{description}')

            if port["vid"] is not None and port["pid"] is not None:
                text += (f' [{port["vid"]:04X}:'f'{port["pid"]:04X}]')

            self.dialog.cmbPort.addItem(
                text,
                {
                    **port,
                    "device": description
                }
            )

        # COM이 없어도 창은 즉시 표시
        if not ports:
            self.dialog.cmbPort.addItem(
                "연결 가능한 COM 포트 없음",
                {
                    "connectable": False,
                    "reason": "not_found"
                }
            )

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
        try:
            return self.dialog.exec()

        finally:
            if self.serial_manager:
                try:
                    self.serial_manager.connect_finished.disconnect(
                        self.handle_connect_finished
                    )
                except (TypeError, RuntimeError):
                    pass

    def connect_device(self):
        port_info = self.dialog.cmbPort.currentData()
        if not port_info: return

        if not port_info.get("connectable", False):
            reason = port_info.get("reason")

            if reason == "not_found":
                QMessageBox.warning(
                    self.dialog,
                    "장치 없음",
                    "연결 가능한 Serial 장치를 "
                    "찾지 못했습니다."
                )

            else:
                QMessageBox.warning(
                    self.dialog,
                    "COM 포트 없음",
                    "장치는 Windows에서 감지되었지만 "
                    "Serial COM 포트가 생성되지 않았습니다.\n\n"
                    "USB CDC/Serial 설정 또는 "
                    "장치 드라이버를 확인해 주세요."
                )

            return

        port = port_info["port"]
        device = port_info["device"]
        baudrate = int(self.dialog.cmbBaudrate.currentText())

        self.loading_dialog = LoadingDialog("연결 중입니다...")
        self.loading_dialog.show()
        self.dialog.btnConnect.setEnabled(False)

        if self.serial_manager:
            self.serial_manager.connect_async(port, baudrate, device)

    def handle_connect_finished(self, success, message):

        if hasattr(self, "loading_dialog"):
            if self.loading_dialog is not None:
                self.loading_dialog.close()
                self.loading_dialog = None

        self.dialog.btnConnect.setEnabled(True)

        if success:
            self.dialog.accept()
        else:
            QMessageBox.warning(self.dialog, "연결 실패", message or "장치 연결에 실패했습니다.")

    def start_usb_scan(self):
        if not self.serial_manager:
            return

        thread = threading.Thread(
            target=self._usb_scan_worker,
            daemon=True
        )
        thread.start()

    def _usb_scan_worker(self):
        candidates = (
            self.serial_manager
            .find_usb_candidates()
        )
        self.usb_scan_signals.finished.emit(
            candidates
        )

    def add_usb_candidates(self, candidates):
        if not candidates: return
        
        # COM 포트와 진단용 USB 장치 구분
        if self.dialog.cmbPort.count() > 0:
            self.dialog.cmbPort.insertSeparator(self.dialog.cmbPort.count())

        for device in candidates:
            text = (f'⚠ {device["name"]} 'f'(COM 포트 없음)')
            self.dialog.cmbPort.addItem(text, device)
    