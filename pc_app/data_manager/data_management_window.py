from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path

import pyqtgraph as pg

from PySide6.QtCore import QFile, QIODevice, QObject, QThread, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QTableWidgetItem,
    QVBoxLayout,
)


class GripFileLoadWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, csv_path: Path, max_plot_points: int = 5000):
        super().__init__()
        self.csv_path = Path(csv_path)
        self.max_plot_points = max_plot_points

    def run(self):
        try:
            summary = self._scan_summary()
            plot_data = self._scan_plot(summary["samples"])
            summary.update(plot_data)
            self.finished.emit(summary)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _parse_row(self, row):
        # 현재 Grip CSV 형식:
        # elapsed, mode, RAW1, RAW2, RAW3, F1, F2, F3, Total, STATUS
        if len(row) < 10:
            return None

        try:
            elapsed = float(row[0])
            mode = row[1].strip()
            force_lc1 = float(row[5])
            force_lc2 = float(row[6])
            force_lc3 = float(row[7])
            total_force = float(row[8])
            status = int(row[9].strip(), 0)
        except (ValueError, TypeError, IndexError):
            return None

        numeric_values = (
            elapsed,
            force_lc1,
            force_lc2,
            force_lc3,
            total_force,
        )

        if not all(math.isfinite(value) for value in numeric_values):
            return None

        return {
            "elapsed": elapsed,
            "mode": mode,
            "lc1": force_lc1,
            "lc2": force_lc2,
            "lc3": force_lc3,
            "total": total_force,
            "status": status,
        }

    def _scan_summary(self):
        samples = 0
        malformed = 0
        abnormal_status = 0
        mode = None
        duration = 0.0
        peak = None
        force_sum = 0.0

        with self.csv_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)

            for row in reader:
                parsed = self._parse_row(row)

                if parsed is None:
                    malformed += 1
                    continue

                samples += 1
                mode = mode or parsed["mode"]
                duration = max(duration, parsed["elapsed"])
                peak = (
                    parsed["total"]
                    if peak is None
                    else max(peak, parsed["total"])
                )
                force_sum += parsed["total"]

                if parsed["status"] not in (0x36, 0x37):
                    abnormal_status += 1

        if samples <= 0:
            raise ValueError(
                "유효한 측정 데이터가 없습니다.\n"
                "CSV 형식이 현재 PC App 형식과 일치하는지 확인해 주세요."
            )

        sampling_rate = (samples / duration) if duration > 0 else 0.0

        return {
            "path": str(self.csv_path),
            "file_name": self.csv_path.name,
            "mode": mode or "-",
            "samples": samples,
            "duration": duration,
            "peak": peak if peak is not None else 0.0,
            "sampling_rate": sampling_rate,
            "abnormal_status": abnormal_status,
            "malformed": malformed,
        }

    def _scan_plot(self, total_samples: int):
        # 장시간 측정 CSV도 UI에 수십만 점을 그대로 올리지 않도록
        # 최대 약 5,000점으로 표시용 데이터만 추출한다.
        stride = max(
            1,
            math.ceil(total_samples / self.max_plot_points)
        )

        times = []
        lc1 = []
        lc2 = []
        lc3 = []
        total = []

        valid_index = 0

        with self.csv_path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)

            for row in reader:
                parsed = self._parse_row(row)

                if parsed is None:
                    continue

                if valid_index % stride == 0:
                    times.append(parsed["elapsed"])
                    lc1.append(parsed["lc1"])
                    lc2.append(parsed["lc2"])
                    lc3.append(parsed["lc3"])
                    total.append(parsed["total"])

                valid_index += 1

        return {
            "plot_times": times,
            "plot_lc1": lc1,
            "plot_lc2": lc2,
            "plot_lc3": lc3,
            "plot_total": total,
            "plot_stride": stride,
        }


