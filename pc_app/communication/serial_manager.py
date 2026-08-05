'''
serial_manager.py
MCU-PC USB Serial 통신 전담 모듈
- 연결, 통신
- 데이터 송/수신
- 연결 상태 : 이벤트 형태로 main에 전달
'''
import serial
import serial.tools.list_ports
from PySide6.QtCore import QObject, Signal

import threading
import time

class SerialManager(QObject):

    line_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.serial_port = None
        self.connected = False
        self.port = config.get_com_port()
        self.device = "Unknown"
        self.baudrate = 115200
        self.receive_thread = None
        self.running = False
        self.last_received_time = time.time()
        self.timeout_limit = 3.0

    ### 통신 연결용 함수 ###
    # 연결(구현) + 끊어진 후 재연결(미구현)
    def connect(self, port, baudrate=115200, device="Unknown") :
        # 이미 연결된 경우
        if self.is_connected():
            if self.port == port :
                return True
            self.disconnect()

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=1
            )

            self.port = port
            self.baudrate = baudrate
            self.device = device
            self.connected = True

            # 연결 상태 전달
            self.connection_changed.emit(True)
            self.running = True

            # 수신 시작
            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            return True

        # 시리얼 관련 오류(연결 끊김 등)
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial 연결 실패: {e}")
            self.connected = False
            self.serial_port = None
            self.port = None
            return False

    # 연결 해제
    def disconnect(self) :
        try:
            self.running = False
            if self.receive_thread is not None:
                self.receive_thread.join(timeout=1)
                self.receive_thread = None

            # Serial 포트가 열려 있는 경우
            if self.serial_port is not None:
                if self.serial_port.is_open:
                    self.serial_port.close()

            # 상태 초기화
            self.connected = False
            self.serial_port = None
            self.port = None

            # 연결 상태 전달
            self.connection_changed.emit(False)

        except Exception as e:
            self.error_occurred.emit(f"Serial 연결 해제 실패: {e}") 

    # 연결 상태 반환
    def is_connected(self) :
        return (
            self.connected
            and self.serial_port is not None
            and self.serial_port.is_open
        )
    
    # 연결 종료 처리
    def close(self) :
        ...

    # COM 포트 검색
    def find_ports(self) :
        ports = []

        try:
            devices = serial.tools.list_ports.comports()
            for device in devices:
                ports.append({
            "port": device.device,
            "description": device.description
        })

        except Exception as e:
            self.error_occurred.emit(f"Serial 포트 검색 실패: {e}")

        return ports

    ### 데이터 송수신용 함수 ###
    # 데이터 읽기
    def read_data(self):
        if not self.is_connected():
            return None
        try:
            if self.serial_port.in_waiting > 0:
                data = self.serial_port.readline()
                return data.decode("utf-8", errors="ignore").strip()
            return None

        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial 수신 실패: {e}")
            self.connected = False
            self.serial_port = None
            self.connection_changed.emit(False)
            return None

    # MCU로 데이터 전송하기
    # 전송 형식 : message + "\n"
    def send_data(self, message):
        if not self.is_connected():
            self.error_occurred.emit("Serial 연결 없음")
            return False
        
        try:
            if isinstance(message, str):
                data = (message + "\n").encode("utf-8")
            elif isinstance(message, bytes):
                data = message
            else:
                raise TypeError("지원하지 않는 데이터 형식")
            self.serial_port.write(data)
            return True
        except serial.SerialException as e:
            self.error_occurred.emit(f"Serial 전송 실패: {e}")
            self.connected = False
            self.serial_port = None
            return False

    # 데이터 수신 반복
    def _receive_loop(self):
        while self.running:
            data = self.read_data()

            if data is not None:
                self.last_received_time = time.time()
                self.line_received.emit(data)