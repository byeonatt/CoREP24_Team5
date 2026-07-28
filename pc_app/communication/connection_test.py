from PySide6.QtCore import QCoreApplication
from serial_manager import SerialManager


def on_connection_changed(status):
    if status:
        print("[Signal] Serial 연결됨")
    else:
        print("[Signal] Serial 연결 해제됨")


def on_error(message):
    print(f"[Signal Error] {message}")


def main():

    # PySide6 Signal 사용을 위한 Application 생성
    app = QCoreApplication([])

    manager = SerialManager()

    # Signal 연결
    manager.connection_changed.connect(
        on_connection_changed
    )

    manager.error_occurred.connect(
        on_error
    )

    # 1. COM 포트 검색
    print("=== 사용 가능한 COM 포트 ===")

    ports = manager.find_ports()

    for port in ports:
        print(port)


    if len(ports) == 0:
        print("연결 가능한 Serial 장치가 없습니다.")
        return


    # 테스트할 포트 선택
    port = ports[0]["port"]


    # 2. 연결 테스트
    print("\n=== 연결 테스트 ===")
    result = manager.connect(port)
    print("connect 결과:", result)

    # 2-1. 데이터 송신 테스트
    if result:
        print("\n=== 데이터 전송 테스트 ===")
        send_result = manager.send_data("START")
        print("send_data 결과:", send_result)

    # 3. 상태 확인
    print("\n=== 상태 확인 ===")
    print(
        "연결 상태:",
        manager.is_connected()
    )

    # 4. 연결 해제
    print("\n=== 연결 해제 ===")
    manager.disconnect()
    print(
        "연결 상태:",
        manager.is_connected()
    )


if __name__ == "__main__":
    main()