from PySide6.QtWidgets import QMainWindow
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from pathlib import Path

from windows.main.connect_dialog import ConnectDialog

class MeasurementWindow(QMainWindow):

    def __init__(
        self,
        config=None,
        csv_manager=None,
        serial_manager=None
    ):
        super().__init__()


        self.config = config
        self.csv_manager = csv_manager
        self.serial_manager = serial_manager

        # ui 로드
        ui_path = Path(__file__).parent / "measurement.ui"
        ui_file = QFile(str(ui_path))
        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(
                f"Cannot open {ui_path}"
            )
        self.ui = QUiLoader().load(ui_file)
        ui_file.close()

        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setFixedSize(900, 600)
        self.setWindowTitle("Measurement")
        self.test_display()

        self.update_connection_status(False)
        self.connect_signal()


    def test_display(self):
        # LCD 테스트
        if hasattr(self.ui, "lcdCurrentForce"):
            self.ui.lcdCurrentForce.display(12.34)
            
        if hasattr(self.ui, "lcdPeakForce"):
            self.ui.lcdPeakForce.display(18.56)

    def update_connection_status(self, connected):
        if connected:
            self.ui.lblConnectionState.setText("연결 성공")
            self.ui.lblCom.setText(f"COM : {self.serial_manager.port}")
            self.ui.lblDevice.setText(f"Device : {self.serial_manager.device}")
        else:
            self.ui.lblConnectionState.setText("연결 해제")
            self.ui.lblCom.setText("COM : -")
            self.ui.lblDevice.setText("Device : -")

    def connect_signal(self):
        if self.serial_manager:
            self.serial_manager.line_received.connect(self.update_force_display)
            self.serial_manager.connection_changed.connect(self.update_connection_status)
            self.serial_manager.error_occurred.connect(self.update_error_status)
            self.ui.btnConnect.clicked.connect(self.open_connect_dialog)
            self.ui.btnExit.clicked.connect(self.close_application)

    def open_connect_dialog(self):
        dialog = ConnectDialog(self.serial_manager) 
        dialog.exec()

    def update_force_display(self, data):

        try:
            current, peak = data.split(",")
            current = float(current)
            peak = float(peak)

            self.ui.lcdCurrentForce.display(current)
            self.ui.lcdPeakForce.display(peak)

        except Exception as e:
            print("Force data error:", e)

    def update_error_status(self, message):
        self.ui.lblConnectionState.setText(message)

    def close_application(self):
        if self.serial_manager:
            if self.serial_manager.is_connected():
                self.serial_manager.disconnect()
        self.close()