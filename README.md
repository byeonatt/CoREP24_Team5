# Grip Force Measurement System

ESP32-S3, ADS1256, 3개의 로드셀과 PySide6 기반 PC App을 이용한 **인서트 그리퍼 미세 파지력 측정 시스템**입니다.

그리퍼를 실제 설비에 조립하기 전에 파지력을 측정하고, 측정 결과를 저장하여 사전 검사 및 품질 이력 관리에 활용하는 것을 목표로 합니다.

```text
[ Load Cell 1 / 2 / 3 ]
          │
          ▼
      [ ADS1256 ]
          │ SPI
          ▼
      [ ESP32-S3 ]
          │ USB Serial (115200 baud)
          ▼
        [ PC ]
   Python + PySide6
```

---

## 1. 주요 기능

### 측정

- 외경 2-Jaw 측정
- 내경 2-Jaw 측정
- 내경 3-Jaw 측정
- LC1 / LC2 / LC3 RAW 값 실시간 표시
- LC1 / LC2 / LC3 변환 힘(N) 표시
- ESP32에서 계산된 최종 파지력 `TOTAL` 표시
- 현재 파지력 / 최대 파지력 / 평균 파지력 표시
- 실시간 파지력 그래프 표시
- 측정 시간 및 수신 속도 표시

### 통신 상태 확인

- Serial 연결 상태 확인
- ESP32 `READY` 핸드셰이크 확인
- ADS1256 `STATUS` 값 표시
- 정상 STATUS 기준: 주로 `0x36 ~ 0x37`
- FORCE 패킷 수신 타임아웃 감지
- 최근 연결 장치 자동 재연결 지원

### 영점 설정

- PC App에서 `CMD,ZERO` 전송
- 무부하 상태의 RAW 값을 새로운 TARE로 설정
- 영점 설정 중 측정 및 기타 조작 방지
- 영점 완료 후 PC App에서 로드셀 값 안정 여부 확인
- 갱신된 TARE 값은 ESP32 NVS에 저장

### 캘리브레이션

- `CMD,CAL_GET`으로 현재 보정값 조회
- `CMD,CAL_SET`으로 TARE / Force Factor 저장
- LC1 / LC2 / LC3별 보정값 관리
- 외경 / 내경 2-Jaw / 내경 3-Jaw 모드별 Force Factor 관리
- 저장 후 재조회하여 적용값 검증

### 데이터 관리

- 측정 데이터를 CSV로 자동 저장
- 세션 단위 파일 관리
- Grip Event 단위 측정 결과 관리
- 과거 측정 데이터 조회
- 판정 기준 설정 및 OK / NG 판정 기능
- 저장 경로 사용자 지정

### 안전 기능

- 최대 측정 시간 초과 시 자동 종료
- 장시간 파지력 변화가 없을 경우 자동 종료
- 통신 끊김 및 FORCE 패킷 미수신 감지
- 프로그램 종료 시 Serial 연결 안전 해제

---

## 2. Hardware

### MCU

- ESP32-S3

### ADC

- ADS1256
- 24-bit ADC
- VREF: 2.5 V

### Load Cell

3개의 로드셀을 사용합니다.

| Load Cell | ADS1256 Differential Channel |
|---|---|
| LC1 | AIN4(+) - AIN5(-) |
| LC2 | AIN2(+) - AIN3(-) |
| LC3 | AIN0(+) - AIN1(-) |

### ESP32-S3 ↔ ADS1256

| Signal | ESP32-S3 GPIO |
|---|---:|
| SCLK | GPIO 12 |
| MISO | GPIO 13 |
| MOSI | GPIO 11 |
| CS | GPIO 10 |
| DRDY | GPIO 4 |

RESET / SYNC는 현재 `PIN_UNUSED` 방식으로 사용합니다.

---

## 3. 측정 모드

PC App에서 다음 세 가지 모드를 선택할 수 있습니다.

| Mode | Command | Description |
|---|---|---|
| 외경 | `CMD,MODE_OD` | 외경 2-Jaw |
| 내경 2-Jaw | `CMD,MODE_ID_2` | 내경 2-Jaw |
| 내경 3-Jaw | `CMD,MODE_ID_3` | 내경 3-Jaw |

모드를 변경하면 ESP32도 동일한 모드로 전환되며, 해당 모드에 저장된 Force Factor를 사용합니다.

---

## 4. Force 계산

각 로드셀의 힘은 ESP32에서 다음 방식으로 계산합니다.

```text
F_LC = (RAW_LC - TARE_OFFSET) × FORCE_FACTOR
```

최종 파지력 `TOTAL` 역시 ESP32에서 계산합니다.

