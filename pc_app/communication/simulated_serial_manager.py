"""
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
- 실제 작업 환경을 흉내 낸 자동 Grip Cycle 테스트
  * 약 0.35초 상승
  * 약 2.7~3.3초 파지 유지
  * 약 0.35초 해제
  * Grip 사이 대기
  * 최대 200회 반복

실제 SerialManager와 최대한 동일한 인터페이스를 사용하므로,
main.py에서 SerialManager 대신 이 클래스를 생성하여 사용할 수 있다.

자동 Grip Cycle 테스트 동작
1. Simulator 연결
2. CMD,ZERO 수신
3. 이후 MODE_OD / MODE_ID_2 / MODE_ID_3 중 하나를 수신
4. 약 4초 후 첫 Grip 시작
5. 설정된 횟수까지 자동으로 Grip 반복

기본은 QUICK_TEST=True:
- Grip 유지시간은 실제 환경처럼 약 3초
- Grip 사이 대기시간은 1.5~2.5초로 줄여 테스트를 빠르게 수행

REALISTIC_INTERVAL_TEST=True로 바꾸면:
- Grip 사이 대기시간을 약 12~15초로 늘림
- 200회 측정 시 전체 시간이 실제 작업환경과 비슷하게 길어짐
"""

import math
import random
import time

from PySide6.QtCore import QObject, Signal, QTimer


