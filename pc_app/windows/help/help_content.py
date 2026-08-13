"""Offline help text shown in the HelpWindow QTextBrowser widgets.

The content is intentionally stored in Python instead of external HTML files so
PyInstaller packaging only needs to include help.ui as an additional data file.
Edit the constants in this module when the operating procedure changes.
"""

from __future__ import annotations

APP_NAME = "Grip Force Measurement System"
APP_VERSION = "1.0.0"


_COMMON_STYLE = """
<style type="text/css">
    body {
        font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
        font-size: 10.5pt;
        color: #202124;
        line-height: 1.55;
        margin: 18px 22px 28px 22px;
    }
    h1 {
        color: #1f2937;
        font-size: 18pt;
        margin: 0 0 5px 0;
    }
    h2 {
        color: #244d73;
        font-size: 13.5pt;
        margin: 24px 0 8px 0;
        padding: 0 0 6px 0;
        border-bottom: 1px solid #d9dde3;
    }
    h3 {
        color: #34495e;
        font-size: 11.5pt;
        margin: 18px 0 6px 0;
    }
    p {
        margin: 6px 0 10px 0;
    }
    ol, ul {
        margin-top: 5px;
        margin-bottom: 12px;
    }
    li {
        margin-bottom: 5px;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 9px 0 16px 0;
    }
    th {
        background-color: #eef3f8;
        color: #243b53;
        border: 1px solid #cfd5dc;
        padding: 7px 9px;
        text-align: left;
        font-weight: 600;
    }
    td {
        border: 1px solid #d9dde3;
        padding: 7px 9px;
        vertical-align: top;
    }
    code {
        font-family: Consolas, 'Courier New', monospace;
        background-color: #f1f3f5;
        color: #222222;
        padding: 1px 4px;
    }
    pre {
        font-family: Consolas, 'Courier New', monospace;
        background-color: #f5f7f9;
        border: 1px solid #d9dde3;
        padding: 10px 12px;
        white-space: pre-wrap;
    }
    .lead {
        color: #5f6368;
        margin-bottom: 16px;
    }
    .flow {
        background-color: #f7f9fc;
        border: 1px solid #cfd8e3;
        padding: 12px 14px;
        text-align: center;
        font-weight: 600;
        color: #26384a;
    }
    .note {
        background-color: #eef6ff;
        border: 1px solid #b9d5f2;
        padding: 10px 12px;
        margin: 10px 0 14px 0;
    }
    .warning {
        background-color: #fff7e8;
        border: 1px solid #e7c786;
        padding: 10px 12px;
        margin: 10px 0 14px 0;
    }
    .danger {
        background-color: #fff1f1;
        border: 1px solid #e2aaaa;
        padding: 10px 12px;
        margin: 10px 0 14px 0;
    }
    .small {
        color: #626b75;
        font-size: 9.5pt;
    }
</style>
"""


