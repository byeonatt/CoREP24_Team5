from time import time

from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer
from pathlib import Path

from windows.main.connect_dialog import ConnectDialog
from windows.settings.settings_dialog import SettingsDialog
from communication.protocol import (
    parse_packet,
    PacketType,
    Command,
    create_command
)

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
        self.loading_dialog = None
        self.is_measuring = False
        self.current_csv = None
        self.connected = False
        self.peak_force = 0
        self.measure_mode = "OD"   # OD : 외경, ID : 내경
        self.waiting_measure_start = False
        self.last_data_time = None
        self.device_ready = False

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

        self.ui.btnSetting.setEnabled(False)
        self.ui.btnStart.setEnabled(False)
        self.ui.btnStop.setEnabled(False)

        self.connect_signal()
        self.update_connection_status(self.connected)


    def test_display(self):
        # LCD 테스트
        if hasattr(self.ui, "lcdCurrentForce"):
            self.ui.lcdCurrentForce.display(0.0)
        if hasattr(self.ui, "lcdPeakForce"):
            self.ui.lcdPeakForce.display(0.0)
        if hasattr(self.ui, "lblStatus"):
            self.ui.lblStatus.setText("상태 : 대기")
        if hasattr(self.ui, "lblMode"):
            self.ui.lblMode.setText("Mode : 외경")

    def connect_signal(self):
        # SerialManager signal 연결
        if self.serial_manager:
            self.serial_manager.line_received.connect(self.receive_data)
            self.serial_manager.connection_changed.connect(self.update_connection_status)
            self.serial_manager.error_occurred.connect(self.update_error_status)

        # UI Button 연결
        self.ui.btnConnect.clicked.connect(self.open_connect_dialog)
        self.ui.btnStart.clicked.connect(self.start_measurement)
        self.ui.btnStop.clicked.connect(self.stop_measurement)
        self.ui.btnSetting.clicked.connect(self.open_settings_dialog)
        self.ui.btnExit.clicked.connect(self.close_application)

    def update_connection_status(self, connected):
        self.connected = connected
        if connected:
            self.device_ready = False
            self.ui.lblConnectionState.setText("연결 성공")
            self.ui.lblDevice.setText(f"Device : {self.serial_manager.device}")
        else:
            self.ui.lblConnectionState.setText("연결 해제")
            self.ui.lblDevice.setText("Device : -")
        self.update_button_state() 

    def update_button_state(self):
        self.ui.btnSetting.setEnabled(self.connected and not self.is_measuring)
        self.ui.btnStart.setEnabled(self.connected and self.device_ready and not self.is_measuring)
        self.ui.btnStop.setEnabled(self.connected and self.is_measuring)

    def open_connect_dialog(self):
        dialog = ConnectDialog(self.serial_manager) 
        dialog.exec()


    def start_measurement(self):
        try:
            command = create_command(Command.START)

            if self.serial_manager.send_data(command):
                self.is_measuring = False
                self.waiting_measure_start = True
                self.last_data_time = time.time()
                self.ui.lblStatus.setText("상태 : 대기")
                self.start_timer.start(3000)
                self.update_button_state()
            else:
                self.update_error_status("측정 시작 명령 전송 실패")

        except Exception as e:
            self.update_error_status(f"측정 시작 오류: {e}")


    def stop_measurement(self):
        command = create_command(Command.STOP)
        self.serial_manager.send_data(command)
        self.is_measuring = False
        self.ui.lblStatus.setText("상태 : 대기")

        self.update_button_state()

        if self.current_csv:
            self.current_csv.close()
            self.current_csv = None
        ... # 디스플레이 갱신 정지 구현


    def open_settings_dialog(self):
        self.setting_dialog = SettingsDialog(self.measure_mode, self.serial_manager)

        if self.setting_dialog.dialog.exec():
            self.measure_mode = self.setting_dialog.measure_mode

    def set_measure_mode(self, mode):
        self.measure_mode = mode


    def update_force_display(self, force):
        if not self.is_measuring:
            return
        if force > self.peak_force:
            self.peak_force = force

        self.ui.lcdCurrentForce.display(force)
        self.ui.lcdPeakForce.display(self.peak_force)

    def update_status(self, status):
        self.ui.lblStatus.setText(f"상태 : {status}")

    def update_error_status(self, message):
        QMessageBox.warning(self, "오류", message)
        self.ui.lblStatus.setText("상태 : 대기")

    def close_application(self):
        if self.serial_manager:
            if self.serial_manager.is_connected():
                self.serial_manager.disconnect()
        self.close()

    def receive_data(self, line):
        print("수신:", line)
        if self.connected and not self.device_ready:
            self.device_ready = True
            self.ui.lblStatus.setText("상태 : 측정 가능")
            self.update_button_state()

        packet = parse_packet(line)
        if packet is None: return

        if self.waiting_measure_start or self.is_measuring:
            self.last_data_time = time.time()

        if packet.type == PacketType.FORCE:
            self.update_force_display(packet.value)
        elif packet.type == PacketType.STATUS:
            self.update_status(packet.value)
        elif packet.type == PacketType.ERROR:
            self.update_error_status(packet.value)

