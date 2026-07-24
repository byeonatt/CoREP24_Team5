# CoREP24_Team5
CoREP24기 생산품질5팀 초소형 그리퍼 파지력 측정기

< 폴더 구성 >

GripForceMeasurement/
│
├── firmware/                  # STM32 프로젝트
│   ├── Core/
│   ├── Drivers/
│   ├── Middlewares/
│   ├── USB_DEVICE/
│   ├── .ioc
│   └── README.md
│
├── pc_app/                    # PySide6 프로그램
│   ├── main.py
│   ├── app.py
│   │
│   ├── ui/                    # UI 파일
│   │   ├── main_window.ui
│   │   ├── calibration.ui
│   │   └── icons/
│   │
│   ├── windows/               # 각 창(Window)
│   │   ├── main_window.py
│   │   ├── calibration_window.py
│   │   └── settings_window.py
│   │
│   ├── widgets/               # 사용자 정의 위젯
│   │   ├── force_display.py
│   │   └── status_indicator.py
│   │
│   ├── communication/         # STM32 통신
│   │   ├── serial_manager.py
│   │   └── protocol.py
│   │
│   ├── measurement/           # 측정 관련 로직
│   │   ├── measurement.py
│   │   ├── calibration.py
│   │   └── session.py
│   │
│   ├── utils/
│   │   ├── csv_manager.py
│   │   ├── logger.py
│   │   └── config.py
│   │
│   ├── resources/
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
├── docs/
│   ├── UI/
│   ├── Images/
│   ├── Manual/
│   └── Report/
│
├── test/
│   ├── stm32/
│   └── python/
│
├── README.md
├── LICENSE
└── .gitignore