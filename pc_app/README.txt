[MCU(ESP32) 내장 파일 생성 프롬프트]

장비를 켠 순간부터 매 순간 측정 데이터를 터미널에 전송하는 시스템
로드셀로부터 각각의 RAW 데이터를 받아서 내부에서 각각의 TARE_OFFSET, FORCE_FACTOR 등을 이용해 N(뉴턴) 값으로 변화한 다음 전송한다.

명령어는 'CMD,(명령어)' 형태로 입력된다. (예: CMD,ZERO)

반응하는 명령어 목록
-ZERO -> 영점을 조절한다(TARE_OFFSET을 새로 지정한다).
-MODE_OD -> 외경 모드로 변환한다.
-MODE_ID_2 -> 내경 2-jaw 모드로 변환한다.
-MODE_ID_3 -> 내경 3-jaw 모드로 변환한다.
-CAL_GET -> 현재 ESP32에 저장되어있는 캘리브레이션 상수를 반환한다.
-CAL_SET -> ESP32의 캘리브레이션 상수를 변경한다.

외경 모드 : 외경 모드용 Force Factor와 공통 TARE_OFFSET을 각각 N 단위로 계산한다.
내경 2-jaw 모드 : 내경 2-jaw 모드용 TARE, Force Factor를 각 로드셀의 RAW 값에 적용하여 LC1, LC2, LC3의 힘을 각각 N 단위로 계산한다.
내경 3-jaw 모드 : 내경 3-jaw 모드용 TARE, Force Factor를 각 로드셀의 RAW 값에 적용하여 LC1, LC2, LC3의 힘을 각각 N 단위로 계산한다.



[프로그램 사용 프로세스]

1. 전원이 연결되면 매순간 PC로 로드셀 측정 데이터를 전송한다.
전송되는 데이터: 'F', 각 로드셀(LC)의 raw값, 각 jaw의 뉴턴 변환값
데이터는 'F,RAW_LC1,RAW_LC2,RAW_LC3,F_LC1,F_LC2,F_LC3' 형태로 전송한다.
-Force(N) 계산 : F_LC = (RAW_LC - TARE_OFFSET) × FORCE_FACTOR

2. Serial이 연결 되면 PC로부터 'CMD,START' 메세지를 전달받고, 그 답장으로 'READY,ESP32' 패킷을 PC로 전송한다.

3. 'CMD,ZERO'가 입력되면, 각 로드셀의 TARE_OFFSET을 새로 저장한다.

4. 'CMD,CAL_GET'이 입력되면 현재의 캘리브레이션 상수(TARE_OFFSET, FORCE_FACTOR 등)을 반환한다.
데이터 반환값은 다음과 같이 table 형태이다.
CAL_GET,LC1,TARE1,OD_F1,ID2_F1,ID3_F1
CAL_GET,LC2,TARE2,OD_F2,ID2_F2,ID3_F2
CAL_GET,LC3,TARE3,OD_F3,ID2_F3,ID3_F3

5. 'CMD,CAL_SET'이 입력되면 변수로 입력된 값을 캘리브레이션 상수에 저장한다.
데이터 입력값은 다음과 같이 table 형태이다.
CMD,CAL_SET,
TARE1,OD_F1,ID2_F1,ID3_F1,
TARE2,OD_F2,ID2_F2,ID3_F2,
TARE3,OD_F3,ID2_F3,ID3_F3
이렇게 설정된 캘리브레이션 상수는 전원이 꺼져도 유지된다.



[MCU-PC 간 통신 프로세스]

[통신 연결 설정]
        ↓
COM 포트 검색
        ↓
포트 선택 + Baudrate 선택
        ↓
SerialManager.connect()
        ↓
수신 Thread 시작
        ↓
measurement.py에 연결 성공 전달
        ↓
PC → CMD,START
        ↓
3초 Handshake 대기
        ↓
ESP32 → READY,ESP32
        ↓
device_ready = True
        ↓
측정 가능
        ↓
ESP32 → F,RAW1,RAW2,RAW3,F1,F2,F3,STATUS
        ↓
PC가 지속적으로 수신/파싱



[초기 저장 경로]

C:/Users/User/Documents/GripForceData



[저장 데이터 구성]
G0001.csv
━━━━━━━━━━━━━━━━━━━━
원본 데이터
100 Hz
수십만 행
프로그램 분석 중심
헤더 X


G0001_events.csv
━━━━━━━━━━━━━━━━━━━━
실제 파지 이벤트 요약
약 200행
사람 + 프로그램 모두 사용
헤더 O


Session001.csv
━━━━━━━━━━━━━━━━━━━━
Measurement 단위 결과 요약
몇 행 ~ 수십 행
사람이 직접 확인하기 좋음
헤더 O