class DataManagementWindow(QMainWindow):

    MODE_TEXT = {
        "MODE_OD": "외경",
        "MODE_ID_2": "내경 2-Jaw",
        "MODE_ID_3": "내경 3-Jaw",
    }

    def __init__(self, base_directory):
        super().__init__()

        self.base_directory = (
            Path(base_directory)
            .expanduser()
            .resolve()
        )

        self.selected_csv_path = None
        self._load_thread = None
        self._load_worker = None

        ui_path = (
            Path(__file__).parent
            / "data_management.ui"
        )

        ui_file = QFile(str(ui_path))

        if not ui_file.open(QIODevice.ReadOnly):
            raise FileNotFoundError(
                f"Cannot open {ui_path}"
            )

        self.ui = QUiLoader().load(ui_file)
        ui_file.close()

        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        self.setWindowTitle("데이터 관리")

        # 기존 팝업 창 정책과 동일:
        # 최대화 및 임의 크기 변경 방지
        self.setWindowFlag(
            Qt.WindowMaximizeButtonHint,
            False
        )

        self.setFixedSize(
            self.ui.size()
        )

        self.ui.basePathEdit.setText(
            str(self.base_directory)
        )

        self._setup_table()
        self._setup_graph()
        self._connect_signals()

        self.refresh_sessions()

    def _setup_table(self):
        table = self.ui.gripTable

        table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        header = table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.Stretch
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeToContents
        )

    def _setup_graph(self):
        pg.setConfigOption(
            "background",
            "w"
        )

        pg.setConfigOption(
            "foreground",
            "k"
        )

        self.plot_widget = pg.PlotWidget(
            parent=self.ui.graphContainer
        )

        layout = self.ui.graphContainer.layout()

        if layout is None:
            layout = QVBoxLayout(
                self.ui.graphContainer
            )

            layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            layout.setSpacing(0)

        layout.addWidget(
            self.plot_widget
        )

        self.plot_widget.setLabel(
            "bottom",
            "Time",
            units="s"
        )

        self.plot_widget.setLabel(
            "left",
            "Force",
            units="N"
        )

        self.plot_widget.showGrid(
            x=True,
            y=True,
            alpha=0.15
        )

        self.plot_widget.addLegend()

        self.plot_widget.setMouseEnabled(
            x=True,
            y=True
        )

        self.lc1_curve = self.plot_widget.plot(
            [],
            [],
            name="LC1",
            pen=pg.mkPen(
                "#3B82F6",
                width=1.4
            )
        )

        self.lc2_curve = self.plot_widget.plot(
            [],
            [],
            name="LC2",
            pen=pg.mkPen(
                "#10B981",
                width=1.4
            )
        )

        self.lc3_curve = self.plot_widget.plot(
            [],
            [],
            name="LC3",
            pen=pg.mkPen(
                "#F59E0B",
                width=1.4
            )
        )

        self.total_curve = self.plot_widget.plot(
            [],
            [],
            name="Total",
            pen=pg.mkPen(
                "#EF4444",
                width=2.2
            )
        )

    def _connect_signals(self):
        self.ui.refreshButton.clicked.connect(
            self.refresh_sessions
        )

        self.ui.openBaseFolderButton.clicked.connect(
            self.open_base_folder
        )

        self.ui.openSelectedCsvButton.clicked.connect(
            self.open_selected_csv
        )

        self.ui.sessionComboBox.currentIndexChanged.connect(
            self.load_selected_session
        )

        self.ui.gripTable.itemSelectionChanged.connect(
            self.handle_grip_selection
        )

        self.ui.gripTable.itemDoubleClicked.connect(
            lambda *_: self.open_selected_csv()
        )

    def refresh_sessions(self):
        self.base_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        current_name = (
            self.ui.sessionComboBox.currentText()
        )

        sessions = [
            path
            for path in self.base_directory.glob("Session*")
            if path.is_dir()
        ]

        def session_sort_key(path):
            digits = "".join(
                ch
                for ch in path.name
                if ch.isdigit()
            )

            return (
                int(digits)
                if digits
                else -1
            )

        sessions.sort(
            key=session_sort_key,
            reverse=True
        )

        self.ui.sessionComboBox.blockSignals(True)
        self.ui.sessionComboBox.clear()

        for session_path in sessions:
            self.ui.sessionComboBox.addItem(
                session_path.name,
                str(session_path)
            )

        self.ui.sessionComboBox.blockSignals(False)

        if not sessions:
            self.ui.gripTable.setRowCount(0)
            self._reset_summary(
                "저장된 Session이 없습니다."
            )
            self._clear_plot()
            return

        restore_index = (
            self.ui.sessionComboBox.findText(
                current_name
            )
        )

        self.ui.sessionComboBox.setCurrentIndex(
            restore_index
            if restore_index >= 0
            else 0
        )

        self.load_selected_session()

    def load_selected_session(self):
        session_path_text = (
            self.ui.sessionComboBox.currentData()
        )

        if not session_path_text:
            self.ui.gripTable.setRowCount(0)
            return

        session_path = Path(
            session_path_text
        )

        grip_files = [
            path
            for path in session_path.glob("G*.csv")
            if not path.stem.endswith("_events")
        ]
        grip_files.sort(
            key=lambda path: path.stat().st_mtime,
            reverse=True
        )

        table = self.ui.gripTable
        table.blockSignals(True)
        table.setRowCount(0)

        for csv_path in grip_files:
            row = table.rowCount()
            table.insertRow(row)

            stat = csv_path.stat()

            size_mb = (
                stat.st_size
                / (1024 * 1024)
            )

            modified = datetime.fromtimestamp(
                stat.st_mtime
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            file_item = QTableWidgetItem(
                csv_path.name
            )

            file_item.setData(
                Qt.UserRole,
                str(csv_path)
            )

            table.setItem(
                row,
                0,
                file_item
            )

            table.setItem(
                row,
                1,
                QTableWidgetItem(
                    f"{size_mb:.2f} MB"
                )
            )

            table.setItem(
                row,
                2,
                QTableWidgetItem(
                    modified
                )
            )

        table.blockSignals(False)

        self.selected_csv_path = None

        self._reset_summary(
            "측정 파일을 선택하세요."
            if grip_files
            else "이 Session에는 측정 CSV가 없습니다."
        )

        self._clear_plot()

    def handle_grip_selection(self):
        selected_rows = (
            self.ui.gripTable
            .selectionModel()
            .selectedRows()
        )

        if not selected_rows:
            self.selected_csv_path = None
            return

        row = selected_rows[0].row()

        item = self.ui.gripTable.item(
            row,
            0
        )

        if item is None:
            return

        csv_path = Path(
            item.data(Qt.UserRole)
        )

        self.selected_csv_path = csv_path

        self.load_grip_file(
            csv_path
        )

    def load_grip_file(
        self,
        csv_path: Path
    ):
        if (
            self._load_thread is not None
            and self._load_thread.isRunning()
        ):
            self.ui.loadingLabel.setText(
                "이전 측정 파일을 읽는 중입니다. "
                "잠시 후 다시 선택해 주세요."
            )
            return

        self._reset_summary(
            f"{csv_path.name} 읽는 중..."
        )

        self.ui.loadingLabel.setText(
            "CSV를 분석하고 그래프를 준비하는 중..."
        )

        self.ui.gripTable.setEnabled(
            False
        )

        thread = QThread(self)

        worker = GripFileLoadWorker(
            csv_path
        )

        worker.moveToThread(
            thread
        )

        thread.started.connect(
            worker.run
        )

        worker.finished.connect(
            self._handle_load_finished
        )

        worker.failed.connect(
            self._handle_load_failed
        )

        worker.finished.connect(
            thread.quit
        )

        worker.failed.connect(
            thread.quit
        )

        worker.finished.connect(
            worker.deleteLater
        )

        worker.failed.connect(
            worker.deleteLater
        )

        thread.finished.connect(
            thread.deleteLater
        )

        thread.finished.connect(
            self._clear_load_thread_reference
        )

        self._load_thread = thread
        self._load_worker = worker

        thread.start()

    def _clear_load_thread_reference(self):
        self._load_thread = None
        self._load_worker = None

        self.ui.gripTable.setEnabled(
            True
        )

    def _handle_load_finished(
        self,
        result: dict
    ):
        if (
            self.selected_csv_path is not None
            and Path(result["path"])
            != self.selected_csv_path
        ):
            return

        mode_text = self.MODE_TEXT.get(
            result["mode"],
            result["mode"]
        )

        duration = result["duration"]
        minutes = int(duration // 60)
        seconds = duration % 60

        self.ui.fileValueLabel.setText(
            result["file_name"]
        )

        self.ui.modeValueLabel.setText(
            mode_text
        )

        self.ui.samplesValueLabel.setText(
            f'{result["samples"]:,}'
        )

        self.ui.durationValueLabel.setText(
            f"{minutes:02d}:{seconds:04.1f}"
        )

        self.ui.peakValueLabel.setText(
            f'{result["peak"]:.3f} N'
        )

        self.ui.rateValueLabel.setText(
            f'{result["sampling_rate"]:.1f} Hz'
        )

        abnormal = result["abnormal_status"]
        malformed = result["malformed"]

        if abnormal == 0:
            status_text = "정상"
        else:
            status_text = (
                f"비정상 {abnormal:,}건"
            )

        if malformed:
            status_text += (
                f" / 형식오류 {malformed:,}행"
            )

        self.ui.statusValueLabel.setText(
            status_text
        )

        self.ui.loadingLabel.setText(
            f'그래프 표시 간격: '
            f'{result["plot_stride"]} sample'
        )

        self._update_plot(
            result
        )

    def _handle_load_failed(
        self,
        message: str
    ):
        self.ui.loadingLabel.setText(
            "CSV 읽기 실패"
        )

        self._clear_plot()

        QMessageBox.warning(
            self,
            "데이터 조회 실패",
            "측정 CSV를 읽지 못했습니다."
            f"\n\n{message}"
        )

    def _update_plot(
        self,
        result
    ):
        times = result["plot_times"]

        self.lc1_curve.setData(
            times,
            result["plot_lc1"]
        )

        self.lc2_curve.setData(
            times,
            result["plot_lc2"]
        )

        self.lc3_curve.setData(
            times,
            result["plot_lc3"]
        )

        self.total_curve.setData(
            times,
            result["plot_total"]
        )

        mode = result["mode"]

        self.lc1_curve.setVisible(True)
        self.lc2_curve.setVisible(True)
        self.total_curve.setVisible(True)

        self.lc3_curve.setVisible(
            mode == "MODE_ID_3"
        )

        self.plot_widget.enableAutoRange()
        self.plot_widget.autoRange()

    def _clear_plot(self):
        self.lc1_curve.setData([], [])
        self.lc2_curve.setData([], [])
        self.lc3_curve.setData([], [])
        self.total_curve.setData([], [])

    def _reset_summary(
        self,
        message="측정 파일을 선택하세요."
    ):
        self.ui.fileValueLabel.setText("-")
        self.ui.modeValueLabel.setText("-")
        self.ui.samplesValueLabel.setText("-")
        self.ui.durationValueLabel.setText("-")
        self.ui.peakValueLabel.setText("-")
        self.ui.rateValueLabel.setText("-")
        self.ui.statusValueLabel.setText("-")

        self.ui.loadingLabel.setText(
            message
        )

    def open_base_folder(self):
        self.base_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(self.base_directory)
            )
        )

    def open_selected_csv(self):
        if self.selected_csv_path is None:
            QMessageBox.information(
                self,
                "데이터 관리",
                "먼저 측정 CSV를 선택해 주세요."
            )
            return

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(self.selected_csv_path)
            )
        )

    def closeEvent(self, event):
        if (
            self._load_thread is not None
            and self._load_thread.isRunning()
        ):
            QMessageBox.information(
                self,
                "데이터 관리",
                "CSV를 읽는 중입니다. "
                "잠시 후 창을 닫아 주세요."
            )

            event.ignore()
            return

        event.accept()
