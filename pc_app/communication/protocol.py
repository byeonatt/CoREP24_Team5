"""
MCU <-> PC 통신 프로토콜(신호) 정의
- 명령(Command) 정의
- 데이터(Packet) 파싱
"""

from dataclasses import dataclass
from enum import Enum

# PC -> MCU 전송할 데이터 패킷
class Command(Enum):
    START = "CMD,START"
    ZERO = "ZERO"
    GET_CAL = "GET_CAL"        # 현재 캘리브레이션 값 요청
    SET_CAL = "SET_CAL"        # 캘리브레이션 값 저장
    MODE_OD = "MODE_OD"         # 외경
    MODE_ID_2 = "MODE_ID_2"     # 내경 2-Jaw
    MODE_ID_3 = "MODE_ID_3"     # 내경 3-Jaw

# MCU -> PC 전송할 데이터 패킷
class PacketType(Enum):
    FORCE = "F"
    STATUS = "S"
    ERROR = "E"
    INFO = "I"
    CALIBRATION = "C"
    DEBUG = "D"

@dataclass
class Packet:
    type: PacketType
    value: str | float

# MCU에서 받은 데이터 패킷
def parse_packet(line:str):

    parts = line.split(",", 1)
    if len(parts) < 2: return None

    code = parts[0]
    value = parts[1]

    if code == "F":
        return Packet(PacketType.FORCE, float(value))
    elif code == "S":
        return Packet(PacketType.STATUS, value)
    elif code == "E":
        return Packet(PacketType.ERROR, value)
    elif code == "I":
        return Packet(PacketType.INFO, value)
    elif code == "C":
        return Packet(PacketType.CALIBRATION, value)
    elif code == "D":
        return Packet(PacketType.DEBUG, value)

    return None

# MCU로 전송할 명령 생성
def create_command(command: Command) -> str:
    return f"CMD,{command.value}"

# 수신 데이터가 정상인지 검사
def validate_packet(line:str):

    if not line: return False
    parts=line.split(",", 1)

    if len(parts)!=2: return False
    if parts[0] not in ["F","S","E","I","C","D"]: return False

    return True