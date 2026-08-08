"""
MCU <-> PC 통신 프로토콜(신호) 정의
- 명령(Command) 정의
- 데이터(Packet) 파싱
"""

from dataclasses import dataclass
from enum import Enum

# PC -> MCU 전송할 데이터 패킷
class Command(Enum):
    START = "START"
    ZERO = "ZERO"

    GET_CAL = "CAL_GET"        # 현재 캘리브레이션 값 요청
    SET_CAL = "CAL_SET"        # 캘리브레이션 값 저장
    MODE_OD = "MODE_OD"         # 외경
    MODE_ID_2 = "MODE_ID_2"     # 내경 2-Jaw
    MODE_ID_3 = "MODE_ID_3"     # 내경 3-Jaw

# MCU -> PC 전송할 데이터 패킷
class PacketType(Enum):
    FORCE = "F"
    READY = "READY"
    CALIBRATION = "CAL_GET"

@dataclass
class ForceData:
    raw_lc1: int
    raw_lc2: int
    raw_lc3: int
    force_lc1: float
    force_lc2: float
    force_lc3: float
    status: int

    @property
    def total_force(self):
        return (self.force_lc1+self.force_lc2+self.force_lc3)

    @property
    def status_ok(self):
        return self.status in (0x36, 0x37)

@dataclass
class CalibrationData:
    load_cell: str
    tare: float
    od_factor: float
    id2_factor: float
    id3_factor: float

@dataclass
class Packet:
    type: PacketType
    value: ForceData | CalibrationData | str


# MCU에서 받은 데이터 패킷
def parse_packet(line: str):

    if not line: return None
    parts = [part.strip() for part in line.strip().split(",")]

    if not parts: return None
    code = parts[0]

    try:
        if code == "F":
            if len(parts) != 8: return None

            status = int(parts[7], 0)

            data = ForceData(
                raw_lc1=int(parts[1]),
                raw_lc2=int(parts[2]),
                raw_lc3=int(parts[3]),

                force_lc1=float(parts[4]),
                force_lc2=float(parts[5]),
                force_lc3=float(parts[6]),

                status=status
            )
            return Packet(PacketType.FORCE, data)

        elif code == "READY":
            if len(parts) != 2:
                return None
            if parts[1] != "ESP32":
                return None
            return Packet(PacketType.READY, parts[1])

        elif code == "CAL_GET":

            if len(parts) != 6:return None

            data = CalibrationData(
                load_cell=parts[1],
                tare=float(parts[2]),
                od_factor=float(parts[3]),
                id2_factor=float(parts[4]),
                id3_factor=float(parts[5])
            )

            return Packet(PacketType.CALIBRATION, data)

    except (ValueError, TypeError): return None

    return None


# MCU로 전송할 명령 생성
def create_command(command: Command) -> str:
    return f"CMD,{command.value}"