class SimulatedSerialManager(QObject):

    # 실제 SerialManager와 동일한 Signal
    line_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    connect_finished = Signal(bool, str)

    # =========================================================
    # 자동 Grip 테스트 설정
    # =========================================================

    # False로 바꾸면 기존 수동 set_force() 방식만 사용
    AUTO_GRIP_TEST_ENABLED = True

    # False: 빠른 테스트 (Grip 간격 약 1.5~2.5초)
    # True : 실제 200회/약 1시간 환경에 가까운 간격 (약 12~15초)
    REALISTIC_INTERVAL_TEST = False

    # 한 번의 테스트에서 자동 생성할 Grip 수
    AUTO_GRIP_COUNT = 200

    # 모드 선택 후 첫 Grip이 시작되기까지 대기시간
    FIRST_GRIP_DELAY_S = 4.0

    # 실제 파지 유지 시간 범위
    HOLD_TIME_MIN_S = 2.7
    HOLD_TIME_MAX_S = 3.3

    # 힘 상승/해제 시간
    RAMP_UP_TIME_S = 0.35
    RAMP_DOWN_TIME_S = 0.35

    # 빠른 테스트용 Grip 간 간격
    QUICK_GAP_MIN_S = 1.5
    QUICK_GAP_MAX_S = 2.5

    # 실제 환경에 가까운 Grip 간 간격
    REALISTIC_GAP_MIN_S = 12.0
    REALISTIC_GAP_MAX_S = 15.0

    # Grip마다 사용할 목표 파지력.
    # 예를 들어 판정 기준을 2.8~3.2 N으로 잡으면
    # 2.70 N / 3.30 N 이벤트는 NG 테스트에도 사용할 수 있다.
    AUTO_GRIP_FORCE_PATTERN = (
        3.00,
        3.05,
        2.95,
        3.10,
        2.90,
        2.70,
        3.00,
        3.30,
    )

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

        # -----------------------------------------------------
        # 자동 Grip Cycle용 상태
        # -----------------------------------------------------

        self.auto_grip_timer = QTimer(self)
        self.auto_grip_timer.setInterval(20)  # 50 Hz로 목표 힘 갱신
        self.auto_grip_timer.timeout.connect(
            self._update_auto_grip_cycle
        )

        self.auto_grip_armed = False
        self.auto_grip_running = False

        self.auto_grip_event_index = 0

        self.auto_phase = "IDLE"
        self.auto_phase_start_time = None
        self.auto_phase_duration_s = 0.0

        self.auto_target_force_n = 0.0
        self.auto_hold_time_s = 0.0

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

        self.force_timer.start()

        self.connection_changed.emit(True)
        self.connect_finished.emit(True, "")

    def is_connected(self):
        return self.connected

    def disconnect(self):
        self.force_timer.stop()
        self.stop_auto_grip_test()

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

            if self.AUTO_GRIP_TEST_ENABLED:
                self.stop_auto_grip_test()

                self.simulated_force = 0.0
                self.zero_offset = 0.0

            else:
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

        # CAL_GET / CAL_SET
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

        # =====================================================
        # 현재 Simulator가 이미 만들어놓은 실제 가상 하중
        # =====================================================

        physical_force = (
            self.simulated_force
            - self.zero_offset
        )

        # =====================================================
        # 모드에 따라 실제 하중 분배
        # =====================================================

        if self.mode == "MODE_ID_3":

            physical_lc1 = physical_force / 3.0
            physical_lc2 = physical_force / 3.0
            physical_lc3 = physical_force / 3.0

            factor_key = "id3"

        elif self.mode == "MODE_ID_2":

            physical_lc1 = physical_force / 2.0
            physical_lc2 = physical_force / 2.0
            physical_lc3 = 0.0

            factor_key = "id2"

        else:  # MODE_OD

            physical_lc1 = physical_force / 2.0
            physical_lc2 = physical_force / 2.0
            physical_lc3 = 0.0

            factor_key = "od"

        # =====================================================
        # 가상 센서 RAW 생성
        # =====================================================

        raw_noise1 = random.randint(-15, 15)
        raw_noise2 = random.randint(-15, 15)
        raw_noise3 = random.randint(-15, 15)

        raw1 = int(
            self.raw_baseline[0]
            + physical_lc1
            * self.counts_per_newton
            + raw_noise1
        )

        raw2 = int(
            self.raw_baseline[1]
            + physical_lc2
            * self.counts_per_newton
            + raw_noise2
        )

        raw3 = int(
            self.raw_baseline[2]
            + physical_lc3
            * self.counts_per_newton
            + raw_noise3
        )

        # =====================================================
        # 현재 CAL_SET으로 저장된 Calibration 값
        # =====================================================

        cal1 = self.calibration["LC1"]
        cal2 = self.calibration["LC2"]
        cal3 = self.calibration["LC3"]

        # =====================================================
        # 실제 ESP32 방식으로 Force 계산
        #
        # F = (RAW - TARE) * FORCE_FACTOR
        # =====================================================

        f1 = (
            raw1
            - cal1["tare"]
        ) * cal1[factor_key]

        f2 = (
            raw2
            - cal2["tare"]
        ) * cal2[factor_key]

        f3 = (
            raw3
            - cal3["tare"]
        ) * cal3[factor_key]

        # =====================================================
        # F Packet
        # =====================================================

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

    # =========================================================
    # 자동 Grip Cycle
    # =========================================================

    def _start_auto_grip_if_armed(self):
        """
        정상 사용 순서:
        ZERO -> MODE 선택 -> 측정 시작

        Simulator는 PC App의 '측정 시작' 버튼을 직접 알 수 없으므로,
        MODE 명령을 받은 뒤 FIRST_GRIP_DELAY_S만큼 기다렸다가
        첫 Grip을 시작한다.
        """

        if not self.AUTO_GRIP_TEST_ENABLED:
            return

        if not self.auto_grip_armed:
            return

        self.auto_grip_armed = False

        self.start_auto_grip_test(
            first_delay_s=self.FIRST_GRIP_DELAY_S
        )

    def start_auto_grip_test(
        self,
        first_delay_s=None,
    ):
        """
        자동 Grip 시나리오 시작.

        외부 테스트 코드에서도 직접 호출할 수 있다.
        """

        if first_delay_s is None:
            first_delay_s = (
                self.FIRST_GRIP_DELAY_S
            )

        self.stop_auto_grip_test()

        self.auto_grip_running = True
        self.auto_grip_event_index = 0

        self.simulated_force = 0
        self.zero_offset = 0.0

        self._set_auto_phase(
            "GAP",
            float(first_delay_s),
        )

        self.auto_grip_timer.start()

        interval_mode = (
            "REALISTIC"
            if self.REALISTIC_INTERVAL_TEST
            else "QUICK"
        )

        print(
            "[SIM AUTO] 자동 Grip 테스트 시작 | "
            f"mode={self.mode} | "
            f"events={self.AUTO_GRIP_COUNT} | "
            f"interval={interval_mode}"
        )

    def stop_auto_grip_test(self):
        self.auto_grip_timer.stop()

        self.auto_grip_running = False
        self.auto_phase = "IDLE"
        self.auto_phase_start_time = None
        self.auto_phase_duration_s = 0.0

        self.auto_target_force_n = 0.0
        self.auto_hold_time_s = 0.0

        self.simulated_force = 0.0

    def _set_auto_phase(
        self,
        phase,
        duration_s,
    ):
        self.auto_phase = phase
        self.auto_phase_start_time = (
            time.monotonic()
        )
        self.auto_phase_duration_s = max(
            0.0,
            float(duration_s),
        )

    def _next_gap_seconds(self):
        if self.REALISTIC_INTERVAL_TEST:
            return random.uniform(
                self.REALISTIC_GAP_MIN_S,
                self.REALISTIC_GAP_MAX_S,
            )

        return random.uniform(
            self.QUICK_GAP_MIN_S,
            self.QUICK_GAP_MAX_S,
        )

    def _next_target_force(self):
        pattern = (
            self.AUTO_GRIP_FORCE_PATTERN
        )

        index = (
            self.auto_grip_event_index
            % len(pattern)
        )

        return float(
            pattern[index]
        )

    @staticmethod
    def _smoothstep(progress):
        progress = max(
            0.0,
            min(
                1.0,
                float(progress),
            ),
        )

        return (
            progress
            * progress
            * (3.0 - 2.0 * progress)
        )

    def _update_auto_grip_cycle(self):
        if not self.auto_grip_running:
            return

        if self.auto_phase_start_time is None:
            return

        now = time.monotonic()

        elapsed = (
            now
            - self.auto_phase_start_time
        )

        duration = max(
            self.auto_phase_duration_s,
            1e-6,
        )

        progress = min(
            1.0,
            elapsed / duration,
        )

        # -----------------------------------------------------
        # Grip 사이 대기
        # -----------------------------------------------------

        if self.auto_phase == "GAP":
            self.simulated_force = 0.0

            if progress >= 1.0:
                if (
                    self.auto_grip_event_index
                    >= self.AUTO_GRIP_COUNT
                ):
                    print(
                        "[SIM AUTO] 자동 Grip 테스트 완료 | "
                        f"{self.AUTO_GRIP_COUNT}회"
                    )

                    self.stop_auto_grip_test()
                    return

                self.auto_target_force_n = (
                    self._next_target_force()
                )

                self.auto_hold_time_s = (
                    random.uniform(
                        self.HOLD_TIME_MIN_S,
                        self.HOLD_TIME_MAX_S,
                    )
                )

                print(
                    "[SIM AUTO] "
                    f"Grip #{self.auto_grip_event_index + 1} 시작 | "
                    f"target={self.auto_target_force_n:.3f} N | "
                    f"hold={self.auto_hold_time_s:.2f} s"
                )

                self._set_auto_phase(
                    "RAMP_UP",
                    self.RAMP_UP_TIME_S,
                )

            return

        # -----------------------------------------------------
        # 힘 상승
        # -----------------------------------------------------

        if self.auto_phase == "RAMP_UP":
            smooth = self._smoothstep(
                progress
            )

            self.simulated_force = (
                self.auto_target_force_n
                * smooth
            )

            if progress >= 1.0:
                self.simulated_force = (
                    self.auto_target_force_n
                )

                self._set_auto_phase(
                    "HOLD",
                    self.auto_hold_time_s,
                )

            return

        # -----------------------------------------------------
        # 2.7 ~ 3.3초 유지
        # -----------------------------------------------------

        if self.auto_phase == "HOLD":
            # 실제 파지처럼 완전히 직선이 아니라
            # 아주 작은 저주파 흔들림 + 미세 랜덤 변동을 넣는다.
            slow_wave = (
                0.010
                * math.sin(
                    elapsed
                    * 2.0
                    * math.pi
                    * 0.7
                )
            )

            micro_noise = random.uniform(
                -0.006,
                0.006,
            )

            # 유지 후반부에 약 0.5% 정도의 미세한 힘 저하
            droop = (
                self.auto_target_force_n
                * 0.005
                * progress
            )

            self.simulated_force = max(
                0.0,
                self.auto_target_force_n
                + slow_wave
                + micro_noise
                - droop
            )

            if progress >= 1.0:
                self._set_auto_phase(
                    "RAMP_DOWN",
                    self.RAMP_DOWN_TIME_S,
                )

            return

        # -----------------------------------------------------
        # 힘 해제
        # -----------------------------------------------------

        if self.auto_phase == "RAMP_DOWN":
            smooth = self._smoothstep(
                progress
            )

            self.simulated_force = (
                self.auto_target_force_n
                * (1.0 - smooth)
            )

            if progress >= 1.0:
                self.simulated_force = 0.0

                self.auto_grip_event_index += 1

                print(
                    "[SIM AUTO] "
                    f"Grip #{self.auto_grip_event_index} 해제"
                )

                self._set_auto_phase(
                    "GAP",
                    self._next_gap_seconds(),
                )

            return

    # ---------------------------------------------------------
    # 테스트 제어용 함수
    # ---------------------------------------------------------

    def set_force(self, force):
        """
        가상 전체 파지력 입력값 설정.

        수동 Force 테스트를 시작하면 자동 Grip 시나리오는 중지한다.
        """
        self.stop_auto_grip_test()
        self.auto_grip_armed = False
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
        self.stop_auto_grip_test()

        self.mode = "MODE_OD"
        self.status = 0x36
        self.data_enabled = True
        self.simulated_force = 0.0
        self.zero_offset = 0.0

        self.auto_grip_armed = False
        self.auto_grip_event_index = 0

    # ---------------------------------------------------------
    # CAL_GET 테스트용 기본 응답
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
