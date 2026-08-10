from collections import deque
from bisect import bisect_left, bisect_right
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
        # Local Peak Detection # Peak 관련은 여기를 수정
        # =====================================================

        # Peak 주변을 비교할 시간
        # 앞뒤 0.15초
        self.peak_neighborhood_seconds = 0.15

        # 주변 값보다 최소 이만큼 높아야 Peak
        self.peak_min_prominence = 0.15

        # 아주 작은 힘의 노이즈는 Peak에서 제외
        self.peak_min_force = 0.30

        # Peak끼리 너무 가까우면 하나로 합침
        self.peak_min_distance_seconds = 0.25

        # 현재 그래프에 표시된 Peak
        self.local_peaks = []

        # Peak 라벨 TextItem 목록
        self.peak_text_items = []

        # 불필요하게 계속 그래픽을 다시 만들지 않기 위한 상태값
        self.peak_signature = None

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

        # =====================================================
        # Local Peak Marker
        # =====================================================

        self.peak_scatter = pg.ScatterPlotItem(
            size=10,
            symbol="o",
            pen=pg.mkPen(
                "#B91C1C",
                width=2
            ),
            brush=pg.mkBrush(
                "#EF4444"
            )
        )

        self.plot_widget.addItem(
            self.peak_scatter
        )

        self.peak_scatter.setData(
            [],
            []
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

        self.local_peaks.clear()
        self.peak_signature = None

        self.peak_scatter.setData([], [])
        for text_item in self.peak_text_items:

            self.plot_widget.removeItem(
                text_item
            )
        self.peak_text_items.clear()


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
        self.update_local_peak_markers()

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

    def find_local_peaks(self):

        if len(self.time_data) < 3:
            return []

        times = list(self.time_data)
        forces = list(self.total_data)

        if not times:
            return []

        latest_time = times[-1]

        # 현재 화면에 보이는 최근 10초 정도만 분석
        visible_start_time = max(
            0.0,
            latest_time - self.display_window_seconds
        )

        start_index = bisect_left(
            times,
            visible_start_time
        )

        candidates = []


        # =================================================
        # Local Maximum 탐색
        # =================================================

        for i in range(
            max(start_index, 1),
            len(times) - 1
        ):

            peak_time = times[i]
            peak_force = forces[i]

            if peak_force < self.peak_min_force:
                continue

            left_time = (
                peak_time
                - self.peak_neighborhood_seconds
            )

            right_time = (
                peak_time
                + self.peak_neighborhood_seconds
            )

            left_index = bisect_left(
                times,
                left_time
            )

            right_index = bisect_right(
                times,
                right_time
            )


            if right_time > latest_time:
                continue

            if left_index >= i:
                continue

            if right_index <= i + 1:
                continue


            left_values = forces[
                left_index:i
            ]

            right_values = forces[
                i + 1:right_index
            ]

            if not left_values or not right_values:
                continue


            surrounding_max = max(
                max(left_values),
                max(right_values)
            )

            if peak_force <= surrounding_max:
                continue

            left_base = min(
                left_values
            )

            right_base = min(
                right_values
            )

            baseline = max(
                left_base,
                right_base
            )

            prominence = (
                peak_force
                - baseline
            )


            if prominence < self.peak_min_prominence:
                continue


            candidates.append(
                (
                    peak_time,
                    peak_force
                )
            )


        filtered = []

        for peak_time, peak_force in candidates:

            if not filtered:

                filtered.append(
                    (
                        peak_time,
                        peak_force
                    )
                )

                continue


            previous_time, previous_force = (
                filtered[-1]
            )

            distance = (
                peak_time
                - previous_time
            )


            # 충분히 떨어져 있으면 별개의 Grip Peak
            if distance >= self.peak_min_distance_seconds:

                filtered.append(
                    (
                        peak_time,
                        peak_force
                    )
                )

                continue


            # 너무 가까운 Peak면 둘 중 높은 것만 유지
            if peak_force > previous_force:

                filtered[-1] = (
                    peak_time,
                    peak_force
                )


        return filtered

    def update_local_peak_markers(self):

        peaks = self.find_local_peaks()


        # =================================================
        # 이전 화면과 동일하면 아무것도 하지 않음
        # =================================================

        signature = tuple(
            (
                round(t, 3),
                round(force, 3)
            )
            for t, force in peaks
        )

        if signature == self.peak_signature:
            return

        self.peak_signature = signature
        self.local_peaks = peaks


        # =================================================
        # Scatter 점 갱신
        # =================================================

        if peaks:

            x_values = [
                t
                for t, _
                in peaks
            ]

            y_values = [
                force
                for _, force
                in peaks
            ]

            self.peak_scatter.setData(
                x_values,
                y_values
            )

        else:

            self.peak_scatter.setData(
                [],
                []
            )

        for text_item in self.peak_text_items:

            self.plot_widget.removeItem(
                text_item
            )

        self.peak_text_items.clear()

        for peak_time, peak_force in peaks:

            text = pg.TextItem(
                text=f"{peak_force:.2f} N",
                color="#B91C1C",
                anchor=(0.5, 1.25)
            )

            text.setPos(
                peak_time,
                peak_force
            )

            self.plot_widget.addItem(
                text
            )

            self.peak_text_items.append(
                text
            )