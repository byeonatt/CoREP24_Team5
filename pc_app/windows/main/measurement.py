import time

from PySide6.QtWidgets import QMainWindow, QMessageBox, QInputDialog, QTableWidgetItem, QFileDialog
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer
from pathlib import Path
from collections import deque

from data_manager.csv_manager import CSVManager
from windows.main.connect_dialog import ConnectDialog
from windows.settings.settings_dialog import SettingsDialog
from windows.settings.judgement_settings_dialog import JudgementSettingsDialog
from windows.calibration.calibration_window import CalibrationWindow
from windows.main.realtime_force_graph import RealtimeForceGraph
from data_manager.data_management_window import DataManagementWindow
from data_manager.grip_event_detector import GripEventDetector

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
        self.is_measuring = False
        self.connected = False

        self.force_sum = 0
        self.peak_force = 0
        self.sample_count = 0

        self.measurement_start_time = None
        self.current_csv = None
        self.measure_mode = None
        self.device_ready = False
        self.current_judgement = None
        self.data_management_window = None
        self.current_grip_id = None

        self.grip_event_detector = GripEventDetector(
            start_threshold_n=0.50,
            release_threshold_n=0.20,
            release_hold_seconds=0.20,
            min_peak_force_n=1.00,
            min_event_duration_s=0.10,
            min_event_gap_s=0.30,
        )
        self.grip_events = []

        self.max_measurement_seconds = 60 * 60
        self.inactivity_window_seconds = 5 * 60
        self.inactivity_threshold_n = 0.25
        self.inactivity_sample_interval = 1.0
        self.inactivity_samples = deque()
        self.last_inactivity_sample_time = None

        self.last_force_data = None
        self.last_force_packet_time = None
        self.last_monitor_update_time = 0.0
        self.force_packet_timeout = 1.0
        self.rate_sample_count = 0
        self.rate_start_time = None

        self.zero_in_progress = False
        self.zero_ignore_frames = 5
        self.zero_ignore_count = 0
        self.zero_samples = {"lc1": [], "lc2": [], "lc3": []}
        self.zero_check_sample_count = 20
        self.zero_tolerance = 0.05
        self.zero_stability_tolerance = 0.03

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
        self.setWindowTitle("Measurement")
        # 실시간 Force 그래프
        self.force_graph = RealtimeForceGraph(self.ui.graphContainer)
        self.force_graph.set_mode(None)
        

        self.handshake_timer = QTimer(self)
        self.handshake_timer.setSingleShot(True)
        self.handshake_timer.timeout.connect(self.handle_handshake_timeout)

        self.communication_watchdog = QTimer(self)
        self.communication_watchdog.setInterval(250)
        self.communication_watchdog.timeout.connect(self.check_force_packet_timeout)

        self.measurement_timer = QTimer(self)
        self.measurement_timer.setInterval(100)
        self.measurement_timer.timeout.connect(self.update_measurement_time)

        self.measurement_safety_timer = QTimer(self)
        self.measurement_safety_timer.setInterval(1000)
        self.measurement_safety_timer.timeout.connect(self.check_measurement_safety)

        self.test_display()
        self.ui.startButton.setEnabled(False)
        self.ui.stopButton.setEnabled(False)

        self.connect_signal()
        self.update_connection_status(self.connected)
        self.update_measure_mode()
        self.communication_watchdog.start()


    def test_display(self):
        self.ui.currentForceLabel.setText("0.00 N")
        self.ui.peakForceLabel.setText("0.00 N")
        self.ui.averageForceLabel.setText("0.00 N")

        self.ui.connectedLabel.setText("●  연결 대기")
        self.ui.portValueLabel.setText("-")
        self.ui.deviceValueLabel.setText("-")
        self.ui.measurementTimeLabel.setText("00:00.0")

        self.ui.samplingRateLabel.setText("0 Hz")
        self.ui.measurementStateLabel.setText("연결 대기")
        self.ui.forceStatusLabel.setText("판정 대기")
        self.ui.operationStateLabel.setText("●  통신 대기")

        self.ui.pcEspStatusLabel.setText("미연결")
        self.ui.serialPortStatusLabel.setText("-")
        self.ui.handshakeStatusLabel.setText("대기")
        self.ui.adcStatusLabel.setText("미수신")

        self.ui.gripCountLabel.setText("0")
        self.ui.judgementSummaryLabel.setText("대기")
        self.ui.forceRangeLabel.setText("미적용")

    def connect_signal(self):
        # SerialManager signal 연결
        if self.serial_manager:
            self.serial_manager.line_received.connect(self.receive_data)
            self.serial_manager.connection_changed.connect(self.update_connection_status)
            self.serial_manager.error_occurred.connect(self.update_error_status)

        # UI Button 연결
        self.ui.zeroButton.clicked.connect(self.zero_adjustment)
        self.ui.modeButton.clicked.connect(self.select_measure_mode)
        self.ui.startButton.clicked.connect(self.start_measurement)
        self.ui.stopButton.clicked.connect(self.stop_measurement)
        self.ui.calibrationTabButton.clicked.connect(self.open_calibration_window)
        self.ui.settingsTabButton.clicked.connect(self.open_connect_dialog)
        self.ui.actionConnectionSettings.triggered.connect(self.open_connect_dialog)
        self.ui.actionJudgementSettings.triggered.connect(self.open_judgement_settings)
        self.ui.dataTabButton.clicked.connect(self.open_data_management_window)
        self.ui.actionDataManagement.triggered.connect(self.open_data_management_window)
        self.ui.actionSaveDirectory.triggered.connect(self.select_save_directory)


    def update_connection_status(self, connected):
        self.connected = connected

        if connected:
            self.device_ready = False
            self.last_force_packet_time = None

            self.ui.connectedLabel.setText("●  Serial 연결됨")
            self.ui.portValueLabel.setText(self.serial_manager.port)
            self.ui.deviceValueLabel.setText("확인 중")
            self.ui.measurementStateLabel.setText("ESP32 확인 중")

            self.ui.pcEspStatusLabel.setText("확인 중")
            self.ui.serialPortStatusLabel.setText(self.serial_manager.port)
            self.ui.handshakeStatusLabel.setText("준비")
            self.ui.adcStatusLabel.setText("미수신")

            command = create_command(Command.START)
            if self.serial_manager.send_data(command):
                self.handshake_timer.start(1500)

        else:
            self.device_ready = False
            self.is_measuring = False
            self.zero_in_progress = False

            self.zero_ignore_count = 0
            self.zero_samples = {
                "lc1": [],
                "lc2": [],
                "lc3": []
            }

            self.last_force_packet_time = None

            if self.measurement_timer.isActive():
                self.measurement_timer.stop()
            if self.measurement_safety_timer.isActive():
                self.measurement_safety_timer.stop()

            self.reset_measurement_safety_state()
            self.force_graph.stop()
            self.close_current_csv()

            if self.handshake_timer.isActive():
                self.handshake_timer.stop()

            self.last_force_data = None
            self.rate_sample_count = 0
            self.rate_start_time = None

            self.ui.connectedLabel.setText("●  연결 대기")
            self.ui.portValueLabel.setText("-")
            self.ui.deviceValueLabel.setText("-")
            self.ui.measurementStateLabel.setText("연결 대기")

            self.ui.operationStateLabel.setText("●  통신 대기")
            self.ui.pcEspStatusLabel.setText("미연결")
            self.ui.serialPortStatusLabel.setText("-")
            self.ui.handshakeStatusLabel.setText("대기")
            self.ui.adcStatusLabel.setText("미수신")

        self.update_button_state()

    def handle_handshake_timeout(self):
        if self.connected and not self.device_ready:
            self.ui.measurementStateLabel.setText("장치 응답 없음")
            self.ui.handshakeStatusLabel.setText("실패")
            self.ui.operationStateLabel.setText("●  장비 확인 실패")
            QMessageBox.warning(
                self,
                "장치 확인 실패",
                "Serial 포트는 연결되었지만 "
                "ESP32의 READY 응답을 받지 못했습니다.\n\n"
                "올바른 포트를 선택했는지 확인해 주세요."
            )
            if self.serial_manager:
                self.serial_manager.disconnect()

    def update_button_state(self):
        ready = (self.connected and self.device_ready)
        available = (ready and not self.is_measuring and not self.zero_in_progress)

        self.ui.zeroButton.setEnabled(available)
        self.ui.modeButton.setEnabled(available)
        self.ui.startButton.setEnabled(available)
        self.ui.stopButton.setEnabled(ready and self.is_measuring)
        self.ui.dataTabButton.setEnabled(not self.is_measuring)
        self.ui.settingsTabButton.setEnabled(
            self.connected
            and not self.is_measuring
            and not self.zero_in_progress
        )
        self.ui.calibrationTabButton.setEnabled(
            self.connected
            and not self.is_measuring
            and not self.zero_in_progress
        )
        self.ui.actionDataManagement.setEnabled(not self.is_measuring)
        self.ui.actionSaveDirectory.setEnabled(not self.is_measuring)
        self.ui.actionJudgementSettings.setEnabled(not self.is_measuring and not self.zero_in_progress)

    def open_connect_dialog(self):
        dialog = ConnectDialog(self.serial_manager) 
        dialog.exec()

    def open_judgement_settings(self):
        if self.is_measuring:
            QMessageBox.warning(
                self,
                "판정 기준 설정",
                "측정 중에는 판정 기준을 변경할 수 없습니다."
            )
            return
        dialog = JudgementSettingsDialog(self.config)
        if dialog.dialog.exec():
            self.update_judgement_display()

    def start_measurement(self):
        try:
            if not self.device_ready:
                QMessageBox.warning(self,
                    "측정 시작 불가",
                    "ESP32가 연결되어 있지 않습니다."
                )
                return

            # 측정 모드 확인
            if self.measure_mode is None:
                QMessageBox.warning(
                    self,
                    "측정 시작 불가",
                    "측정 모드를 먼저 설정해 주세요."
                )
                return

            # 측정 데이터 확인
            if self.last_force_data is None:
                QMessageBox.warning(
                    self,
                    "측정 시작 불가",
                    "로드셀 데이터를 수신하지 못하고 있습니다."
                )
                return

            # ADS1256 상태 확인
            if not self.last_force_data.status_ok:
                QMessageBox.warning(
                    self,
                    "측정 시작 불가",
                    "ADS1256 통신 상태가 정상적이지 않습니다."
                )
                return
            
            self.current_judgement = (self.config.get_judgement_snapshot(self.measure_mode))

            # CSV 파일 생성
            self.current_grip_id = (self.config.get_next_grip_id())
            self.current_csv = (self.csv_manager.start_measurement(self.current_grip_id))

            # 측정값 초기화
            self.peak_force = 0.0
            self.force_sum = 0.0
            self.sample_count = 0
            self.rate_sample_count = 0

            # Grip Event 초기화
            self.grip_event_detector.reset()
            self.grip_events.clear()

            self.force_graph.start()

            now = time.monotonic()
            self.measurement_start_time = now
            self.rate_start_time = now
            self.is_measuring = True
            self.update_judgement_display()

            self.ui.peakForceLabel.setText("0.00 N")
            self.ui.averageForceLabel.setText("0.00 N")
            self.ui.measurementTimeLabel.setText("00:00.0")
            self.ui.samplingRateLabel.setText("0 Hz")
            self.ui.measurementStateLabel.setText("측정 중")

            self.reset_measurement_safety_state()
            self.measurement_safety_timer.start()
            self.measurement_timer.start()
            self.update_button_state()


        except Exception as e:
            self.is_measuring = False
            self.measurement_timer.stop()
            self.close_current_csv()
            self.update_button_state()
            self.update_error_status(f"측정 시작 오류: {e}")


    def stop_measurement(self):
        if not self.is_measuring:
            return
        self.grip_event_detector.cancel_active_event()
        self.is_measuring = False
        if self.measurement_safety_timer.isActive():
            self.measurement_safety_timer.stop()
        self.reset_measurement_safety_state()

        self.force_graph.stop()
        if self.measurement_timer.isActive():
            self.measurement_timer.stop()

        self.ui.measurementStateLabel.setText("측정 완료")
        self.close_current_csv()
        self.save_session_result()
        self.current_grip_id = None
        self.update_button_state()

    def close_current_csv(self):
        if self.current_csv is None: return
        if self.csv_manager: self.csv_manager.close()
        self.current_csv = None

    def open_calibration_window(self):
        self.calibration_window = CalibrationWindow(self.serial_manager)
        self.calibration_window.show()

    def open_data_management_window(self):
        if self.is_measuring:
            QMessageBox.information(
                self,
                "데이터 관리",
                "측정 중에는 데이터 관리 화면을 "
                "열 수 없습니다.\n\n"
                "측정을 종료한 후 다시 시도해 주세요."
            )
            return

        try:
            base_directory = (self.config.get_base_directory())
            self.data_management_window = (DataManagementWindow(base_directory=base_directory))
            self.data_management_window.show()
        except Exception as e:
            QMessageBox.warning(
                self,
                "데이터 관리 오류",
                f"데이터 관리 화면을 열지 못했습니다.\n\n{e}"
            )

    def set_measure_mode(self, mode):
        self.measure_mode = mode

    def select_measure_mode(self):
        if not self.connected or not self.device_ready:
            QMessageBox.warning(self, "모드 설정", "ESP32가 연결되어 있지 않습니다.")
            return

        if self.is_measuring:
            QMessageBox.warning(self, "모드 설정", "측정 중에는 모드를 변경할 수 없습니다.")
            return

        modes = ["외경", "내경 2-Jaw", "내경 3-Jaw"]

        # 현재 모드가 선택된 상태로 창 열기
        if self.measure_mode == "MODE_OD":
            current_index = 0
        elif self.measure_mode == "MODE_ID_2":
            current_index = 1
        elif self.measure_mode == "MODE_ID_3":
            current_index = 2
        else:
            current_index = 0

        selected, ok = QInputDialog.getItem(
            self,
            "측정 모드 설정",
            "측정 모드를 선택하세요.",
            modes,
            current_index,
            False
        )

        if not ok:
            return

        if selected == "외경":
            mode = "MODE_OD"
            command_type = Command.MODE_OD

        elif selected == "내경 2-Jaw":
            mode = "MODE_ID_2"
            command_type = Command.MODE_ID_2

        elif selected == "내경 3-Jaw":
            mode = "MODE_ID_3"
            command_type = Command.MODE_ID_3

        else:
            return

        # ESP32로 모드 명령 전송
        command = create_command(command_type)

        if self.serial_manager.send_data(command):
            self.measure_mode = mode
            self.update_measure_mode()
            self.ui.operationStateLabel.setText(f"● 측정 모드: {selected}")
        else:
            self.update_error_status("모드 설정 명령 전송에 실패했습니다.")

    def zero_adjustment(self):

        if not self.device_ready:
            QMessageBox.warning(
                self,
                "영점 설정",
                "ESP32가 연결되어 있지 않습니다."
            )
            return
        if self.is_measuring:
            QMessageBox.warning(
                self,
                "영점 설정",
                "측정 중에는 영점을 설정할 수 없습니다."
            )
            return
        if self.zero_in_progress:
            return
        
        if self.last_force_data is None:
            QMessageBox.warning(
                self,
                "영점 설정",
                "로드셀 데이터를 수신하지 못하고 있습니다."
            )
            return
        if not self.last_force_data.status_ok:
            QMessageBox.warning(
                self,
                "영점 설정",
                "ADS1256 통신 상태가 정상적이지 않습니다."
            )
            return
        if self.zero_in_progress: return

        reply = QMessageBox.question(
            self,
            "영점 설정",
            "로드셀에 하중이 없는 상태인지 확인해 주세요.\n\n"
            "현재 상태를 영점으로 설정하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes: return

        command = create_command(Command.ZERO)
        if not self.serial_manager.send_data(command):
            self.update_error_status("영점 설정 명령 전송에 실패했습니다.")
            return

        self.zero_in_progress = True
        self.zero_ignore_count = 0
        self.zero_samples = {"lc1": [], "lc2": [], "lc3": []}
        self.ui.operationStateLabel.setText("●  영점 설정 확인 중")
        self.update_button_state()


    def update_adc_status(self, data):
        status_text = f"0x{data.status:02X}"

        if data.status_ok:
            self.ui.adcStatusLabel.setText(f"{status_text} 정상")
        else:
            self.ui.adcStatusLabel.setText(f"{status_text} 비정상")
            if not self.zero_in_progress:
                self.ui.operationStateLabel.setText(f"● ADC 통신 이상  {status_text}")

    def update_error_status(self, message):
        QMessageBox.warning(self, "오류", message)
        if self.is_measuring:
            self.ui.measurementStateLabel.setText("측정 중")
        elif self.device_ready:
            self.ui.measurementStateLabel.setText("측정 가능")
        else:
            self.ui.measurementStateLabel.setText("연결 대기")

    def update_measure_mode(self):
        if self.measure_mode == "MODE_OD":
            text = "외경"
        elif self.measure_mode == "MODE_ID_2":
            text = "내경 2-Jaw"
        elif self.measure_mode == "MODE_ID_3":
            text = "내경 3-Jaw"
        else:
            text = "미설정"
        self.ui.modeValueLabel.setText(text)
        self.force_graph.set_mode(self.measure_mode)
        self.ui.modeButton.setToolTip(f"현재 측정 모드: {text}")
        self.update_judgement_display()

    def update_judgement_display(self):
        if (
            self.is_measuring
            and self.current_judgement is not None
        ):
            judgement = self.current_judgement
        else:
            if not self.config.get_judgement_enabled():
                judgement = {
                    "enabled": False,
                    "lower_limit_n": None,
                    "upper_limit_n": None,
                }
            elif self.measure_mode is None:
                judgement = None
            else:
                judgement = (self.config.get_judgement_snapshot(self.measure_mode))

        if judgement is None:
            self.ui.forceRangeLabel.setText("모드 선택 필요")
            self.ui.judgementSummaryLabel.setText("대기")
            return
        if not judgement["enabled"]:
            self.ui.forceRangeLabel.setText("미적용")
            self.ui.judgementSummaryLabel.setText("판정 미적용")
            return
        
        lower = judgement["lower_limit_n"]
        upper = judgement["upper_limit_n"]
        self.ui.forceRangeLabel.setText(f"{lower:.3f} ~ {upper:.3f} N")
        self.ui.judgementSummaryLabel.setText("OK 0 / NG 0")

    def close_application(self):
        if self.serial_manager:
            if self.serial_manager.is_connected():
                self.serial_manager.disconnect()
        self.close()

    def receive_data(self, line):
        packet = parse_packet(line)

        if packet is None: return

        if packet.type == PacketType.READY:

            if self.handshake_timer.isActive():
                self.handshake_timer.stop()
            self.device_ready = True
            self.last_force_packet_time = time.monotonic()

            self.ui.connectedLabel.setText("●  장비 연결됨")
            self.ui.deviceValueLabel.setText(packet.value)
            self.ui.measurementStateLabel.setText("측정 가능")
            self.ui.pcEspStatusLabel.setText("정상")
            self.ui.handshakeStatusLabel.setText("READY 확인")
            self.ui.operationStateLabel.setText("●  ESP32 정상")

            self.update_button_state()
            return
        
        if packet.type == PacketType.FORCE:
            if not self.device_ready: return

            data = packet.value
            self.last_force_data = data
            self.last_force_packet_time = (time.monotonic()) # 시간

            if self.zero_in_progress:
                self.check_zero_result(data)
            if self.is_measuring:
                self.rate_sample_count += 1
                elapsed = (time.monotonic() - self.measurement_start_time)
                self.csv_manager.append_measurement(
                    elapsed_time=elapsed,
                    mode=self.measure_mode,
                    data=data
                )
                event = self.grip_event_detector.update(
                    elapsed_time_s=elapsed,
                    total_force_n=data.total_force
                )
                if event is not None:
                    self.grip_events.append(event)
                    self.csv_manager.append_grip_event(
                        event_id=event.event_id,
                        start_time_s=event.start_time_s,
                        peak_time_s=event.peak_time_s,
                        end_time_s=event.end_time_s,
                        duration_s=event.duration_s,
                        peak_force_n=event.peak_force_n
                    )
                    # 임시(파지 테스트)
                    print(
                        f"[GRIP EVENT] #{event.event_id} "
                        f"Peak={event.peak_force_n:.3f} N "
                        f"Duration={event.duration_s:.3f} s"
                    )

                self.update_inactivity_monitor(data)

            self.ui.pcEspStatusLabel.setText("정상") # 통신 상태 정상 확인
            self.update_force_display(data) # 실시간 파지력
            self.update_serial_monitor(data) # 시리얼 모니터 갱신
            if self.is_measuring:
                self.force_graph.add_data(data)

            return

    def update_force_display(self, data):
        total_force = data.total_force

        self.ui.currentForceLabel.setText(f"{total_force:.2f} N")
        self.update_adc_status(data)
        if not self.is_measuring:
            return

        if total_force > self.peak_force:
            self.peak_force = total_force

        self.ui.peakForceLabel.setText(f"{self.peak_force:.2f} N")

        self.force_sum += total_force
        self.sample_count += 1

        average = (self.force_sum / self.sample_count)
        self.ui.averageForceLabel.setText(f"{average:.2f} N")

    def check_force_packet_timeout(self):
        if not self.connected: return
        if not self.device_ready: return
        if self.last_force_packet_time is None: return

        elapsed = (time.monotonic() - self.last_force_packet_time)

        if elapsed > self.force_packet_timeout:

            self.last_force_data = None

            if self.zero_in_progress:
                self.zero_in_progress = False
                self.zero_samples.clear()

            if self.is_measuring:
                self.grip_event_detector.cancel_active_event()
                self.is_measuring = False
                if self.measurement_timer.isActive():
                    self.measurement_timer.stop()
                if self.measurement_safety_timer.isActive():
                    self.measurement_safety_timer.stop()
                self.reset_measurement_safety_state()
                self.force_graph.stop()
                self.close_current_csv()

                self.ui.measurementStateLabel.setText("통신 오류로 측정 중단")

            self.ui.pcEspStatusLabel.setText("데이터 수신 끊김")
            self.ui.adcStatusLabel.setText("수신 없음")
            self.ui.operationStateLabel.setText("●  통신 이상")
            self.update_button_state()

    def update_serial_monitor(self, data):
        now = time.monotonic()

        if now - self.last_monitor_update_time < 0.1 : return

        self.last_monitor_update_time = now
        row = self.ui.sessionTable.rowCount()
        self.ui.sessionTable.insertRow(row)

        timestamp = time.strftime("%H:%M:%S")

        values = [
            timestamp,

            str(data.raw_lc1),
            f"{data.force_lc1:.3f}",

            str(data.raw_lc2),
            f"{data.force_lc2:.3f}",

            str(data.raw_lc3),
            f"{data.force_lc3:.3f}",

            f"{data.total_force:.3f}"
        ]

        for column, value in enumerate(values):
            self.ui.sessionTable.setItem(
                row,
                column,
                QTableWidgetItem(value)
            )

        self.ui.sessionTable.scrollToBottom()
        max_rows = 200

        while (
            self.ui.sessionTable.rowCount()
            > max_rows
        ):
            self.ui.sessionTable.removeRow(0)

    def update_measurement_time(self):
        if not self.is_measuring: return
        if self.measurement_start_time is None: return

        elapsed = (time.monotonic() - self.measurement_start_time)
        minutes = int(elapsed // 60)
        seconds = elapsed % 60

        self.ui.measurementTimeLabel.setText(f"{minutes:02d}:{seconds:04.1f}")
        self.update_sampling_rate()

    def update_sampling_rate(self):
        if not self.is_measuring: return
        if self.rate_start_time is None: return

        elapsed = (time.monotonic() - self.rate_start_time)

        if elapsed <= 0: return

        rate = (self.rate_sample_count / elapsed)
        self.ui.samplingRateLabel.setText(f"{rate:.1f} Hz")

    def check_zero_result(self, data):

        if not self.zero_in_progress:
            return
        
        if not data.status_ok:
            self.zero_in_progress = False
            self.zero_ignore_count = 0
            self.zero_samples = {"lc1": [], "lc2": [], "lc3": []}
            self.ui.operationStateLabel.setText("●  영점 설정 실패")

            self.update_button_state()

            QMessageBox.warning(
                self,
                "영점 설정 실패",
                "영점 확인 중 ADS1256 통신 이상이 발생했습니다."
            )
            return

        if self.zero_ignore_count < self.zero_ignore_frames:
            self.zero_ignore_count += 1
            return

        self.zero_samples["lc1"].append(data.force_lc1)
        self.zero_samples["lc2"].append(data.force_lc2)
        self.zero_samples["lc3"].append(data.force_lc3)

        if (
            len(self.zero_samples["lc1"])
            < self.zero_check_sample_count
        ):
            return

        active_cells = self.get_active_load_cells()
        if not active_cells:
            self.zero_in_progress = False
            self.ui.operationStateLabel.setText("●  영점 설정 실패")
            self.update_button_state()
            QMessageBox.warning(
                self,
                "영점 설정 실패",
                "측정 모드가 설정되어 있지 않습니다."
            )
            return

        success = True
        result_lines = []

        for lc in active_cells:
            samples = self.zero_samples[lc]
            mean_value = (sum(samples) / len(samples))
            peak_to_peak = (max(samples) - min(samples))
            mean_ok = (abs(mean_value) <= self.zero_tolerance)
            stability_ok = (peak_to_peak <= self.zero_stability_tolerance)

            if not (mean_ok and stability_ok):
                success = False

            result_lines.append(
                f"{lc.upper()} : "
                f"평균 {mean_value:.3f} N / "
                f"변동 {peak_to_peak:.3f} N"
            )

        result_text = "\n".join(result_lines)

        self.zero_in_progress = False
        self.zero_ignore_count = 0
        self.zero_samples = {"lc1": [], "lc2": [], "lc3": []}

        if success:
            self.ui.operationStateLabel.setText("●  영점 설정 완료")
            QMessageBox.information(
                self,
                "영점 설정 완료",
                "영점 설정이 완료되었습니다.\n\n"
                + result_text
            )
        else:
            self.ui.operationStateLabel.setText("●  영점 설정 불안정")
            QMessageBox.warning(
                self,
                "영점 설정 확인",
                "영점 설정 후 일부 로드셀 값이 "
                "허용 범위 안에서 안정되지 않았습니다.\n\n"
                + result_text
            )
        self.update_button_state()

    def get_active_load_cells(self):
        if self.measure_mode == "MODE_OD":
            return ["lc1", "lc2"]
        elif self.measure_mode == "MODE_ID_2":
            return ["lc1", "lc2"]
        elif self.measure_mode == "MODE_ID_3":
            return ["lc1", "lc2", "lc3"]
        return []

    def reset_measurement_safety_state(self):
        self.inactivity_samples.clear()
        self.last_inactivity_sample_time = None

    def update_inactivity_monitor(self, data):
        if not self.is_measuring: return
        now = time.monotonic()

        if self.last_inactivity_sample_time is not None:
            elapsed = (now - self.last_inactivity_sample_time)
            if elapsed < self.inactivity_sample_interval:
                return
        self.last_inactivity_sample_time = now

        total_force = float(data.total_force)
        self.inactivity_samples.append((now, total_force))

        cutoff = (now - self.inactivity_window_seconds)
        while (
            self.inactivity_samples
            and
            self.inactivity_samples[0][0] < cutoff
        ):
            self.inactivity_samples.popleft()

    def check_measurement_safety(self):
        if not self.is_measuring:
            return
        if self.measurement_start_time is None:
            return

        now = time.monotonic()
        elapsed = (now - self.measurement_start_time)

        if elapsed >= self.max_measurement_seconds:
            self.auto_stop_measurement(reason="max_time")
            return

        if elapsed < self.inactivity_window_seconds:
            return

        if len(self.inactivity_samples) < 2:
            return

        cutoff = (now - self.inactivity_window_seconds)
        while (
            self.inactivity_samples
            and
            self.inactivity_samples[0][0] < cutoff
        ):
            self.inactivity_samples.popleft()

        if len(self.inactivity_samples) < 2:
            return

        oldest_time = (self.inactivity_samples[0][0])
        coverage = (now - oldest_time)

        if coverage < (
            self.inactivity_window_seconds
            - 2.0
        ):
            return

        forces = [force for _, force in self.inactivity_samples]
        min_force = min(forces)
        max_force = max(forces)
        variation = (max_force - min_force)

        if variation <= self.inactivity_threshold_n:
            self.auto_stop_measurement(
                reason="inactivity",
                variation=variation
            )

    def auto_stop_measurement(self, reason, variation=None):
        if not self.is_measuring:
            return
        
        self.stop_measurement()

        if reason == "max_time":
            self.ui.operationStateLabel.setText("● 최대 측정시간 도달")
            QMessageBox.information(
                self,
                "측정 자동 종료",
                "최대 측정시간 60분에 도달하여\n"
                "측정을 자동으로 종료했습니다."
            )

        elif reason == "inactivity":
            self.ui.operationStateLabel.setText("● 무활동 자동 종료")
            if variation is None:
                variation = 0.0
            QMessageBox.information(
                self,
                "측정 자동 종료",
                "최근 5분 동안 유효한 힘 변화가 "
                "감지되지 않아\n"
                "측정을 자동으로 종료했습니다.\n\n"
                f"최근 변화폭: {variation:.3f} N\n"
                f"종료 기준: {self.inactivity_threshold_n:.3f} N"
            )

    def select_save_directory(self):
        if self.is_measuring:
            QMessageBox.information(
                self,
                "저장 경로 변경",
                "측정 중에는 저장 경로를 변경할 수 없습니다."
            )
            return
        
        current_directory = str(self.config.get_base_directory())
        folder = QFileDialog.getExistingDirectory(
            self,
            "데이터 저장 폴더 선택",
            current_directory
        )

        if not folder: return

        try:
            self.config.set_save_directory(folder)
            new_session_directory = (self.config.get_save_directory())
            new_session_directory.mkdir(parents=True, exist_ok=True)
            self.csv_manager.set_save_directory(new_session_directory)

        except Exception as e:
            QMessageBox.warning(
                self,
                "저장 경로 변경 실패",
                str(e)
            )
            return

        QMessageBox.information(
            self,
            "저장 경로 변경",
            "데이터 저장 경로를 변경했습니다.\n\n"
            f"{new_session_directory}"
        )

    def save_session_result(self):

        if self.current_grip_id is None:
            return
        if self.measurement_start_time is None:
            return
        
        duration = (time.monotonic() - self.measurement_start_time)

        if self.sample_count > 0:
            average_force = (self.force_sum / self.sample_count)
        else:
            average_force = 0.0

        event_count = len(self.grip_events)
        event_peaks = [event.peak_force_n for event in self.grip_events]

        if event_peaks:
            event_peak_min = min(event_peaks)
            event_peak_max = max(event_peaks)
            event_peak_avg = (sum(event_peaks) / len(event_peaks))
        else:
            event_peak_min = None
            event_peak_avg = None
            event_peak_max = None

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            self.csv_manager.append_session_result(
                grip_id=self.current_grip_id,
                timestamp=timestamp,
                mode=self.measure_mode,

                max_force=self.peak_force,
                average_force=average_force,
                duration=duration,

                event_count=event_count,
                event_peak_min=event_peak_min,
                event_peak_avg=event_peak_avg,
                event_peak_max=event_peak_max
            )

        except Exception as e:
            QMessageBox.warning(
                self,
                "Session 저장 오류",
                "측정 원본 데이터는 저장되었지만 "
                "Session 요약 저장에 실패했습니다."
                f"\n\n{e}"
            )