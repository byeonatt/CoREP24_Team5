# GripForceMeasurement Development Checklist

> 최종 목표 : STM32 기반 파지력 측정기 + PC 제어 프로그램 개발
> - STM32 인베디드 프로그래밍 -> firmware 폴더(개발언어 : C++)
> - PC용 제어 어플리케이션 프로그래밍 -> pc_app 폴더(개발언어 : Python)
> 
> 개발 원칙
> - 기능 하나를 구현한 후 반드시 테스트한다.
> - 테스트가 완료되면 체크박스를 완료(`- [x]`)한다.
> - 모든 기능은 Firmware → PC → 통합 테스트 순으로 진행한다.
>
> 코드를 수정하여 체크박스 사이를 x로 수정하면 체크 가능!

---

# Phase 1. STM32 기본 측정 기능
- 목표 : 로드셀에서 측정한 값을 실시간으로 PC로 전송시켜 띄울 수 있다.

## 1. ADS1256 드라이버

- [ ] ADS1256 초기화
- [ ] SPI 통신 구현
- [ ] ADC Raw Data 읽기
- [ ] 데이터 정상 수신 확인

---

## 2. Load Cell 데이터 처리

- [ ] ADC Raw Data → Force 계산 구조 작성
- [ ] 3개 로드셀 데이터 읽기
- [ ] 데이터 정상 출력 확인

---

## 3. USB 통신 (Firmware)

- [ ] USB CDC 초기화
- [ ] PC 연결 상태 확인
- [ ] 측정 데이터 송신
- [ ] 명령 수신(Start / Stop / Zero)

---

## ✅ Phase 1 완료 조건

- [ ] STM32에서 측정값을 PC로 실시간 전송 가능

---

# Phase 2. PC USB 통신
- 목표 : PC에서 내린 명령을 STM32로 전송해 동작시킬 수 있다.

## 1. USB 연결

- [ ] COM Port 검색
- [ ] COM Port 선택
- [ ] 연결
- [ ] 연결 해제
- [ ] 자동 재연결

---

## 2. 데이터 수신

- [ ] USB 데이터 수신
- [ ] 패킷 파싱
- [ ] Force 값 표시

---

## 3. 명령 전송

- [ ] START
- [ ] STOP
- [ ] ZERO
- [ ] 기타 명령

---

## ✅ Phase 2 완료 조건

- [ ] STM32 ↔ PC 양방향 통신 가능

---

# Phase 3. 측정 알고리즘 (Firmware)
- 목표 : 로드셀에서 측정한 값을 *안정적으로* N(뉴턴) 단위로 변환할 수 있다.

## 1. 캘리브레이션

### 영점 보정

- [ ] ADC 평균 계산
- [ ] Zero Offset 저장
- [ ] Flash 저장
- [ ] 재부팅 후 유지 확인

### 스팬 보정

- [ ] Scale Factor 계산
- [ ] Flash 저장
- [ ] 재부팅 후 유지 확인

### 온도 보정 (선택)

- [ ] 온도 데이터 수집
- [ ] 보정 상수 적용

---

## 2. 측정 보조 기능

- [ ] 최대 힘 측정(Peak Hold)
- [ ] Auto Zero Tracking : 힘이 측정되지 않은 채 일정 시간이 지나면 자동으로 영점 변환
- [ ] Digital Filter
- [ ] 센서 이상 감지 (ADC 이상, 로드셀 이상 등)
- [ ] 과부하 감지(선택) - 과부하 될 만큼의 힘이 아닐 것 같음

---

## ✅ Phase 3 완료 조건

- [ ] 안정적으로 Force(N) 계산 가능

---

# Phase 4. PC 메인 화면
- 목표 : 어플리케이션 기본 틀 개발 및 실행 성공

## 실시간 측정 화면

- [ ] 현재 힘 표시
- [ ] 최대 힘 표시
- [ ] 측정 시간 표시
- [ ] 측정 시작 버튼
- [ ] 측정 종료 버튼
- [ ] Zero 버튼

---

## 상태 표시

- [ ] 연결 상태
- [ ] 측정 상태
- [ ] 오류 메시지
- [ ] 로그 출력

---

## 메뉴

- [ ] 측정
- [ ] 설정
- [ ] 데이터
- [ ] 도움말

---

## ✅ Phase 4 완료 조건

- [ ] 기본 측정 프로그램 동작

---

# Phase 5. 데이터 관리
- 목표 : 측정 데이터 저장 가능

## CSV 저장

- [ ] 자동 파일명 생성
- [ ] CSV 자동 저장
- [ ] Session 관리
- [ ] Session.csv 갱신
- [ ] 저장 폴더 관리
- [ ] 파일 덮어쓰기 방지

---

## 출력

- [ ] Output 폴더 생성
- [ ] CSV Export

---

## ✅ Phase 5 완료 조건

- [ ] 측정 종료 후 자동 저장

---

# Phase 6. 설정 화면
- 목표 : 어플리케이션 내에서 프로그램의 설정과 상수 변경 가능

## 캘리브레이션

- [ ] Zero Calibration
- [ ] Span Calibration
- [ ] Calibration 저장

---

## 환경 설정

- [ ] User
- [ ] COM Port
- [ ] 저장 위치
- [ ] 기타 설정

---

## ✅ Phase 6 완료 조건

- [ ] 모든 설정 변경 가능

---

# Phase 7. UI 개선
- 목표 : 편리성, 가독성을 고려하여 UI 개발 및 개선

## UI 리소스

- [ ] 아이콘
- [ ] 폰트
- [ ] 로고
- [ ] 색상 테마

---

## 사용자 편의 기능

- [ ] 알림(Popup)
- [ ] 저장 완료 메시지
- [ ] 오류 메시지
- [ ] Calibration 완료 메시지

---

## ✅ Phase 7 완료 조건

- [ ] UI 완성

---

# Phase 8. 통합 테스트
- 목표 : 안정적으로 장치 동작

## 기능 테스트

- [ ] USB 연결/해제
- [ ] 자동 재연결
- [ ] 캘리브레이션
- [ ] CSV 저장
- [ ] Session 관리
- [ ] Peak Hold
- [ ] Auto Zero Tracking
- [ ] Filter

---

## 장시간 테스트

- [ ] 30분 연속 측정
- [ ] USB 안정성 확인
- [ ] 메모리 누수 확인
- [ ] 저장 오류 확인

---

## 최종 검증

- [ ] 전체 기능 테스트
- [ ] 코드 정리
- [ ] README 업데이트
- [ ] Release Version 생성

---

# Progress

## Firmware

- [ ] ADS1256
- [ ] Load Cell
- [ ] USB
- [ ] Calibration
- [ ] Measurement Algorithm

---

## PC Application

- [ ] USB
- [ ] Main UI
- [ ] Data Management
- [ ] Settings
- [ ] UI Resources

---

## Overall Progress

- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5
- [ ] Phase 6
- [ ] Phase 7
- [ ] Phase 8

---

**Last Update : 2026-07-27**
