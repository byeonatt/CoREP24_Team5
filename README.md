# Grip Force Measurement System

STM32와 PySide6를 이용한 산업용 미세 파지력 측정 시스템

[ 로드셀 -- ADC -- STM32 ] -- miniB -- USB A -- [ PC ]

## Project Structure

```text
GripForceMeasurement/
│
├── firmware/                  # STM32 프로젝트
│   ├── Core/
│   ├── Drivers/
│   ├── Middlewares/
│   ├── USB_DEVICE/
│   ├── GripForceMeasurement.ioc
│   └── README.md
│
├── pc_app/                    # PySide6 프로그램
│   ├── main.py
│   ├── app.py
│   │
│   ├── ui/                    # Qt Designer(.ui) 파일
│   │   ├── main_window.ui
│   │   ├── calibration.ui
│   │   └── icons/
│   │
│   ├── windows/               # 각 화면(Window)
│   │   ├── main_window.py
│   │   ├── calibration_window.py
│   │   └── settings_window.py
│   │
│   ├── widgets/               # 사용자 정의 위젯
│   │   ├── force_display.py
│   │   └── status_indicator.py
│   │
│   ├── communication/         # STM32 USB 통신
│   │   ├── serial_manager.py
│   │   └── protocol.py
│   │
│   ├── measurement/           # 측정 및 캘리브레이션
│   │   ├── measurement.py
│   │   ├── calibration.py
│   │   └── session.py
│   │
│   ├── utils/                 # 공통 기능
│   │   ├── csv_manager.py
│   │   ├── logger.py
│   │   └── config.py
│   │
│   ├── resources/             # 아이콘, 이미지, 폰트
│   │   ├── icons/
│   │   ├── images/
│   │   └── fonts/
│   │
│   └── requirements.txt
│
├── data/                      # 측정 데이터
│   ├── csv/
│   ├── backup/
│   └── temp/
│
├── docs/                      # 문서
│   ├── UI/
│   ├── Images/
│   ├── Manual/
│   └── Report/
│
├── test/                      # 테스트 코드
│   ├── stm32/
│   └── python/
│
├── README.md
├── LICENSE
└── .gitignore
```
