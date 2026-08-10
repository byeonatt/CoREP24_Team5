from dataclasses import dataclass
from enum import Enum, auto


@dataclass(frozen=True)
class GripEvent:
    event_id: int
    start_time_s: float
    peak_time_s: float
    end_time_s: float
    duration_s: float
    peak_force_n: float


class GripState(Enum):
    IDLE = auto()
    GRIPPING = auto()
    RELEASING = auto()


class GripEventDetector:
    """
    Total Force를 이용해 실제 파지 동작을 실시간에 가깝게 검출한다.

    기본 동작:
    1) force >= start_threshold_n      -> Grip 시작
    2) Grip 중 최대 force / 시각 추적
    3) force <= release_threshold_n    -> Release 후보
    4) release_hold_seconds 동안 낮은 상태 유지 -> Event 확정
    5) peak < min_peak_force_n 또는 너무 짧은 Event는 폐기

    update()는 Event가 확정되는 순간 GripEvent를 반환하고,
    그 외에는 None을 반환한다.
    """

    def __init__(
        self,
        start_threshold_n: float = 0.50,
        release_threshold_n: float = 0.20,
        release_hold_seconds: float = 0.20,
        min_peak_force_n: float = 1.00,
        min_event_duration_s: float = 0.10,
        min_event_gap_s: float = 0.30,
    ):
        if release_threshold_n >= start_threshold_n:
            raise ValueError(
                "release_threshold_n은 start_threshold_n보다 작아야 합니다."
            )

        if release_hold_seconds < 0:
            raise ValueError("release_hold_seconds는 0 이상이어야 합니다.")

        if min_event_duration_s < 0:
            raise ValueError("min_event_duration_s는 0 이상이어야 합니다.")

        if min_event_gap_s < 0:
            raise ValueError("min_event_gap_s는 0 이상이어야 합니다.")

        self.start_threshold_n = float(start_threshold_n)
        self.release_threshold_n = float(release_threshold_n)
        self.release_hold_seconds = float(release_hold_seconds)
        self.min_peak_force_n = float(min_peak_force_n)
        self.min_event_duration_s = float(min_event_duration_s)
        self.min_event_gap_s = float(min_event_gap_s)

        self.reset()

    def reset(self):
        self.state = GripState.IDLE

        self.event_count = 0
        self.last_event_end_time_s = None

        self.start_time_s = None
        self.peak_time_s = None
        self.peak_force_n = None

        self.release_candidate_time_s = None

    @property
    def is_active(self) -> bool:
        return self.state != GripState.IDLE

    def cancel_active_event(self):
        """
        측정 종료/통신 오류 등으로 진행 중 Event를 폐기할 때 사용.
        이미 확정된 event_count는 유지한다.
        """
        self.state = GripState.IDLE
        self.start_time_s = None
        self.peak_time_s = None
        self.peak_force_n = None
        self.release_candidate_time_s = None

    def update(
        self,
        elapsed_time_s: float,
        total_force_n: float,
    ) -> GripEvent | None:
        now = float(elapsed_time_s)
        force = float(total_force_n)

        # -------------------------------------------------
        # IDLE
        # -------------------------------------------------
        if self.state == GripState.IDLE:
            if force < self.start_threshold_n:
                return None

            # 직전 Event와 너무 가까우면 새 Event 시작을 잠시 막는다.
            if self.last_event_end_time_s is not None:
                if (
                    now - self.last_event_end_time_s
                    < self.min_event_gap_s
                ):
                    return None

            self.state = GripState.GRIPPING
            self.start_time_s = now
            self.peak_time_s = now
            self.peak_force_n = force
            self.release_candidate_time_s = None

            return None

        # -------------------------------------------------
        # GRIPPING
        # -------------------------------------------------
        if self.state == GripState.GRIPPING:
            self._update_peak(now, force)

            if force <= self.release_threshold_n:
                self.state = GripState.RELEASING
                self.release_candidate_time_s = now

            return None

        # -------------------------------------------------
        # RELEASING
        # -------------------------------------------------
        if self.state == GripState.RELEASING:
            self._update_peak(now, force)

            # Release 확인 도중 힘이 다시 올라오면 같은 Grip으로 계속 본다.
            if force > self.release_threshold_n:
                self.state = GripState.GRIPPING
                self.release_candidate_time_s = None
                return None

            if self.release_candidate_time_s is None:
                self.release_candidate_time_s = now
                return None

            low_duration = (
                now - self.release_candidate_time_s
            )

            if low_duration < self.release_hold_seconds:
                return None

            # 실제 Event 종료 시점은 "낮은 힘이 시작된 순간"으로 기록하고,
            # 이후 hold 시간은 검출 확정 지연으로만 사용한다.
            end_time_s = self.release_candidate_time_s

            event = self._finalize_event(end_time_s)

            # Event가 유효하지 않더라도 상태는 IDLE로 복귀한다.
            self.state = GripState.IDLE
            self.start_time_s = None
            self.peak_time_s = None
            self.peak_force_n = None
            self.release_candidate_time_s = None

            if event is not None:
                self.last_event_end_time_s = event.end_time_s

            return event

        return None

    def _update_peak(
        self,
        elapsed_time_s: float,
        force_n: float,
    ):
        if self.peak_force_n is None:
            self.peak_force_n = force_n
            self.peak_time_s = elapsed_time_s
            return

        if force_n > self.peak_force_n:
            self.peak_force_n = force_n
            self.peak_time_s = elapsed_time_s

    def _finalize_event(
        self,
        end_time_s: float,
    ) -> GripEvent | None:
        if (
            self.start_time_s is None
            or self.peak_time_s is None
            or self.peak_force_n is None
        ):
            return None

        duration_s = (
            end_time_s - self.start_time_s
        )

        if duration_s < self.min_event_duration_s:
            return None

        if self.peak_force_n < self.min_peak_force_n:
            return None

        self.event_count += 1

        return GripEvent(
            event_id=self.event_count,
            start_time_s=self.start_time_s,
            peak_time_s=self.peak_time_s,
            end_time_s=end_time_s,
            duration_s=duration_s,
            peak_force_n=self.peak_force_n,
        )
