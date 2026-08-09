from pathlib import Path
import math

from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt

from communication.protocol import (
    parse_packet,
    PacketType,
    Command,
    create_command,
    create_cal_set_command
)


class CalibrationWindow(QMainWindow):

    def __init__(self, serial_manager=None):
        super().__init__()

        self.serial_manager = serial_manager

        # CAL_GET으로 받은 LC별 데이터
        self.calibration_values = {}

        self.verify_in_progress = False
        self.pending_calibration = None

        self.cal_verify_delay_ms = 300

        self.factor_abs_tolerance = 1e-12
        self.factor_rel_tolerance = 1e-6

        ui_path = Path(__file__).parent / "calibration.ui"
        ui_file = QFile(str(ui_path))

        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(f"Cannot open {ui_path}")

        self.ui = QUiLoader().load(ui_file)
        ui_file.close()

        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setWindowTitle("Calibration")

        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setFixedSize(self.ui.size())

        self.ui.applyButton.setEnabled(False)

        self.cal_get_timer = QTimer(self)
        self.cal_get_timer.setSingleShot(True)
        self.cal_get_timer.timeout.connect(
            self.handle_cal_get_timeout
        )
        self.cal_verify_timer = QTimer(self)
        self.cal_verify_timer.setSingleShot(True)
        self.cal_verify_timer.timeout.connect(
            self.handle_cal_verify_timeout
        )

        self.connect_signal()
        self.clear_fields()

        QTimer.singleShot(0, self.request_calibration)

    def connect_signal(self):
        self.ui.applyButton.clicked.connect(self.apply_calibration)
        if not self.serial_manager:
            return
        self.serial_manager.line_received.connect(self.receive_data)
        self.serial_manager.connection_changed.connect(self.handle_connection_changed)

    def request_calibration(self):
        if not self.serial_manager:
            QMessageBox.warning(
                self,
                "캘리브레이션 조회 실패",
                "SerialManager가 없습니다."
            )
            return

        if not self.serial_manager.is_connected():
            QMessageBox.warning(
                self,
                "캘리브레이션 조회 실패",
                "ESP32와 Serial 연결이 되어 있지 않습니다."
            )
            return

        self.calibration_values.clear()
        self.clear_fields()
        self.ui.applyButton.setEnabled(False)

        command = create_command(Command.GET_CAL)

        if self.serial_manager.send_data(command):
            self.cal_get_timer.start(1500)
        else:
            QMessageBox.warning(
                self,
                "캘리브레이션 조회 실패",
                "CMD,CAL_GET 전송에 실패했습니다."
            )

    def receive_data(self, line):
        packet = parse_packet(line)

        if packet is None:
            return

        # F / READY 패킷은 CalibrationWindow에서 무시
        if packet.type != PacketType.CALIBRATION:
            return

        data = packet.value

        if data.load_cell not in ("LC1", "LC2", "LC3",):
            return

        self.calibration_values[data.load_cell] = data
        self.populate_load_cell(data)

        if all(
            lc in self.calibration_values
            for lc in ("LC1", "LC2", "LC3")
        ):

            if self.verify_in_progress:
                if self.cal_verify_timer.isActive():
                    self.cal_verify_timer.stop()
                self.verify_calibration_values()
                return

            if self.cal_get_timer.isActive():
                self.cal_get_timer.stop()

            self.ui.applyButton.setEnabled(True)


    @staticmethod
    def format_number(value):
        # TARE와 작은 Force Factor를 모두 보기 좋게 표시
        return f"{value:.12g}"

    def populate_load_cell(self, data):
        widgets = {
            "LC1": {
                "tare": self.ui.txtLC1Tare,
                "od": self.ui.txtLC1ODFactor,
                "id2": self.ui.txtLC1ID2Factor,
                "id3": self.ui.txtLC1ID3Factor,
            },
            "LC2": {
                "tare": self.ui.txtLC2Tare,
                "od": self.ui.txtLC2ODFactor,
                "id2": self.ui.txtLC2ID2Factor,
                "id3": self.ui.txtLC2ID3Factor,
            },
            "LC3": {
                "tare": self.ui.txtLC3Tare,
                "od": self.ui.txtLC3ODFactor,
                "id2": self.ui.txtLC3ID2Factor,
                "id3": self.ui.txtLC3ID3Factor,
            },
        }

        row = widgets[data.load_cell]
    
        row["tare"].setText(self.format_number(data.tare))
        row["od"].setText(self.format_number(data.od_factor))
        row["id2"].setText(self.format_number(data.id2_factor))
        row["id3"].setText(self.format_number(data.id3_factor))

    def clear_fields(self):
        fields = [
            self.ui.txtLC1Tare,
            self.ui.txtLC1ODFactor,
            self.ui.txtLC1ID2Factor,
            self.ui.txtLC1ID3Factor,

            self.ui.txtLC2Tare,
            self.ui.txtLC2ODFactor,
            self.ui.txtLC2ID2Factor,
            self.ui.txtLC2ID3Factor,

            self.ui.txtLC3Tare,
            self.ui.txtLC3ODFactor,
            self.ui.txtLC3ID2Factor,
            self.ui.txtLC3ID3Factor,
        ]

        for field in fields:
            field.clear()

    def handle_cal_get_timeout(self):
        expected = {"LC1", "LC2", "LC3",}
        received = set(self.calibration_values.keys())
        missing = sorted(expected - received)
        self.ui.applyButton.setEnabled(False)
        QMessageBox.warning(
            self,
            "캘리브레이션 조회 실패",
            "CAL_GET 응답이 완전히 수신되지 않았습니다.\n\n"
            f"미수신: {', '.join(missing)}"
        )

    def handle_connection_changed(self, connected):

        if connected: return

        if self.cal_get_timer.isActive():
            self.cal_get_timer.stop()

        if self.cal_verify_timer.isActive():
            self.cal_verify_timer.stop()

        self.verify_in_progress = False
        self.pending_calibration = None
        self.calibration_values.clear()

        self.ui.applyButton.setEnabled(False)


    def closeEvent(self, event):

        if self.cal_get_timer.isActive():
            self.cal_get_timer.stop()

        if self.cal_verify_timer.isActive():
            self.cal_verify_timer.stop()

        self.verify_in_progress = False
        self.pending_calibration = None

        if self.serial_manager:
            try: self.serial_manager.line_received.disconnect(self.receive_data)
            except (TypeError, RuntimeError): pass

            try: self.serial_manager.connection_changed.disconnect(self.handle_connection_changed)
            except (TypeError, RuntimeError): pass

        event.accept()

        event.accept()
    def apply_calibration(self):

        if not self.serial_manager:
            QMessageBox.warning(
                self,
                "캘리브레이션 저장 실패",
                "SerialManager가 없습니다."
            )
            return

        if not self.serial_manager.is_connected():
            QMessageBox.warning(
                self,
                "캘리브레이션 저장 실패",
                "ESP32가 연결되어 있지 않습니다."
            )
            return

        try:
            # LC1
            tare1 = float(self.ui.txtLC1Tare.text())
            od_f1 = float(self.ui.txtLC1ODFactor.text())
            id2_f1 = float(self.ui.txtLC1ID2Factor.text())
            id3_f1 = float(self.ui.txtLC1ID3Factor.text())

            # LC2
            tare2 = float(self.ui.txtLC2Tare.text())
            od_f2 = float(self.ui.txtLC2ODFactor.text())
            id2_f2 = float(self.ui.txtLC2ID2Factor.text())
            id3_f2 = float(self.ui.txtLC2ID3Factor.text())

            # LC3
            tare3 = float(self.ui.txtLC3Tare.text())
            od_f3 = float(self.ui.txtLC3ODFactor.text())
            id2_f3 = float(self.ui.txtLC3ID2Factor.text())
            id3_f3 = float(self.ui.txtLC3ID3Factor.text())

        except ValueError:
            QMessageBox.warning(
                self,
                "입력 오류",
                "모든 캘리브레이션 항목에 "
                "숫자를 입력해 주세요."
            )
            return

        try:
            # LC1
            self.validate_calibration_value("LC1 TARE", tare1, "tare")
            self.validate_calibration_value("LC1 OD Factor", od_f1, "factor")
            self.validate_calibration_value("LC1 ID2 Factor", id2_f1, "factor")
            self.validate_calibration_value("LC1 ID3 Factor", id3_f1, "factor")

            # LC2
            self.validate_calibration_value("LC2 TARE", tare2, "tare")
            self.validate_calibration_value("LC2 OD Factor", od_f2, "factor")
            self.validate_calibration_value("LC2 ID2 Factor", id2_f2, "factor")
            self.validate_calibration_value("LC2 ID3 Factor", id3_f2, "factor")

            # LC3
            self.validate_calibration_value("LC3 TARE", tare3, "tare")
            self.validate_calibration_value("LC3 OD Factor", od_f3, "factor")
            self.validate_calibration_value("LC3 ID2 Factor", id2_f3, "factor")
            self.validate_calibration_value("LC3 ID3 Factor", id3_f3, "factor")    

        except ValueError as e:
            QMessageBox.warning(
                self,
                "캘리브레이션 입력 오류",
                str(e)
            )
            return

        self.pending_calibration = {
            "LC1": {
                "tare": tare1,
                "od": od_f1,
                "id2": id2_f1,
                "id3": id3_f1,
            },
            "LC2": {
                "tare": tare2,
                "od": od_f2,
                "id2": id2_f2,
                "id3": id3_f2,
            },
            "LC3": {
                "tare": tare3,
                "od": od_f3,
                "id2": id2_f3,
                "id3": id3_f3,
            },
        }

        command = create_cal_set_command(
            tare1, od_f1, id2_f1, id3_f1,
            tare2, od_f2, id2_f2, id3_f2,
            tare3, od_f3, id2_f3, id3_f3
        )

        if not self.serial_manager.send_data(command):
            self.pending_calibration = None

            QMessageBox.warning(
                self,
                "캘리브레이션 저장 실패",
                "CMD,CAL_SET 전송에 실패했습니다."
            )
            return
        
        self.verify_in_progress = True
        self.ui.applyButton.setEnabled(False)
        self.calibration_values.clear()

        QTimer.singleShot(
            self.cal_verify_delay_ms,
            self.request_calibration_verification
        )

    def request_calibration_verification(self):

        if not self.verify_in_progress: return
        if not self.serial_manager:
            self.finish_calibration_verification(
                False,
                "SerialManager가 없습니다."
            )
            return
        if not self.serial_manager.is_connected():
            self.finish_calibration_verification(
                False,
                "ESP32 연결이 끊어졌습니다."
            )
            return

        self.calibration_values.clear()

        command = create_command(Command.GET_CAL)
        if self.serial_manager.send_data(command):
            self.cal_verify_timer.start(1500)
        else:
            self.finish_calibration_verification(False, "저장값 확인을 위한 CAL_GET 전송에 실패했습니다.")

    def verify_calibration_values(self):

        if self.pending_calibration is None:
            self.finish_calibration_verification(False, "비교할 캘리브레이션 값이 없습니다.")
            return

        mismatches = []

        for lc in ("LC1", "LC2", "LC3"):

            expected = self.pending_calibration[lc]
            actual = self.calibration_values[lc]

            if not math.isclose(
                expected["tare"],
                actual.tare,
                rel_tol=0.0,
                abs_tol=0.5
            ):
                mismatches.append(
                    f"{lc} TARE: "
                    f"{expected['tare']} → {actual.tare}"
                )

            comparisons = [
                ("OD", expected["od"], actual.od_factor),
                ("ID2", expected["id2"], actual.id2_factor),
                ("ID3", expected["id3"], actual.id3_factor),
            ]

            for name, expected_value, actual_value in comparisons:
                if not math.isclose(
                    expected_value,
                    actual_value,
                    rel_tol=self.factor_rel_tolerance,
                    abs_tol=self.factor_abs_tolerance
                ):
                    mismatches.append(
                        f"{lc} {name}: "
                        f"{expected_value} → {actual_value}"
                    )

        if mismatches:
            message = (
                "CAL_SET 후 다시 읽은 값이 "
                "입력값과 일치하지 않습니다.\n\n"
                + "\n".join(mismatches)
            )
            self.finish_calibration_verification(False, message)

        else:
            self.finish_calibration_verification(
                True,
                "캘리브레이션 값이 정상적으로 저장되었습니다."
            )

    def finish_calibration_verification(self, success, message):
        self.verify_in_progress = False
        self.pending_calibration = None

        if self.cal_verify_timer.isActive():
            self.cal_verify_timer.stop()

        self.ui.applyButton.setEnabled(True)

        if success:
            QMessageBox.information(
                self,
                "캘리브레이션 저장 완료",
                message
            )
        else:
            QMessageBox.warning(
                self,
                "캘리브레이션 저장 확인 실패",
                message
            )

    def handle_cal_verify_timeout(self):

        if not self.verify_in_progress:
            return

        expected = {"LC1", "LC2", "LC3",}
        received = set(self.calibration_values.keys())
        missing = sorted(expected - received)

        self.finish_calibration_verification(
            False,
            "CAL_SET 후 저장값 확인 응답이 "
            "완전히 수신되지 않았습니다.\n\n"
            f"미수신: {', '.join(missing)}"
        )


    def validate_calibration_value(self, name, value, value_type):

        if not math.isfinite(value):
            raise ValueError(f"{name}: 유효한 숫자가 아닙니다.")

        if value_type == "tare":
            # ADS1256 signed 24-bit 범위
            if not (-8388608 <= value <= 8388607):
                raise ValueError(
                    f"{name}: "
                    "TARE 값이 ADS1256 허용 범위를 "
                    "벗어났습니다."
                )
            
        elif value_type == "factor":
            if value == 0:
                raise ValueError(
                    f"{name}: "
                    "Force Factor는 0일 수 없습니다."
                )

            if abs(value) > 1.0:
                raise ValueError(
                    f"{name}: "
                    "Force Factor 값이 지나치게 큽니다."
                )

        else:
            raise ValueError(
                f"{name}: "
                "알 수 없는 캘리브레이션 값 종류입니다."
            )