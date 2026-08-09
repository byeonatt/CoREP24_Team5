"""
simulated_serial_manager.py

ESP32가 없는 환경에서 PC App을 테스트하기 위한 가상 SerialManager.

지원 기능
- 가상 포트 SIM1
- CMD,START -> READY,ESP32
- 약 100 Hz F 패킷 발생
- CMD,ZERO
- CMD,MODE_OD
- CMD,MODE_ID_2
- CMD,MODE_ID_3
- ADS1256 STATUS 변경
- 데이터 송신 일시정지/재개
- 가상 하중 변경

실제 SerialManager와 최대한 동일한 인터페이스를 사용하므로,
main.py에서 SerialManager 대신 이 클래스를 생성하여 사용할 수 있다.
"""

import random

from PySide6.QtCore import QObject, Signal, QTimer


class SimulatedSerialManager(QObject):

    # 실제 SerialManager와 동일한 Signal
    line_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    connect_finished = Signal(bool, str)

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.connected = False
        self.connecting = False

        self.port = None
        self.device = "ESP32 Simulator"
        self.baudrate = 115200

        # 현재 측정 모드
        self.mode = "MODE_OD"

        # ADS1256 STATUS
        self.status = 0x36

        # F 패킷 송신 여부
        self.data_enabled = True

        # 가상 입력 하중
        self.simulated_force = 0.0

        # ZERO 명령 적용용 offset
        self.zero_offset = 0.0

        # 가상 RAW baseline
        self.raw_baseline = [
            -12500,
            -12000,
            -13000,
        ]

        # 단순 시뮬레이션용 RAW scale
        self.counts_per_newton = 5000

        # 약 100 Hz
        self.force_timer = QTimer(self)
        self.force_timer.setInterval(10)
        self.force_timer.timeout.connect(
            self._emit_force_packet
        )

        self.calibration = {
            "LC1": {
                "tare": -12500.0,
                "od": 0.000200,
                "id2": 0.000200,
                "id3": 0.000200,
            },
            "LC2": {
                "tare": -12000.0,
                "od": 0.000200,
                "id2": 0.000200,
                "id3": 0.000200,
            },
            "LC3": {
                "tare": -13000.0,
                "od": 0.000200,
                "id2": 0.000200,
                "id3": 0.000200,
            },
        }

    # ---------------------------------------------------------
    # 장치 검색
    # ---------------------------------------------------------

    def find_ports(self):
        """ConnectDialog에 표시할 가상 Serial 포트."""

        return [
            {
                "port": "SIM1",
                "description": "ESP32 Simulator",
                "hwid": "SIMULATED",
                "vid": None,
                "pid": None,
                "serial_number": "SIM001",
                "manufacturer": "Python Simulator",
                "product": "ESP32 Simulator",
                "interface": "Virtual Serial",
                "connectable": True,
            }
        ]

    def find_usb_candidates(self):
        return []

    # ---------------------------------------------------------
    # 연결
    # ---------------------------------------------------------

    def connect_async(
        self,
        port,
        baudrate=115200,
        device="ESP32 Simulator",
    ):
        if self.connecting:
            return

        self.connecting = True

        self.port = port
        self.baudrate = baudrate
        self.device = device

        # 실제 연결처럼 짧은 지연 후 완료
        QTimer.singleShot(
            200,
            self._finish_connect,
        )

    def _finish_connect(self):
        self.connecting = False
        self.connected = True

        # 먼저 수신 가능한 상태로 만든 뒤
        # 실제 SerialManager와 같은 순서로 상태 전달
        self.force_timer.start()

        self.connection_changed.emit(True)
        self.connect_finished.emit(True, "")

    def is_connected(self):
        return self.connected

    def disconnect(self):
        self.force_timer.stop()

        was_connected = self.connected

        self.connected = False
        self.connecting = False
        self.port = None

        if was_connected:
            self.connection_changed.emit(False)

    def close(self):
        self.disconnect()

    # ---------------------------------------------------------
    # PC -> MCU 명령 처리
    # ---------------------------------------------------------

    def send_data(self, message):
        if not self.connected:
            self.error_occurred.emit(
                "Simulator 연결 없음"
            )
            return False

        if isinstance(message, bytes):
            message = message.decode(
                "utf-8",
                errors="ignore",
            )

        if not isinstance(message, str):
            self.error_occurred.emit(
                "Simulator가 지원하지 않는 데이터 형식"
            )
            return False

        message = message.strip()

        print(
            "[SIM RX]",
            message,
        )

        # Handshake
        if message == "CMD,START":
            QTimer.singleShot(
                100,
                self._emit_ready,
            )
            return True

        # ZERO
        if message == "CMD,ZERO":
            self.zero_offset = (
                self.simulated_force
            )
            return True

        # 측정 모드
        if message == "CMD,MODE_OD":
            self.mode = "MODE_OD"
            return True

        if message == "CMD,MODE_ID_2":
            self.mode = "MODE_ID_2"
            return True

        if message == "CMD,MODE_ID_3":
            self.mode = "MODE_ID_3"
            return True

        # CAL_GET / CAL_SET은 추후 캘리브레이션 개발 시 확장 가능
        if message == "CMD,CAL_GET":
            self._emit_default_calibration()
            return True

        if message.startswith("CMD,CAL_SET"):
            return self._handle_cal_set(message)

        # 현재 시뮬레이터에서는 알 수 없는 명령도
        # Serial write 자체는 성공한 것으로 처리
        return True

    def _emit_ready(self):
        if not self.connected:
            return

        self.line_received.emit(
            "READY,ESP32"
        )

    # ---------------------------------------------------------
    # MCU -> PC F 패킷 생성
    # ---------------------------------------------------------

    def _emit_force_packet(self):
        if not self.connected:
            return

        if not self.data_enabled:
            return

        force = (
            self.simulated_force
            - self.zero_offset
        )

        noise1 = random.uniform(
            -0.003,
            0.003,
        )
        noise2 = random.uniform(
            -0.003,
            0.003,
        )
        noise3 = random.uniform(
            -0.003,
            0.003,
        )

        # 3-Jaw는 세 채널 사용
        if self.mode == "MODE_ID_3":
            f1 = force / 3.0 + noise1
            f2 = force / 3.0 + noise2
            f3 = force / 3.0 + noise3

        # 외경 / 내경 2-Jaw는 LC1, LC2 중심으로 시뮬레이션
        else:
            f1 = force / 2.0 + noise1
            f2 = force / 2.0 + noise2
            f3 = noise3

        raw1 = int(
            self.raw_baseline[0]
            + f1 * self.counts_per_newton
        )
        raw2 = int(
            self.raw_baseline[1]
            + f2 * self.counts_per_newton
        )
        raw3 = int(
            self.raw_baseline[2]
            + f3 * self.counts_per_newton
        )

        packet = (
            f"F,"
            f"{raw1},"
            f"{raw2},"
            f"{raw3},"
            f"{f1:.6f},"
            f"{f2:.6f},"
            f"{f3:.6f},"
            f"0x{self.status:02X}"
        )

        self.line_received.emit(
            packet
        )

    # ---------------------------------------------------------
    # 테스트 제어용 함수
    # ---------------------------------------------------------

    def set_force(self, force):
        """가상 전체 파지력 입력값 설정."""
        self.simulated_force = float(force)

    def set_adc_status(self, status):
        """
        ADS1256 STATUS 변경.

        예:
        set_adc_status(0x36)  # 정상
        set_adc_status(0x31)  # 비정상 테스트
        """
        self.status = int(status)

    def pause_data(self):
        """F 패킷 발생 중단 -> watchdog 테스트."""
        self.data_enabled = False

    def resume_data(self):
        """F 패킷 발생 재개."""
        self.data_enabled = True

    def reset_simulator(self):
        """시뮬레이터 상태 초기화."""
        self.mode = "MODE_OD"
        self.status = 0x36
        self.data_enabled = True
        self.simulated_force = 0.0
        self.zero_offset = 0.0

    # ---------------------------------------------------------
    # 향후 CAL_GET 테스트용 기본 응답
    # ---------------------------------------------------------

    def _emit_default_calibration(self):

        if not self.connected:
            return

        packets = []

        for lc in ("LC1", "LC2", "LC3"):

            values = self.calibration[lc]

            packet = (
                f"CAL_GET,"
                f"{lc},"
                f"{values['tare']},"
                f"{values['od']},"
                f"{values['id2']},"
                f"{values['id3']}"
            )

            packets.append(packet)

        for index, packet in enumerate(packets):

            QTimer.singleShot(
                20 * index,
                lambda p=packet:
                    self.line_received.emit(p)
            )

    def _handle_cal_set(self, message):

        try:
            parts = [
                value.strip()
                for value in message.split(",")
            ]

            # CMD,CAL_SET + 12개 숫자
            if len(parts) != 14:
                self.error_occurred.emit(
                    "Simulator CAL_SET 형식 오류"
                )
                return False

            values = [
                float(value)
                for value in parts[2:]
            ]

            self.calibration["LC1"] = {
                "tare": values[0],
                "od": values[1],
                "id2": values[2],
                "id3": values[3],
            }

            self.calibration["LC2"] = {
                "tare": values[4],
                "od": values[5],
                "id2": values[6],
                "id3": values[7],
            }

            self.calibration["LC3"] = {
                "tare": values[8],
                "od": values[9],
                "id2": values[10],
                "id3": values[11],
            }

            return True

        except ValueError:

            self.error_occurred.emit(
                "Simulator CAL_SET 숫자 변환 오류"
            )

            return False
