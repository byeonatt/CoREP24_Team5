# Grip Force Measurement System

STM32와 PySide6를 이용한 산업용 미세 파지력 측정 시스템

[ 로드셀 -- ADC -- STM32 ] -- miniB -- USB A -- [ PC ]

프로그래밍 방법 :
이하 Project Structure를 AI에 먹이고,
생성해주길 바라는 파일 이름 코딩해달라고 하기

## Project Structure

```text
GripForceMeasurement/
│
├── firmware/                          # STM32 펌웨어 (C++)
│   ├── Core/                          ### 직접 개발하는 부분
│   │   ├── Inc/
│   │   │   ├── loadcell.h
│   │   │   ├── calibration.h
│   │   │   ├── measurement.h          # 측정 알고리즘
│   │   │   ├── usb_protocol.h         # USB 통신
│   │   │   ├── measurement_types.h    # 공통 구조체
│   │   │   └── measurement_config.h   # 상수와 설정값
│   │   │
│   │   └── Src/
│   │       ├── main.cpp
│   │       ├── loadcell.cpp
│   │       ├── calibration.cpp
│   │       ├── measurement.cpp
│   │       └── usb_protocol.cpp
│   │ 
│   │ # 이하 STM32 연결 시 자동 생성
│   ├── Drivers/
│   ├── Middlewares/
│   ├── USB_DEVICE/
│   ├── GripForceMeasurement.ioc
│   └── README.md
│
├── pc_app/                            # PC 제어 프로그램 (Python + PySide6)
│   ├── main.py
│   ├── app.py
│   │
│   ├── windows/
│   │   ├── main/
│   │   │   ├── main_window.py
│   │   │   └── main_window.ui
│   │   │
│   │   ├── calibration/
│   │   │   ├── calibration_window.py
│   │   │   └── calibration.ui
│   │   │
│   │   └── settings/
│   │       ├── settings_window.py
│   │       └── settings.ui
│   │
│   ├── widgets/                       # 사용자 정의 위젯
│   │   ├── force_display.py
│   │   └── status_indicator.py
│   │
│   ├── communication/                 # STM32 USB 통신
│   │   ├── serial_manager.py
│   │   └── protocol.py
│   │
│   ├── data/                          # 데이터 관리
│   │   ├── csv_manager.py
│   │   ├── session_manager.py
│   │   └── file_manager.py
│   │
│   ├── utils/                         # 공통 기능
│   │   ├── logger.py
│   │   └── config.py
│   │
│   ├── resources/                     # 아이콘, 이미지, 폰트
│   │   ├── icons/
│   │   ├── images/
│   │   └── fonts/
│   │
│   └── requirements.txt
│
├── data/                              # 측정 데이터
│   ├── csv/
│   ├── backup/
│   └── temp/
│
├── docs/                              # 프로젝트 문서
│   ├── UI/
│   ├── Images/
│   ├── Manual/
│   ├── Report/
│   ├── Development_Checklist.md
│   ├── Protocol.md
│   ├── CSV_Format.md
│   └── Hardware.md
│
├── test/                              # 테스트 코드
│   ├── stm32/
│   └── python/
│
├── README.md
├── LICENSE
└── .gitignore
```