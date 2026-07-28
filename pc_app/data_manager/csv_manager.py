'''
각 grip 별 데이터, 각 session 별 데이터 저장 관리
- Grip 데이터(G0001.csv)
- Session 요약(Summary.csv)
'''

import csv
from pathlib import Path

class CSVManager :

    def __init__(self, save_directory: Path):
        self.save_directory = save_directory
        self.save_directory.mkdir(parents=True, exist_ok=True)
    
    # GripID를 토대로 파일명 자동 생성 함수
    def generate_filename(self, grip_id: int) -> str:
        return f"G{grip_id:04d}.csv"
    
    # 파일명을 받아 빈 csv 파일을 생성하는 함수
    def create_csv(self, grip_id: int) -> Path:
        filepath = self.save_directory / self.generate_filename(grip_id)

        if filepath.exists():   # 오류 처리
            raise FileExistsError(f"{filepath.name} already exists.")
        filepath.touch()

        return filepath

    # 측정 결과 하나를 받아 csv 파일에 한 줄 저장
    def append_row(self, filepath, timestamp: float, force: float) -> None:
        with filepath.open(mode="a", newline="", encoding="utf-8") as file:

            writer = csv.writer(file)
            writer.writerow([ f"{timestamp:.3f}", f"{force:.3f}" ])
    
    # 빈 Summary.csv 파일을 생성하는 함수
    def create_summary_csv(self) -> Path:
        filepath = self.save_directory / "Summary.csv"

        if not filepath.exists():
            filepath.touch()

        return filepath
    
    def append_summary(self, grip_id, timestamp, max_force:float, duration:float) -> None:
        filepath = self.create_summary_csv()
        with filepath.open(mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([grip_id, timestamp, f"{max_force:.3f}", f"{duration:.3f}"])