```text
외경 2-Jaw   : TOTAL = F_LC2 × 2
내경 2-Jaw   : TOTAL = F_LC2 × 2
내경 3-Jaw   : TOTAL = F_LC1 + F_LC2 + F_LC3
```

---

## 5. Serial Protocol

통신 속도:

```text
115200 baud
```

### PC → ESP32

```text
CMD,START
CMD,ZERO
CMD,MODE_OD
CMD,MODE_ID_2
CMD,MODE_ID_3
CMD,CAL_GET
CMD,CAL_SET,...
```

### ESP32 → PC

#### READY

PC App이 연결 후 다음 명령을 전송합니다.

```text
CMD,START
```

ESP32가 정상적으로 준비되면 다음과 같이 응답합니다.

```text
READY,ESP32
```

PC App은 `READY,ESP32`를 확인한 뒤 장비를 측정 가능한 상태로 전환합니다.

---

### FORCE Packet

현재 측정 패킷 형식:

```text
F,RAW_LC1,RAW_LC2,RAW_LC3,F_LC1,F_LC2,F_LC3,TOTAL,STATUS
```

예:

```text
F,-12345.20,10500.10,-8530.40,0.1234,0.5678,0.9012,1.5924,0x36
```

| Field | Description |
|---|---|
| `RAW_LC1` | LC1 RAW |
| `RAW_LC2` | LC2 RAW |
| `RAW_LC3` | LC3 RAW |
| `F_LC1` | LC1 Force [N] |
| `F_LC2` | LC2 Force [N] |
| `F_LC3` | LC3 Force [N] |
| `TOTAL` | 최종 파지력 [N] |
| `STATUS` | ADS1256 STATUS register |

---

### Calibration

조회:

```text
CMD,CAL_GET
```

저장:

```text
CMD,CAL_SET,
TARE1,OD_F1,ID2_F1,ID3_F1,
TARE2,OD_F2,ID2_F2,ID3_F2,
TARE3,OD_F3,ID2_F3,ID3_F3
```

실제 명령은 개행 없이 한 줄로 전송합니다.

TARE와 Force Factor는 ESP32의 `Preferences`를 이용하여 NVS에 저장되므로 전원을 꺼도 유지됩니다.

---

## 6. PC App

### Technology

- Python
- PySide6
- PySerial
- Qt `.ui`
- CSV 기반 측정 데이터 저장
- PyInstaller 기반 Windows / macOS 배포

---

## 7. PC App Project Structure

현재 개발에서 사용하는 핵심 구조는 다음과 같습니다.

```text
pc_app/
│
├── main.py
│   └── Config / CSVManager / SerialManager 생성
│       → MeasurementWindow 실행
│
├── communication/
│   ├── protocol.py
│   │   ├── Command
│   │   ├── PacketType
│   │   ├── FORCE / READY / CAL 패킷 파싱
│   │   └── PC → ESP32 명령 생성
│   │
│   └── serial_manager.py
│       ├── Serial 연결 / 해제
│       ├── 비동기 연결
│       ├── 포트 검색
│       ├── 데이터 송수신
│       └── Qt Signal 전달
│
├── data_manager/
│   ├── csv_manager.py
│   │   └── 측정 데이터 및 Summary 저장
│   │
│   ├── data_management_window.py
│   │   └── 과거 측정 데이터 조회
│   │
│   └── grip_event_detector.py
│       └── 실제 Grip Event 감지
│
├── utils/
│   ├── config.py
│   │   ├── config.json 관리
│   │   ├── 저장 경로 관리
│   │   ├── 세션 ID 관리
│   │   └── 최근 연결 장치 정보 관리
│   │
│   └── device_change_filter.py
│       └── USB / Serial 장치 변화 감지
│
├── windows/
│   │
│   ├── main/
│   │   ├── measurement.py
│   │   ├── measurement.ui
│   │   ├── connect_dialog.py
│   │   ├── connect_dialog.ui
│   │   └── realtime_force_graph.py
│   │
│   ├── calibration/
│   │   ├── calibration_window.py
│   │   └── calibration.ui
│   │
│   ├── settings/
│   │   ├── settings_dialog.py
│   │   ├── settings_dialog.ui
│   │   ├── judgement_settings_dialog.py
│   │   └── judgement_settings_dialog.ui
│   │
│   └── help/
│       ├── help_window.py
│       └── help_content.py
│
├── resources/
│   └── icon / image 등 프로그램 리소스
│
├── config.json
└── requirements.txt
```


---

## 8. 주요 파일 역할

### `main.py`

프로그램 시작점입니다.

```text
Config
  ↓
CSVManager
  ↓
SerialManager
  ↓
MeasurementWindow
```

각 관리 객체를 생성한 뒤 메인 측정 화면을 실행합니다.

