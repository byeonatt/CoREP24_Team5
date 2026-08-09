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

        # =====================================================
        # Y-axis Auto Range
        # =====================================================

        # 그래프에 표시하는 최근 시간
        self.display_window_seconds = 10.0

        # 새 측정 시작 시 기본 Y축
        self.default_y_min = -0.5
        self.default_y_max = 1.0

        # Y축이 이것보다 좁아지지 않도록 함
        self.min_y_span = 1.0

        # 데이터 위/아래 여백
        self.y_margin_ratio = 0.15
        self.y_margin_abs = 0.10

        # 값이 작아진 뒤 Y축 축소를 시작하기까지 대기시간
        self.y_shrink_delay = 5.0

        # Y축 축소 계산 간격
        self.y_shrink_interval = 0.5

        # 한 번 축소할 때 목표 범위로 이동하는 비율
        # 0.20 = 한 번에 20%
        self.y_shrink_ratio = 0.20

        # 현재 Y축 범위
        self.current_y_min = self.default_y_min
        self.current_y_max = self.default_y_max

        # 축소 대기 상태
        self.y_shrink_candidate_since = None
        self.last_y_shrink_time = time.monotonic()


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
            y=False
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
            self.default_y_min,
            self.default_y_max,
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

        # Y축 상태 초기화
        self.current_y_min = self.default_y_min
        self.current_y_max = self.default_y_max

        self.y_shrink_candidate_since = None
        self.last_y_shrink_time = time.monotonic()

        self.plot_widget.setYRange(
            self.current_y_min,
            self.current_y_max,
            padding=0
        )


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

        if latest_time > self.display_window_seconds:

            self.plot_widget.setXRange(
                latest_time - self.display_window_seconds,
                latest_time,
                padding=0
            )

        else:

            self.plot_widget.setXRange(
                0,
                self.display_window_seconds,
                padding=0
            )
        self.update_y_range()

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

    def get_visible_force_values(self):

        if not self.time_data:
            return []

        times = list(self.time_data)
        latest_time = times[-1]
        cutoff = (latest_time - self.display_window_seconds)

        # 최근 10초가 시작되는 index 찾기
        start_index = 0

        for index, timestamp in enumerate(times):

            if timestamp >= cutoff:
                start_index = index
                break

        values = []

        if self.lc1_curve.isVisible():
            values.extend(list(self.lc1_data)[start_index:])
        if self.lc2_curve.isVisible():
            values.extend(list(self.lc2_data)[start_index:])
        if self.lc3_curve.isVisible():
            values.extend(list(self.lc3_data)[start_index:])
        if self.total_curve.isVisible():
            values.extend(list(self.total_data)[start_index:])

        return values

    def calculate_target_y_range(self):

        values = self.get_visible_force_values()

        if not values:
            return (
                self.default_y_min,
                self.default_y_max
            )

        data_min = min(values)
        data_max = max(values)

        # 0 N 기준선도 화면에 포함
        base_min = min(
            data_min,
            0.0
        )

        base_max = max(
            data_max,
            0.0
        )

        raw_span = (
            base_max
            - base_min
        )

        # 여백 계산에 사용할 span
        margin_span = max(
            raw_span,
            self.min_y_span
        )

        margin = max(
            margin_span * self.y_margin_ratio,
            self.y_margin_abs
        )

        target_min = (
            base_min
            - margin
        )

        target_max = (
            base_max
            + margin
        )


        # -----------------------------------------
        # 최소 Y축 폭 보장
        # -----------------------------------------

        target_span = (
            target_max
            - target_min
        )

        if target_span < self.min_y_span:

            center = (
                target_min
                + target_max
            ) / 2.0

            half_span = (
                self.min_y_span
                / 2.0
            )

            target_min = (
                center
                - half_span
            )

            target_max = (
                center
                + half_span
            )

        return (
            target_min,
            target_max
        )

    def update_y_range(self):

        if not self.time_data:
            return

        now = time.monotonic()

        target_min, target_max = (self.calculate_target_y_range())

        expand_lower = (
            target_min
            < self.current_y_min
        )

        expand_upper = (
            target_max
            > self.current_y_max
        )

        if expand_lower or expand_upper:

            if expand_lower:
                self.current_y_min = target_min

            if expand_upper:
                self.current_y_max = target_max

            self.plot_widget.setYRange(
                self.current_y_min,
                self.current_y_max,
                padding=0
            )
            self.y_shrink_candidate_since = None
            return


        if self.y_shrink_candidate_since is None:
            self.y_shrink_candidate_since = now
            return

        stable_time = (
            now
            - self.y_shrink_candidate_since
        )

        if stable_time < self.y_shrink_delay:
            return

        if (
            now
            - self.last_y_shrink_time
            < self.y_shrink_interval
        ):
            return

        self.last_y_shrink_time = now


        self.current_y_min += (
            target_min
            - self.current_y_min
        ) * self.y_shrink_ratio

        self.current_y_max += (
            target_max
            - self.current_y_max
        ) * self.y_shrink_ratio


        if abs(
            self.current_y_min
            - target_min
        ) < 0.01:

            self.current_y_min = target_min


        if abs(
            self.current_y_max
            - target_max
        ) < 0.01:

            self.current_y_max = target_max


        self.plot_widget.setYRange(
            self.current_y_min,
            self.current_y_max,
            padding=0
        )