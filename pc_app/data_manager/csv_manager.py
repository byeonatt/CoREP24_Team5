'''
각 grip 별 데이터, 각 session 별 데이터 저장 관리
- Grip 데이터(G0001.csv)
- Session 요약(Summary.csv)
'''

import csv
from pathlib import Path


class CSVManager:

    def __init__(self, save_directory: Path):
        self.save_directory = save_directory
        self.save_directory.mkdir(parents=True, exist_ok=True)

        self.file = None
        self.writer = None
        self.current_filepath = None

        self.row_count = 0
        self.flush_interval = 20

    def generate_filename(self, grip_id: int) -> str:
        return f"G{grip_id:04d}.csv"

    def start_measurement(self, grip_id: int) -> Path:

        # 혹시 이전 파일이 열려 있다면 닫기
        self.close()
        filepath = (self.save_directory / self.generate_filename(grip_id))
        if filepath.exists():
            raise FileExistsError(f"{filepath.name} already exists.")
        
        self.file = filepath.open(mode="w", newline="",encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.current_filepath = filepath
        self.row_count = 0

        return filepath
    

    def append_measurement(self, elapsed_time: float, mode: str, data) -> None:
        if self.writer is None:
            raise RuntimeError("CSV 파일이 열려 있지 않습니다.")

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

            f"0x{data.status:02X}"
        ])
        self.row_count += 1

        if (self.row_count % self.flush_interval == 0):
            self.file.flush()


    def close(self):
        if self.file is not None:
            try:
                self.file.flush()
                self.file.close()
            finally:
                self.file = None
                self.writer = None
                self.current_filepath = None
                self.row_count = 0


    def create_session_csv(self) -> Path:
        session_name = self.save_directory.name
        filepath = (self.save_directory / f"{session_name}.csv")
        
        if not filepath.exists():
            filepath.touch()

        return filepath


    def append_session_result(
        self,
        grip_id,
        timestamp,
        mode,
        max_force: float,
        average_force: float,
        duration: float
    ):

        filepath = self.create_session_csv()

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
                f"{max_force:.3f}",
                f"{average_force:.3f}",
                f"{duration:.3f}"
            ])