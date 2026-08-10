"""
설정 관리자
- config.json 읽기/저장
- 저장 경로 / COM 포트 / Session ID 관리
- 판정 기준 적용 여부 및 모드별 판정 범위 관리
"""

import copy
import json
import math
from pathlib import Path


class Config:

    DEFAULT_CONFIG = {
        "user": "Default",
        "save_directory": "",
        "com_port": "AUTO",
        "auto_save": True,
        "auto_reconnect": True,
        "last_session_id": 0,

        # 판정 기준
        # enabled=False일 때는 min/max 값을 보존하되 실제 판정에는 사용하지 않는다.
        "judgement": {
            "enabled": False,
            "MODE_OD": {
                "min_force": 0.0,
                "max_force": 0.0
            },
            "MODE_ID_2": {
                "min_force": 0.0,
                "max_force": 0.0
            },
            "MODE_ID_3": {
                "min_force": 0.0,
                "max_force": 0.0
            }
        }
    }

    VALID_JUDGEMENT_MODES = (
        "MODE_OD",
        "MODE_ID_2",
        "MODE_ID_3",
    )

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "config.json"

        self.config = self._load_config()

        self.current_grip_id = 0
        self.current_session_id = None

    # =====================================================
    # config.json 로드 / 마이그레이션
    # =====================================================

    @classmethod
    def _merge_defaults(cls, defaults, loaded):
        """
        기존 config.json에 새 설정 항목이 없어도
        DEFAULT_CONFIG의 값을 재귀적으로 보충한다.
        """
        result = copy.deepcopy(defaults)

        if not isinstance(loaded, dict):
            return result

        for key, value in loaded.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = cls._merge_defaults(
                    result[key],
                    value
                )
            else:
                result[key] = value

        return result

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            config = copy.deepcopy(
                self.DEFAULT_CONFIG
            )

            self.config = config
            self.save()

            return config

        try:
            with self.config_path.open(
                "r",
                encoding="utf-8"
            ) as file:
                loaded = json.load(file)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            loaded = {}

        config = self._merge_defaults(
            self.DEFAULT_CONFIG,
            loaded
        )

        # 기존 config.json을 새 스키마로 자동 갱신
        self.config = config
        self.save()

        return config

    # =====================================================
    # CSV 저장 폴더
    # =====================================================

    def get_base_directory(self) -> Path:
        save_directory = self.config.get(
            "save_directory",
            ""
        )

        if save_directory:
            base = Path(
                save_directory
            ).expanduser()
        else:
            base = (
                Path.home()
                / "Documents"
                / "GripForceData"
            )

        if not base.is_absolute():
            base = self.project_root / base

        return base.resolve()

    def get_save_directory(self) -> Path:
        session = (
            f"Session"
            f"{self.get_session_id():03d}"
        )

        return (
            self.get_base_directory()
            / session
        ).resolve()

    def set_save_directory(
        self,
        directory: str | Path
    ):
        directory = (
            Path(directory)
            .expanduser()
            .resolve()
        )

        directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.config[
            "save_directory"
        ] = str(directory)

        self.save()

    # =====================================================
    # 저장
    # =====================================================

    def save(self):
        with self.config_path.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                self.config,
                file,
                indent=4,
                ensure_ascii=False
            )

    # =====================================================
    # Grip / Session ID
    # =====================================================

    def get_next_grip_id(self):
        self.current_grip_id += 1
        return self.current_grip_id

    def create_new_session(self) -> int:
        self.current_grip_id = 0

        session_id = (
            self.get_session_id()
        )

        self.current_session_id = (
            session_id
        )

        self.config[
            "last_session_id"
        ] = session_id

        self.save()

        session_directory = (
            self.get_base_directory()
            / f"Session{session_id:03d}"
        )

        session_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        return session_id

    def get_session_id(self) -> int:
        if (
            self.current_session_id
            is not None
        ):
            return (
                self.current_session_id
            )

        last_session_id = (
            self.config.get(
                "last_session_id",
                0
            )
        )

        if last_session_id <= 0:
            return 1

        base_directory = (
            self.get_base_directory()
        )

        last_session_path = (
            base_directory
            / f"Session{last_session_id:03d}"
        )

        # G0001_events.csv는 Measurement 파일로 세지 않음.
        grip_files = [
            path
            for path
            in last_session_path.glob(
                "G*.csv"
            )
            if not path.stem.endswith(
                "_events"
            )
        ]

        if not grip_files:
            return last_session_id

        return last_session_id + 1

    # =====================================================
    # 일반 Getter / Setter
    # =====================================================

    def get_user(self) -> str:
        return self.config["user"]

    def get_com_port(self) -> str:
        return self.config["com_port"]

    def set_user(
        self,
        user: str
    ):
        self.config["user"] = user
        self.save()

    def set_com_port(
        self,
        port: str
    ):
        self.config["com_port"] = port
        self.save()

    # =====================================================
    # 판정 기준 Getter
    # =====================================================

    def get_judgement_enabled(
        self
    ) -> bool:
        judgement = self.config.get(
            "judgement",
            {}
        )

        return bool(
            judgement.get(
                "enabled",
                False
            )
        )

    def get_judgement_limits(
        self,
        mode: str
    ) -> dict:
        if (
            mode
            not in self.VALID_JUDGEMENT_MODES
        ):
            raise ValueError(
                f"지원하지 않는 측정 모드입니다: {mode}"
            )

        judgement = self.config.get(
            "judgement",
            {}
        )

        limits = judgement.get(
            mode,
            {}
        )

        return {
            "min_force": float(
                limits.get(
                    "min_force",
                    0.0
                )
            ),
            "max_force": float(
                limits.get(
                    "max_force",
                    0.0
                )
            ),
        }

    def get_all_judgement_settings(
        self
    ) -> dict:
        result = {
            "enabled":
                self.get_judgement_enabled()
        }

        for mode in (
            self.VALID_JUDGEMENT_MODES
        ):
            result[mode] = (
                self.get_judgement_limits(
                    mode
                )
            )

        return result

    def get_judgement_snapshot(
        self,
        mode: str
    ) -> dict:
        """
        Measurement 시작 순간 호출할 Snapshot.

        판정 미적용이면:
        {
            "enabled": False,
            "lower_limit_n": None,
            "upper_limit_n": None
        }

        판정 적용이면 현재 모드의 범위를 복사해 반환한다.
        이후 config 값이 바뀌어도 이 dict는 변하지 않는다.
        """

        enabled = (
            self.get_judgement_enabled()
        )

        if not enabled:
            return {
                "enabled": False,
                "lower_limit_n": None,
                "upper_limit_n": None,
            }

        limits = (
            self.get_judgement_limits(
                mode
            )
        )

        min_force = (
            limits["min_force"]
        )

        max_force = (
            limits["max_force"]
        )

        self._validate_force_range(
            mode,
            min_force,
            max_force
        )

        return {
            "enabled": True,
            "lower_limit_n": min_force,
            "upper_limit_n": max_force,
        }

    # =====================================================
    # 판정 기준 Setter
    # =====================================================

    @staticmethod
    def _validate_number(
        name: str,
        value
    ) -> float:
        try:
            value = float(value)
        except (
            TypeError,
            ValueError
        ):
            raise ValueError(
                f"{name}: 숫자를 입력해 주세요."
            )

        if not math.isfinite(value):
            raise ValueError(
                f"{name}: 유효한 숫자가 아닙니다."
            )

        if value < 0:
            raise ValueError(
                f"{name}: 0 N 이상이어야 합니다."
            )

        return value

    @classmethod
    def _validate_force_range(
        cls,
        mode: str,
        min_force,
        max_force
    ):
        min_force = cls._validate_number(
            f"{mode} 최소값",
            min_force
        )

        max_force = cls._validate_number(
            f"{mode} 최대값",
            max_force
        )

        if min_force >= max_force:
            raise ValueError(
                f"{mode}: 최소값은 최대값보다 "
                "작아야 합니다."
            )

        return min_force, max_force

    def set_judgement_enabled(
        self,
        enabled: bool
    ):
        self.config.setdefault(
            "judgement",
            {}
        )

        self.config[
            "judgement"
        ]["enabled"] = bool(
            enabled
        )

        self.save()

    def set_judgement_limits(
        self,
        mode: str,
        min_force,
        max_force
    ):
        if (
            mode
            not in self.VALID_JUDGEMENT_MODES
        ):
            raise ValueError(
                f"지원하지 않는 측정 모드입니다: {mode}"
            )

        min_force, max_force = (
            self._validate_force_range(
                mode,
                min_force,
                max_force
            )
        )

        self.config.setdefault(
            "judgement",
            {}
        )

        self.config[
            "judgement"
        ][mode] = {
            "min_force": min_force,
            "max_force": max_force,
        }

        self.save()

    def set_judgement_settings(
        self,
        enabled: bool,
        limits_by_mode: dict
    ):
        """
        판정 설정 창에서 한 번에 저장할 때 사용.

        enabled=False:
        - 판정은 미적용으로 저장
        - 사용자가 입력해둔 유효한 범위는 그대로 보존 가능

        enabled=True:
        - 세 모드 모두 min < max인지 검증
        """

        enabled = bool(enabled)

        normalized = {}

        for mode in (
            self.VALID_JUDGEMENT_MODES
        ):
            values = (
                limits_by_mode.get(
                    mode,
                    {}
                )
            )

            min_force = (
                self._validate_number(
                    f"{mode} 최소값",
                    values.get(
                        "min_force",
                        0.0
                    )
                )
            )

            max_force = (
                self._validate_number(
                    f"{mode} 최대값",
                    values.get(
                        "max_force",
                        0.0
                    )
                )
            )

            # 판정을 적용할 때만 범위 유효성 강제
            if enabled:
                if min_force >= max_force:
                    raise ValueError(
                        f"{mode}: 최소값은 "
                        "최대값보다 작아야 합니다."
                    )

            normalized[mode] = {
                "min_force": min_force,
                "max_force": max_force,
            }

        self.config[
            "judgement"
        ] = {
            "enabled": enabled,
            **normalized
        }

        self.save()