---

### `windows/main/measurement.py`

PC App의 핵심 로직입니다.

주요 기능:

- Serial 연결 상태 처리
- ESP32 `READY` 핸드셰이크
- 측정 모드 변경
- 영점 설정
- 측정 시작 / 종료
- 실시간 파지력 표시
- Peak / Average 계산
- 실시간 그래프 전달
- CSV 저장
- Grip Event 감지
- OK / NG 판정
- FORCE packet timeout 감지
- 자동 측정 종료
- 자동 장치 재연결
- 시리얼 모니터 자동 스크롤 제어
- Calibration / Settings / Help / Data Management 화면 연결

---

### `communication/protocol.py`

ESP32와 PC 사이의 통신 규칙을 담당합니다.

주요 역할:

```text
문자열 수신
   ↓
parse_packet()
   ↓
FORCE / READY / CALIBRATION
   ↓
PC App 내부 데이터 객체
```

PC에서 ESP32로 전송할 명령도 이 파일에서 생성합니다.

---

### `communication/serial_manager.py`

PySerial 기반 실제 Serial 통신을 담당합니다.

주요 Qt Signal:

```text
line_received
connection_changed
error_occurred
```

SerialManager는 UI 로직과 직접 결합하지 않고 Signal을 통해 데이터를 전달합니다.

---

### `data_manager/csv_manager.py`

측정 데이터를 CSV로 저장합니다.

측정 시작 시 파일을 열고 FORCE 패킷이 들어올 때마다 측정 데이터를 기록하며, 측정 종료 시 파일을 닫습니다.

---

### `utils/config.py`

프로그램 설정값을 관리합니다.

예:

- 측정 데이터 저장 경로
- Session ID
- 최근 연결 장치
- VID / PID
- Serial Number
- Port 정보
- 자동 연결에 필요한 설정

---

## 9. PC App 동작 흐름

```text
앱 실행
  │
  ▼
Serial 포트 탐색
  │
  ├─ 이전 장치 존재 → 자동 연결 시도
  │
  └─ 없음 → 연결 설정에서 수동 선택
  │
  ▼
Serial 연결
  │
  ▼
CMD,START
  │
  ▼
READY,ESP32 확인
  │
  ▼
측정 가능 상태
  │
  ├─ MODE 설정
  ├─ ZERO
  └─ Calibration
  │
  ▼
측정 시작
  │
  ├─ FORCE 패킷 수신
  ├─ 실시간 UI 표시
  ├─ 그래프 표시
  ├─ Grip Event 감지
  ├─ CSV 기록
  └─ OK / NG 판정
  │
  ▼
측정 종료
  │
  ▼
파일 저장 / 측정 이력 관리
```

---

## 10. 자동 연결

최근 연결 장치 정보는 Config에 저장됩니다.

장치 검색 우선순위:

```text
1. Serial Number
2. VID + PID
3. 이전 Port
```

USB 장치가 다시 연결되면 PC App이 장치 변화를 감지하고 자동 연결을 시도합니다.

현재 ESP32 Serial 기본 속도는:

```text
115200
```

---

## 11. 측정 화면 주요 상태

메인 화면에서는 다음 정보를 확인할 수 있습니다.

### Connection

- Serial 연결 여부
- Port
- ESP32 장치 상태
- READY Handshake
- ADS1256 STATUS

### Measurement

- 현재 파지력
- 최대 파지력
- 평균 파지력
- 측정 시간
- Sampling / Packet Rate
- 현재 측정 모드
- 측정 진행 상태
- OK / NG 판정

### Load Cell

- LC1 RAW / N
- LC2 RAW / N
- LC3 RAW / N
- TOTAL

---

## 12. Grip Event

연속적으로 수신되는 FORCE 데이터 중 실제 파지 동작을 하나의 Grip Event로 분리합니다.

현재 PC App에서는 다음과 같은 조건을 이용하여 파지 시작 / 해제를 감지합니다.

```text
Start Threshold
Release Threshold
Release Hold Time
Minimum Peak Force
Minimum Event Duration
Minimum Event Gap
```

이를 통해 단순히 모든 FORCE 프레임을 하나의 측정값으로 취급하지 않고, 실제 파지 동작 단위의 결과를 관리할 수 있습니다.

---

## 13. 측정 자동 종료

비정상적으로 측정이 계속 실행되는 상황을 방지하기 위한 안전 기능이 있습니다.

### 최대 시간

```text
60분
```

최대 측정 시간을 초과하면 자동 종료합니다.

### 장시간 무변화

일정 시간 동안 파지력 변화가 설정 범위 이내에 머무르면 측정을 자동 종료합니다.

현재 구현 기준:

```text
감시 시간: 약 5분
```