def _document(title: str, lead: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{_COMMON_STYLE}
</head>
<body>
<h1>{title}</h1>
<p class="lead">{lead}</p>
{body}
</body>
</html>
"""


COMMUNICATION_HTML = _document(
    "통신",
    "PC 앱과 장치를 연결하고, 통신 상태를 확인하는 방법입니다.",
    """
<div class="flow">USB 연결 &rarr; COM 포트 선택 &rarr; 115200 bps 확인 &rarr; 연결 &rarr; READY 확인 &rarr; STATUS 확인</div>

<h2>1. 장치 연결</h2>
<ol>
    <li>측정기의 USB 케이블을 PC에 연결합니다.</li>
    <li>메인 화면의 <b>연결 설정</b> 또는 <b>설정(S) &gt; 통신 연결 설정</b>을 선택합니다.</li>
    <li><b>USB to UART</b>가 표시된 COM 포트를 선택합니다.</li>
    <li>ESP32 펌웨어와 동일한 통신 속도를 선택합니다. 현재 프로젝트의 기본 설계값은 <b>115200 bps</b>입니다.</li>
    <li><b>연결</b> 버튼을 누릅니다.</li>
    <li>메인 화면의 장비 연결 상태와 통신 진단 항목을 확인합니다.</li>
</ol>

<h2>2. 정상 연결 확인</h2>
<table>
    <tr><th>표시 항목</th><th>정상 상태</th><th>의미</th></tr>
    <tr><td>장비 연결 상태</td><td>장비 연결됨</td><td>Serial 포트 연결과 ESP32 장치 확인이 완료된 상태</td></tr>
    <tr><td>PC &harr; ESP32</td><td>정상</td><td>Force 패킷이 계속 수신되는 상태</td></tr>
    <tr><td>Handshake</td><td>READY 확인</td><td>ESP32가 <code>READY,ESP32</code>로 응답한 상태</td></tr>
    <tr><td>ADS1256 STATUS</td><td>0x36 정상 또는 0x37 정상</td><td>현재 PC 앱이 정상으로 인정하는 ADC STATUS 값</td></tr>
</table>

<h2>3. 통신 동작</h2>
<p>Serial 연결 직후 PC 앱은 ESP32에 다음 장치 확인 명령을 보냅니다.</p>
<pre>PC &rarr; CMD,START
ESP32 &rarr; READY,ESP32</pre>
<p>장치가 준비되면 ESP32는 다음 형식의 Force 패킷을 지속적으로 전송합니다.</p>
<pre>F,RAW_LC1,RAW_LC2,RAW_LC3,F_LC1,F_LC2,F_LC3,STATUS</pre>

<div class="note"><b>측정 시작 버튼의 의미</b><br>
ESP32는 측정 시작 전에도 실시간 데이터를 전송합니다. <b>측정 시작</b>은 통신을 시작하는 버튼이 아니라 CSV 기록, 그래프 기록, 최대값 계산, Grip Event 검출 및 OK/NG 판정을 시작하는 버튼입니다.</div>

<h2>4. 연결 문제 해결</h2>

<h3>장치가 찾아지지 않을 경우</h3>
<ol>
    <li>Windows 검색에서 <b>장치 관리자</b>를 실행합니다.</li>
    <li><b>기타 장치</b> 또는 <b>범용 직렬 버스 컨트롤러</b> 항목을 펼칩니다.</li>
    <li><b>USB to UART</b> 관련 장치가 존재하는지 확인합니다.</li>
</ol>
<table>
    <tr><th>확인 결과</th><th>조치 방법</th></tr>
    <tr><td>USB to UART 장치가 존재함</td><td>해당 장치에 맞는 <b>USB to UART 드라이버</b>를 설치합니다. CP210x 계열을 사용하는 경우 CP210x Windows 드라이버를 적용합니다.</td></tr>
    <tr><td>USB to UART 장치가 존재하지 않음</td><td>USB 케이블, USB 포트, 측정기 전원 및 커넥터 등 <b>물리적 연결 상태를 다시 확인</b>합니다.</td></tr>
</table>

<div class="note"><b>드라이버 설치 후</b><br>
장치 관리자의 <b>포트(COM &amp; LPT)</b> 항목에 USB Serial 장치와 COM 포트 번호가 표시되는지 확인한 뒤, PC 앱에서 해당 COM 포트를 선택합니다.</div>

<h3>증상별 확인 사항</h3>
<table>
    <tr><th>증상</th><th>확인 사항</th></tr>
    <tr><td>연결 가능한 COM 포트 없음</td><td>USB 데이터 케이블, 측정기 전원, Windows 장치 관리자를 확인합니다.</td></tr>
    <tr><td>USB 장치는 보이지만 COM 포트 없음</td><td>USB Serial 드라이버와 ESP32 USB CDC/Serial 설정을 확인합니다.</td></tr>
    <tr><td>Serial 연결됨 이후 장치 응답 없음</td><td>올바른 COM 포트와 통신 속도인지 확인하고 ESP32를 재부팅합니다.</td></tr>
    <tr><td>Handshake 실패</td><td>다른 프로그램이 해당 포트를 점유하고 있지 않은지 확인한 뒤 다시 연결합니다.</td></tr>
    <tr><td>ADS1256 STATUS 비정상</td><td>ADC 전원, SPI 배선, DRDY 및 센서 연결을 점검합니다.</td></tr>
    <tr><td>측정 중 데이터 수신 끊김</td><td>현재 측정은 통신 오류로 중단됩니다. 연결 상태를 복구한 뒤 새 측정을 시작합니다.</td></tr>
</table>

<div class="warning"><b>주의</b><br>
통신 속도가 ESP32 펌웨어 설정과 다르면 Serial 포트가 열려도 정상 패킷을 받을 수 없습니다.</div>
""",
)


MEASUREMENT_HTML = _document(
    "측정",
    "모드를 선택하고 영점을 확인한 뒤, 파지력을 기록하고 Grip Event를 판정하는 절차입니다.",
    """
<div class="flow">통신 연결 &rarr; 모드 설정 &rarr; 영점 설정 &rarr; 판정 기준 확인 &rarr; 측정 시작 &rarr; 파지/해제 &rarr; 측정 종료</div>

<div class="warning"><b>순서 중요</b><br>
현재 앱은 선택된 측정 모드에 따라 영점 확인 대상 로드셀을 결정합니다. 따라서 <b>모드 설정을 먼저 하고 영점 설정을 수행</b>하십시오.</div>

<h2>1. 측정 전 준비</h2>
<ul>
    <li>장비 연결 상태와 PC &harr; ESP32 상태가 정상인지 확인합니다.</li>
    <li>ADS1256 STATUS가 <code>0x36</code> 또는 <code>0x37</code>인지 확인합니다.</li>
    <li>측정 모드와 실제 장착된 그리퍼/지그가 일치하는지 확인합니다.</li>
    <li>로드셀에 외부 하중이 없는 상태에서 값이 안정적으로 표시되는지 확인합니다.</li>
</ul>

<h2>2. 측정 모드 설정</h2>
<p><b>모드 설정</b> 버튼을 누르고 실제 그리퍼와 지그에 맞는 모드를 선택합니다.</p>
<table>
    <tr><th>화면 표시</th><th>내부 모드</th><th>영점 확인 대상</th></tr>
    <tr><td>외경</td><td><code>MODE_OD</code></td><td>LC1, LC2</td></tr>
    <tr><td>내경 2-Jaw</td><td><code>MODE_ID_2</code></td><td>LC1, LC2</td></tr>
    <tr><td>내경 3-Jaw</td><td><code>MODE_ID_3</code></td><td>LC1, LC2, LC3</td></tr>
</table>
<p>지그나 측정 모드를 변경한 경우 영점을 다시 설정하는 것을 권장합니다.</p>

<h2>3. 영점 설정</h2>
<ol>
    <li>그리퍼 또는 지그가 로드셀을 누르거나 당기지 않는지 확인합니다.</li>
    <li>장비와 케이블이 흔들리지 않도록 고정합니다.</li>
    <li><b>영점 설정</b> 버튼을 누릅니다.</li>
    <li>무하중 상태 확인 메시지에서 <b>예</b>를 선택합니다.</li>
    <li>영점 확인 결과가 표시될 때까지 장비를 건드리지 않습니다.</li>
</ol>
<p>현재 앱은 영점 명령 후 초기 5개 프레임을 제외하고, 20개 샘플로 활성 로드셀의 평균과 변동폭을 확인합니다.</p>
<table>
    <tr><th>검사 항목</th><th>현재 기준</th></tr>
    <tr><td>평균값 허용 범위</td><td>&plusmn;0.05 N</td></tr>
    <tr><td>샘플 최대값 - 최소값</td><td>0.03 N 이하</td></tr>
    <tr><td>확인 샘플 수</td><td>20개</td></tr>
</table>
<p>영점이 불안정하면 접촉 하중, 케이블 장력, 진동, 센서 안정화 상태를 확인한 뒤 다시 수행합니다.</p>

<h2>4. 판정 기준 설정</h2>
<p><b>설정(S) &gt; 판정 기준 설정</b>에서 모드별 최소 및 최대 파지력을 지정할 수 있습니다.</p>
<div class="flow">최소 파지력 &le; 검출된 Grip Peak &le; 최대 파지력 &rarr; OK<br>범위를 벗어난 경우 &rarr; NG</div>
<p>판정 범위는 새 측정을 시작하는 순간의 값으로 고정되며, 측정 중에는 변경할 수 없습니다. 판정 미적용을 선택해도 실시간 파지력과 Grip Event 데이터는 계속 기록됩니다.</p>

<h2>5. 측정 시작과 화면 확인</h2>
<ol>
    <li>통신, 모드, 영점 및 판정 기준을 확인합니다.</li>
    <li><b>측정 시작</b> 버튼을 누릅니다.</li>
    <li>그리퍼를 정상 동작시켜 파지와 해제를 수행합니다.</li>
    <li>현재 파지력, 최대 파지력, Jaw별 값, 합계와 판정 결과를 확인합니다.</li>
</ol>
<table>
    <tr><th>항목</th><th>의미</th></tr>
    <tr><td>현재 파지력</td><td>가장 최근 수신한 세 로드셀 힘의 합</td></tr>
    <tr><td>최대 파지력</td><td>현재 Measurement에서 기록된 전체 최대값</td></tr>
    <tr><td>측정 시간</td><td>측정 시작 이후 경과 시간</td></tr>
    <tr><td>샘플링 속도</td><td>실제 수신 Force 패킷 수로 계산한 속도</td></tr>
    <tr><td>검출 Grip</td><td>유효 조건을 만족하여 확정된 Grip Event 수</td></tr>
    <tr><td>파지력 상태</td><td>가장 최근에 확정된 Grip Event의 OK/NG 또는 감지 결과</td></tr>
    <tr><td>Jaw 1~3</td><td>각 로드셀에서 N으로 변환된 힘</td></tr>
    <tr><td>합계</td><td>LC1 + LC2 + LC3</td></tr>
</table>
<p class="small">메인 화면의 시리얼 모니터는 화면 성능을 위해 최근 200개 행만 유지합니다. 전체 측정 데이터는 CSV에 계속 저장됩니다.</p>

<h2>6. Grip Event 확정과 판정 시점</h2>
<p>OK/NG는 최고점에 도달한 즉시 확정되지 않습니다. 힘이 낮아진 상태가 유지되어 하나의 파지 동작이 종료되었다고 판단한 뒤 결과가 표시됩니다.</p>
<div class="flow">파지력 상승 &rarr; Peak 기록 &rarr; 그리퍼 해제 &rarr; 낮은 힘 유지 확인 &rarr; Grip Event 확정 &rarr; OK/NG 표시</div>
<table>
    <tr><th>현재 고정 기준</th><th>값</th></tr>
    <tr><td>Grip 시작</td><td>0.50 N 이상</td></tr>
    <tr><td>해제 후보</td><td>0.20 N 이하</td></tr>
    <tr><td>해제 유지</td><td>0.20초</td></tr>
    <tr><td>유효 Peak</td><td>1.00 N 이상</td></tr>
    <tr><td>최소 Event 시간</td><td>0.10초</td></tr>
    <tr><td>Event 간 최소 간격</td><td>0.30초</td></tr>
</table>
<div class="note"><b>참고</b><br>
Peak가 1.00 N보다 작은 파지는 현재 설정에서 Grip Event로 집계되지 않습니다. 측정 대상 범위가 이보다 작다면 출시 전 검출 기준을 조정해야 합니다.</div>

<h2>7. 측정 종료</h2>
<p><b>측정 종료</b> 버튼을 누르면 원본 CSV와 Grip Event CSV를 닫고 Session 요약을 저장합니다. 다음 조건에서도 자동 종료됩니다.</p>
<ul>
    <li>측정 시간이 60분에 도달한 경우</li>
    <li>최근 5분간 전체 파지력 변화폭이 0.25 N 이하인 경우</li>
</ul>

<div class="danger"><b>측정 시 주의사항</b><br>
로드셀에 충격 하중을 가하지 말고, 모드와 다른 방향으로 힘을 가하지 마십시오. 지그 또는 그리퍼 교체 후에는 영점을 다시 설정하십시오.</div>
""",
)


CALIBRATION_HTML = _document(
    "캘리브레이션",
    "ESP32에 저장된 TARE와 모드별 Force Factor를 조회·수정·검증하는 관리자 기능입니다.",
    """
<div class="warning"><b>관리자 기능</b><br>
현재 캘리브레이션 화면은 표준추를 단계별로 측정해 계수를 자동 계산하는 마법사가 아닙니다. 검증된 상수를 직접 입력해 ESP32에 저장하는 <b>캘리브레이션 상수 관리 화면</b>입니다.</div>

<h2>1. 영점 설정과 캘리브레이션의 차이</h2>
<table>
    <tr><th>구분</th><th>영점 설정</th><th>캘리브레이션</th></tr>
    <tr><td>목적</td><td>현재 무하중 상태를 0 N 부근으로 맞춤</td><td>RAW 값을 N으로 변환하는 기준 상수 관리</td></tr>
    <tr><td>사용 시점</td><td>측정 전, 지그/그리퍼 교체 후</td><td>센서 교체, 재조립, 정밀 재보정 시</td></tr>
    <tr><td>주 사용자</td><td>일반 측정 작업자</td><td>관리자 또는 캘리브레이션 담당자</td></tr>
</table>

<h2>2. 관리되는 값</h2>
<p>LC1, LC2, LC3 각각에 대해 다음 네 값을 관리하며 총 12개 항목이 표시됩니다.</p>
<table>
    <tr><th>항목</th><th>용도</th></tr>
    <tr><td><code>ZERO_TARE_OFFSET</code></td><td>무하중 RAW 기준값</td></tr>
    <tr><td><code>OD_FORCE_FACTOR</code></td><td>외경 모드 RAW&rarr;N 변환 계수</td></tr>
    <tr><td><code>ID2_FORCE_FACTOR</code></td><td>내경 2-Jaw 모드 RAW&rarr;N 변환 계수</td></tr>
    <tr><td><code>ID3_FORCE_FACTOR</code></td><td>내경 3-Jaw 모드 RAW&rarr;N 변환 계수</td></tr>
</table>

<h2>3. 값 조회 및 변경</h2>
<ol>
    <li>ESP32와 통신을 연결합니다.</li>
    <li>진행 중인 측정을 종료합니다.</li>
    <li>메인 화면의 <b>캘리브레이션</b>을 선택합니다.</li>
    <li>ESP32에서 LC1, LC2, LC3 값이 모두 조회될 때까지 기다립니다.</li>
    <li>변경 전 값을 별도로 기록하거나 화면을 캡처합니다.</li>
    <li>검증된 TARE와 Force Factor를 입력합니다.</li>
    <li><b>적용</b>을 누르고 저장값 재조회 및 일치 확인이 끝날 때까지 연결을 유지합니다.</li>
    <li>저장 완료 후 메인 화면으로 돌아가 측정 모드를 선택하고 영점을 다시 설정합니다.</li>
</ol>

<h2>4. 저장 검증 동작</h2>
<p>PC 앱은 입력한 12개 값을 ESP32로 전송한 다음, 일정 시간 후 다시 조회하여 입력값과 저장값이 허용 오차 안에서 일치하는지 검사합니다.</p>
<pre>조회: CMD,CAL_GET
저장: CMD,CAL_SET,TARE1,OD1,ID2_1,ID3_1,...,TARE3,OD3,ID2_3,ID3_3</pre>

<div class="danger"><b>주의사항</b><br>
<ul>
    <li>값의 부호를 임의로 바꾸지 마십시오.</li>
    <li>Force Factor에 0 또는 검증되지 않은 값을 입력하지 마십시오.</li>
    <li>저장 확인 중에는 USB 연결을 해제하거나 ESP32 전원을 끄지 마십시오.</li>
    <li>저장값 불일치 메시지가 나타나면 해당 상태로 측정을 진행하지 마십시오.</li>
    <li>센서 또는 ADC를 교체한 경우 모든 모드를 다시 검증하십시오.</li>
</ul>
</div>

<div class="note"><b>비휘발성 저장</b><br>
재부팅 후에도 값이 유지되는지는 ESP32 펌웨어의 NVS 등 비휘발성 저장 구현에 따라 결정됩니다. 최종 배포 전 전원 재인가 후 값 유지 여부를 반드시 확인하십시오.</div>
""",
)


STORAGE_HTML = _document(
    "저장",
    "Measurement 원본 데이터, Grip Event 요약과 Session 요약의 자동 저장 방식입니다.",
    """
<div class="flow">측정 시작 &rarr; G0001.csv 및 G0001_events.csv 생성 &rarr; 실시간 기록 &rarr; 측정 종료 &rarr; Session001.csv 요약 추가</div>

<h2>1. 자동 저장 방식</h2>
<p>현재 앱은 별도의 수동 저장 버튼 없이 자동으로 파일을 관리합니다.</p>
<ul>
    <li><b>측정 시작:</b> 원본 CSV와 Grip Event CSV를 생성하고 기록을 시작합니다.</li>
    <li><b>측정 종료:</b> 두 파일을 닫고 Session 요약 CSV에 Measurement 결과를 추가합니다.</li>
</ul>
<p>측정 시작 순간 파일이 생성되므로, 가능한 경우 <b>측정 종료</b> 버튼으로 정상 종료하십시오.</p>

<h2>2. 기본 저장 위치와 폴더 구조</h2>
<p>저장 위치를 따로 지정하지 않으면 다음 경로를 사용합니다.</p>
<pre>C:\\Users\\&lt;사용자 이름&gt;\\Documents\\GripForceData</pre>
<p>앱 실행 시 Session 폴더가 생성되거나 기존 빈 Session이 사용됩니다.</p>
<pre>GripForceData
├─ Session001
│  ├─ Session001.csv
│  ├─ G0001.csv
│  ├─ G0001_events.csv
│  ├─ G0002.csv
│  └─ G0002_events.csv
├─ Session002
└─ ...</pre>

<h2>3. 파일별 내용</h2>
<table>
    <tr><th>파일</th><th>내용</th><th>헤더</th></tr>
    <tr><td><code>G0001.csv</code></td><td>측정 중 수신한 RAW, Jaw별 N값, 합계, STATUS 원본 데이터</td><td>없음</td></tr>
    <tr><td><code>G0001_events.csv</code></td><td>확정된 각 Grip Event의 시작/Peak/종료 시각, 지속시간, Peak</td><td>있음</td></tr>
    <tr><td><code>Session001.csv</code></td><td>Measurement별 시간, 모드, Event 수, Event Peak 통계와 Raw Peak 요약</td><td>있음</td></tr>
</table>

<h3>G0001.csv 열 순서</h3>
<pre>경과시간, 측정모드, RAW_LC1, RAW_LC2, RAW_LC3,
F_LC1, F_LC2, F_LC3, 전체 파지력, ADS1256 STATUS</pre>

<h3>G0001_events.csv 열</h3>
<pre>event_id, start_time_s, peak_time_s, end_time_s,
duration_s, peak_force_n</pre>

<h3>Session001.csv 열</h3>
<pre>measurement_id, timestamp, mode, duration_s, event_count,
event_peak_min_n, event_peak_avg_n, event_peak_max_n, raw_peak_n</pre>

<div class="warning"><b>현재 버전의 저장 범위</b><br>
화면에서 계산한 개별 Event의 OK/NG 결과, 적용한 최소/최대 판정 기준, 누적 OK/NG 수는 현재 CSV에 저장되지 않습니다. 품질 이력에 해당 값이 필요하면 CSV 컬럼을 확장해야 합니다.</div>

<h2>4. 저장 경로 변경</h2>
<ol>
    <li>진행 중인 측정을 종료합니다.</li>
    <li><b>데이터(D) &gt; 저장 경로 지정</b>을 선택합니다.</li>
    <li>원하는 기본 폴더를 선택합니다.</li>
    <li>완료 메시지에 표시된 새 Session 경로를 확인합니다.</li>
</ol>
<p>측정 중에는 저장 경로를 변경할 수 없습니다.</p>

<h2>5. 데이터 확인</h2>
<ol>
    <li>메인 화면의 <b>데이터</b> 또는 <b>데이터(D) &gt; 데이터 관리</b>를 선택합니다.</li>
    <li>Session과 측정 파일을 선택합니다.</li>
    <li>측정 시간, 샘플 수, Peak, 샘플링 속도와 STATUS를 확인합니다.</li>
    <li>LC1, LC2, LC3 및 전체 파지력 그래프를 확인합니다.</li>
    <li>필요하면 <b>선택 CSV 열기</b> 또는 <b>폴더 열기</b>를 사용합니다.</li>
</ol>

<div class="note"><b>데이터 보존 권장사항</b><br>
원본 CSV는 직접 수정하지 말고 복사본을 만들어 분석하십시오. 중요한 검사 데이터는 회사의 백업 정책에 따라 별도 저장소에 주기적으로 백업하십시오.</div>
""",
)


ABOUT_TEXT = (
    f"{APP_NAME}\n"
    f"버전 {APP_VERSION}\n\n"
    "인서트 전용 미세 파지력 측정 및 기록 프로그램\n"
    "통신 · 측정 · 캘리브레이션 · 데이터 저장"
)
