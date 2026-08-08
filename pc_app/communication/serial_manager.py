'''
serial_manager.py
MCU-PC USB Serial 통신 전담 모듈
- 연결, 통신
- 데이터 송/수신
- 연결 상태 : 이벤트 형태로 main에 전달
'''
import serial
import serial.tools.list_ports
import json
import platform
import subprocess
from PySide6.QtCore import QObject, Signal

import threading
import time

class SerialManager(QObject):

    line_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    connect_finished = Signal(bool, str)

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
        self.connect_thread = None
        self.connecting = False
        self.last_received_time = time.time()
        self.timeout_limit = 3.0

    ### 통신 연결용 함수 ###
    # 연결(구현) + 끊어진 후 재연결(미구현)
    def connect_async(self, port, baudrate=115200, device="Unknown"):
        # 이미 연결 시도 중이면 중복 실행 방지
        if self.connecting: return

        self.connecting = True
        self.connect_thread = threading.Thread(
            target=self._connect_worker,
            args=(port, baudrate, device),
            daemon=True
        )

        self.connect_thread.start()

    def _connect_worker(self, port, baudrate, device):
        success = False
        message = ""

        try:
            # 이미 연결되어 있는 경우
            if self.is_connected():

                # 같은 포트면 그대로 성공 처리
                if self.port == port:
                    success = True
                else:
                    self.disconnect()

            # 새 연결이 필요한 경우
            if not success:

                serial_port = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.2,
                    write_timeout=0.5
                )

                self.serial_port = serial_port
                self.port = port
                self.baudrate = baudrate
                self.device = device

                self.connected = True
                self.running = True

                self.receive_thread = threading.Thread(
                    target=self._receive_loop,
                    daemon=True
                )

                self.receive_thread.start()
                self.connection_changed.emit(True)
                success = True

        except (serial.SerialException, OSError) as e:
            self.connected = False
            self.running = False
            if self.serial_port is not None:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except Exception:
                    pass

            self.serial_port = None
            self.port = None
            message = f"Serial 연결 실패:\n{e}"

        except Exception as e:
            self.connected = False
            self.running = False
            self.serial_port = None
            message = f"연결 중 예상하지 못한 오류:\n{e}"

        finally:
            self.connecting = False
            self.connect_finished.emit(success, message)

    # 연결 해제
    def disconnect(self) :
        try:
            self.running = False
            if self.receive_thread is not None:
                self.receive_thread.join(timeout=0.5)
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
        self.disconnect()

    # 실제 연결이 가능한 USB포트 검색
    def find_ports(self):
        ports = []

        try:
            devices = serial.tools.list_ports.comports()

            for device in sorted(devices, key=lambda x: x.device):
                ports.append({
                    "port": device.device,
                    "description": device.description,
                    "hwid": device.hwid,

                    "vid": device.vid,
                    "pid": device.pid,

                    "serial_number": device.serial_number,
                    "manufacturer": device.manufacturer,
                    "product": device.product,
                    "interface": device.interface,

                    "connectable": True
                })

        except Exception as e:
            self.error_occurred.emit(f"Serial 포트 검색 실패: {e}")

        return ports

    def find_usb_candidates(self):
        if platform.system() != "Windows": return []

        try:
            powershell_script = r"""
            [Console]::OutputEncoding =
                [System.Text.Encoding]::UTF8

            Get-PnpDevice -PresentOnly |
            Select-Object Status,Class,FriendlyName,InstanceId |
            ConvertTo-Json -Compress
            """

            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    powershell_script
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode != 0: return []

            output = result.stdout.strip()
            if not output: return []

            devices = json.loads(output)

            # 장치가 하나뿐이면 dict로 반환될 수 있음
            if isinstance(devices, dict):
                devices = [devices]

            candidates = []

            keywords = (
                "ESP32",
                "ESPRESSIF",
                "USB SERIAL",
                "USB-SERIAL",
                "SERIAL/JTAG",
                "USB JTAG",
                "CP210",
                "CH340",
                "CH341",
                "UART",
                "CDC"
            )

            known_vids = (
                "VID_303A",   # Espressif
                "VID_10C4",   # Silicon Labs CP210x
                "VID_1A86",   # WCH CH34x
                "VID_0403"    # FTDI
            )

            for device in devices:
                name = str(device.get("FriendlyName") or "")
                instance_id = str(device.get("InstanceId") or "")
                class_name = str(device.get("Class") or "")
                combined = (name + " " + instance_id).upper()

                is_candidate = (
                    any(keyword in combined for keyword in keywords)
                    or any(vid in combined for vid in known_vids)
                )

                if not is_candidate:
                    continue

                # 이미 COM 포트가 생성된 장치는
                # find_ports()에서 처리하므로 제외
                if "(COM" in name.upper():
                    continue

                candidates.append({
                    "name": name or "알 수 없는 USB 장치",
                    "class": class_name,
                    "status": device.get("Status"),
                    "instance_id": instance_id,
                    "connectable": False
                })

            return candidates

        except Exception: return []

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
            else: time.sleep(0.001)