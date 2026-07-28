"""
STM32 <-> PC 통신 프로토콜(신호) 정의
- 명령(Command) 정의
- 데이터(Packet) 파싱
"""

from dataclasses import dataclass
from enum import Enum

# PC -> STM32 전송할 명령 리스트
class Command(Enum):
    START = "START"
    STOP = "STOP"
    ZERO = "ZERO"
    CAL = "CAL"

# 측정 데이터에 포함되는 정보 리스트
class MeasurementPacket:
    force: float
    torque: float | None = None

# STM32에서 받은 문자열을 MeasurementPacket으로 변환
def parse_measurement(line: str) -> MeasurementPacket:
        """
        Example
        -------
        "12.53"
        "12.53,0.042"
        """
        raise NotImplementedError

# STM32로 전송할 명령 생성
def create_command(command: Command) -> bytes:
        """
        Example
        -------
        Command.START
            ↓
        b"START\\n"
        """
        raise NotImplementedError

# 수신 데이터가 정상인지 검사
def validate_packet(line: str) -> bool:
        raise NotImplementedError