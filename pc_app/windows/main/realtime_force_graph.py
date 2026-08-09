from collections import deque
import time

import pyqtgraph as pg

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import QTimer


class RealtimeForceGraph:

    def __init__(self, container: QWidget):

        self.container = container

        # =============================================
        # 데이터
        # =============================================

        self.max_samples = 2000

        self.time_data = deque(maxlen=self.max_samples)
        self.lc1_data = deque(maxlen=self.max_samples)
        self.lc2_data = deque(maxlen=self.max_samples)
        self.lc3_data = deque(maxlen=self.max_samples)
        self.total_data = deque(maxlen=self.max_samples)

        self.start_time = None
        self.running = False


        # =============================================
        # PlotWidget 생성
        # =============================================

        # 그래프 테마
        pg.setConfigOption("background", "w")   # 흰색 배경
        pg.setConfigOption("foreground", "k")   # 검은색 글씨/축
        
        self.plot_widget = pg.PlotWidget(
            parent=self.container
        )

        self.plot_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.plot_widget.setMinimumSize(
            200,
            150
        )


        # =============================================
        # graphContainer의 기존 Layout 확인
        # =============================================

        layout = self.container.layout()

        if layout is None:

            layout = QVBoxLayout(
                self.container
            )

            layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            layout.setSpacing(0)

        else: ...


        # =============================================
        # PlotWidget 추가
        # =============================================

        layout.addWidget(
            self.plot_widget
        )

        self.plot_widget.show()


        # =============================================
        # 그래프 설정
        # =============================================

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


        # =============================================
        # Curve
        # =============================================

        self.lc1_curve = self.plot_widget.plot(
            [],
            [],
            name="LC1",
            pen=pg.mkPen(
                "#3B82F6",
                width=1.5
            )
        )

        self.lc2_curve = self.plot_widget.plot(
            [],
            [],
            name="LC2",
            pen=pg.mkPen(
                "#10B981",
                width=1.5
            )
        )

        self.lc3_curve = self.plot_widget.plot(
            [],
            [],
            name="LC3",
            pen=pg.mkPen(
                "#F59E0B",
                width=1.5
            )
        )

        self.total_curve = self.plot_widget.plot(
            [],
            [],
            name="Total",
            pen=pg.mkPen(
                "#EF4444",
                width=2.5
            )
        )


        # 처음부터 축이 확실히 보이도록 범위 설정
        self.plot_widget.setXRange(
            0,
            10,
            padding=0
        )

        self.plot_widget.setYRange(
            -1,
            5,
            padding=0
        )


        # =============================================
        # 화면 갱신 Timer
        # =============================================

        self.update_timer = QTimer(
            self.container
        )

        self.update_timer.setInterval(
            50
        )

        self.update_timer.timeout.connect(
            self.refresh_graph
        )

        self.update_timer.start()


    def start(self):
        self.clear()

        self.start_time = time.monotonic()
        self.running = True


    def stop(self):
        self.running = False


    def clear(self):

        self.time_data.clear()
        self.lc1_data.clear()
        self.lc2_data.clear()
        self.lc3_data.clear()
        self.total_data.clear()

        self.lc1_curve.setData([], [])
        self.lc2_curve.setData([], [])
        self.lc3_curve.setData([], [])
        self.total_curve.setData([], [])


    def add_data(self, data):

        if not self.running:
            return

        if self.start_time is None:
            return

        elapsed = (
            time.monotonic()
            - self.start_time
        )

        self.time_data.append(elapsed)

        self.lc1_data.append(
            data.force_lc1
        )

        self.lc2_data.append(
            data.force_lc2
        )

        self.lc3_data.append(
            data.force_lc3
        )

        self.total_data.append(
            data.total_force
        )


    def refresh_graph(self):

        if not self.time_data:
            return

        x = list(self.time_data)

        self.lc1_curve.setData(x, list(self.lc1_data))
        self.lc2_curve.setData(x, list(self.lc2_data))
        self.lc3_curve.setData(x, list(self.lc3_data))
        self.total_curve.setData(x, list(self.total_data))

        latest_time = x[-1]
        window_seconds = 10.0

        if latest_time > window_seconds:

            self.plot_widget.setXRange(
                latest_time - window_seconds,
                latest_time,
                padding=0
            )

        else:

            self.plot_widget.setXRange(
                0,
                window_seconds,
                padding=0
            )

    def set_mode(self, mode):

        if hasattr(mode, "value"):
            mode = mode.value

        if mode is None:
            self.lc1_curve.setVisible(False)
            self.lc2_curve.setVisible(False)
            self.lc3_curve.setVisible(False)
            self.total_curve.setVisible(True)
            return

        # -----------------------------
        # 외경
        # -----------------------------
        if mode == "MODE_OD":
            self.lc1_curve.setVisible(True)
            self.lc2_curve.setVisible(True)
            self.lc3_curve.setVisible(False)
            self.total_curve.setVisible(True)

        # -----------------------------
        # 내경 2-Jaw
        # -----------------------------
        elif mode == "MODE_ID_2":
            self.lc1_curve.setVisible(True)
            self.lc2_curve.setVisible(True)
            self.lc3_curve.setVisible(False)
            self.total_curve.setVisible(True)

        # -----------------------------
        # 내경 3-Jaw
        # -----------------------------
        elif mode == "MODE_ID_3":
            self.lc1_curve.setVisible(True)
            self.lc2_curve.setVisible(True)
            self.lc3_curve.setVisible(True)
            self.total_curve.setVisible(True)

        # -----------------------------
        # 알 수 없는 모드
        # -----------------------------
        else:
            self.lc1_curve.setVisible(False)
            self.lc2_curve.setVisible(False)
            self.lc3_curve.setVisible(False)
            self.total_curve.setVisible(True)