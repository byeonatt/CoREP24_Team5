"""
각 Measurement / Grip Event / Session 데이터 저장 관리

파일 구조 예시:
Session001/
├─ Session001.csv        # Measurement 요약, 헤더 있음
├─ G0001.csv             # 100 Hz 원본 데이터, 헤더 없음
├─ G0001_events.csv      # 실제 Grip Event 요약, 헤더 있음
├─ G0002.csv
└─ G0002_events.csv
"""

import csv
from pathlib import Path


class CSVManager:

    EVENT_HEADER = [
        "event_id",
        "start_time_s",
        "peak_time_s",
        "end_time_s",
        "duration_s",
        "peak_force_n",
    ]

    SESSION_HEADER = [
        "measurement_id",
        "timestamp",
        "mode",
        "duration_s",
        "event_count",
        "event_peak_min_n",
        "event_peak_avg_n",
        "event_peak_max_n",
        "raw_peak_n"
    ]

    def __init__(self, save_directory: Path):
        self.save_directory = (
            Path(save_directory)
            .expanduser()
            .resolve()
        )

        self.save_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        # Raw measurement CSV
        self.file = None
        self.writer = None
        self.current_filepath = None

        # Grip Event CSV
        self.event_file = None
        self.event_writer = None
        self.current_event_filepath = None

        # Raw CSV flush
        self.row_count = 0
        self.flush_interval = 20

        # Event count
        self.event_row_count = 0

    # =====================================================
    # 저장 경로
    # =====================================================

    def set_save_directory(
        self,
        save_directory: Path
    ):
        """
        앱 실행 중 저장 위치 변경 시 CSVManager에도
        새 Session 폴더를 즉시 반영한다.
        """

        if (
            self.file is not None
            or self.event_file is not None
        ):
            raise RuntimeError(
                "측정 중에는 저장 경로를 변경할 수 없습니다."
            )

        self.save_directory = (
            Path(save_directory)
            .expanduser()
            .resolve()
        )

        self.save_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    # =====================================================
    # 파일명
    # =====================================================

    def generate_filename(
        self,
        grip_id: int
    ) -> str:
        """
        기존 프로젝트 호환을 위해 G0001 형식을 유지한다.
        실제 의미는 Measurement #1에 가깝다.
        """
        return f"G{grip_id:04d}.csv"

    def generate_event_filename(
        self,
        grip_id: int
    ) -> str:
        return f"G{grip_id:04d}_events.csv"

    # =====================================================
    # Measurement 시작
    # =====================================================

    def start_measurement(
        self,
        grip_id: int
    ) -> Path:
        """
        Measurement 시작 시:
        1) G0001.csv 생성 - 헤더 없음
        2) G0001_events.csv 생성 - 헤더 있음

        반환값은 기존 코드 호환을 위해 Raw CSV 경로이다.
        """

        # 이전 파일이 열려 있으면 안전하게 닫음
        self.close()

        raw_filepath = (
            self.save_directory
            / self.generate_filename(grip_id)
        )

        event_filepath = (
            self.save_directory
            / self.generate_event_filename(grip_id)
        )

        if raw_filepath.exists():
            raise FileExistsError(
                f"{raw_filepath.name} already exists."
            )

        if event_filepath.exists():
            raise FileExistsError(
                f"{event_filepath.name} already exists."
            )

        try:
            # Raw CSV
            self.file = raw_filepath.open(
                mode="w",
                newline="",
                encoding="utf-8"
            )
            self.writer = csv.writer(self.file)
            self.current_filepath = raw_filepath
            self.row_count = 0

            # Event CSV
            self.event_file = event_filepath.open(
                mode="w",
                newline="",
                encoding="utf-8"
            )
            self.event_writer = csv.writer(self.event_file)
            self.current_event_filepath = event_filepath
            self.event_row_count = 0

            # Event 파일은 사람이 읽는 요약 파일이므로 헤더 작성
            self.event_writer.writerow(self.EVENT_HEADER)
            self.event_file.flush()

        except Exception:
            self.close()
            raise

        return raw_filepath

    # =====================================================
    # Raw Measurement 저장
    # =====================================================

    def append_measurement(
        self,
        elapsed_time: float,
        mode: str,
        data
    ) -> None:
        """
        G0001.csv에 100 Hz 원본 데이터를 저장한다.
        헤더 없음.
        """

        if self.writer is None:
            raise RuntimeError(
                "Raw CSV 파일이 열려 있지 않습니다."
            )

        self.writer.writerow([
            f"{elapsed_time:.3f}",
            mode,
            data.raw_lc1,
            data.raw_lc2,
            data.raw_lc3,
            f"{data.force_lc1:.6f}",
            f"{data.force_lc2:.6f}",
            f"{data.force_lc3:.6f}",
            f"{data.total_force:.6f}",
            f"0x{data.status:02X}",
        ])

        self.row_count += 1

        if (
            self.row_count
            % self.flush_interval
            == 0
        ):
            self.file.flush()

    # =====================================================
    # Grip Event 저장
    # =====================================================

    def append_grip_event(
        self,
        event_id: int,
        start_time_s: float,
        peak_time_s: float,
        end_time_s: float,
        duration_s: float,
        peak_force_n: float
    ) -> None:
        """
        실제 파지 이벤트 하나가 확정될 때마다
        G0001_events.csv에 한 행씩 즉시 기록한다.
        """

        if self.event_writer is None:
            raise RuntimeError(
                "Grip Event CSV 파일이 열려 있지 않습니다."
            )

        self.event_writer.writerow([
            event_id,
            f"{start_time_s:.3f}",
            f"{peak_time_s:.3f}",
            f"{end_time_s:.3f}",
            f"{duration_s:.3f}",
            f"{peak_force_n:.6f}",
        ])

        self.event_row_count += 1

        # 이벤트는 수가 적고, 중간 종료 시 데이터 손실을 줄이기 위해 즉시 flush
        self.event_file.flush()

    # =====================================================
    # Measurement 종료
    # =====================================================

    def close(self):
        """Raw CSV와 Event CSV를 모두 안전하게 닫는다."""

        if self.file is not None:
            try:
                self.file.flush()
                self.file.close()
            finally:
                self.file = None
                self.writer = None
                self.current_filepath = None
                self.row_count = 0

        if self.event_file is not None:
            try:
                self.event_file.flush()
                self.event_file.close()
            finally:
                self.event_file = None
                self.event_writer = None
                self.current_event_filepath = None
                self.event_row_count = 0

    # =====================================================
    # Session 요약
    # =====================================================

    def create_session_csv(self) -> Path:
        """
        Session001/Session001.csv 생성.
        최초 생성 시 헤더를 한 번 작성한다.
        """

        session_name = self.save_directory.name
        filepath = (
            self.save_directory
            / f"{session_name}.csv"
        )

        if (
            not filepath.exists()
            or filepath.stat().st_size == 0
        ):
            with filepath.open(
                mode="w",
                newline="",
                encoding="utf-8"
            ) as file:
                writer = csv.writer(file)
                writer.writerow(self.SESSION_HEADER)

        return filepath

    def append_session_result(
        self,
        grip_id,
        timestamp,
        mode,
        max_force: float,
        duration: float,
        event_count: int = 0,
        event_peak_min: float | None = None,
        event_peak_avg: float | None = None,
        event_peak_max: float | None = None
    ):
        """
        Measurement 하나가 종료될 때 Session 요약에 한 행 추가.

        기존 measurement.py 호출과 호환되도록
        grip_id / max_force / duration 인자는 유지한다.
        추후 GripEventDetector를 연결하면 event_* 값도 함께 전달한다.
        """

        filepath = self.create_session_csv()

        def format_optional(value):
            if value is None:
                return ""
            return f"{value:.3f}"

        with filepath.open(
            mode="a",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                grip_id,
                timestamp,
                mode,
                f"{duration:.3f}",
                event_count,
                format_optional(event_peak_min),
                format_optional(event_peak_avg),
                format_optional(event_peak_max),
                f"{max_force:.3f}"
            ])
