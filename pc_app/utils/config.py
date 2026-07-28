'''
- config class의 역할 : 설정 관리자
설정(config.json) 읽기/저장
'''

import json
from pathlib import Path


class Config:

    DEFAULT_CONFIG = {
        "user": "Default",
        "save_directory": "./data/csv",
        "backup_directory": "./data/backup",
        "com_port": "AUTO",
        "auto_save": True,
        "auto_reconnect": True,
        "last_session_id": 0
    }

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "config.json"
        self.config = self._load_config()
        self.current_grip_id = 0
        self.current_session_id = self.config["last_session_id"]

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()
            return self.config

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # csv 저장 폴더 생성/반환 함수
    def get_save_directory(self) -> Path:
        base = Path(self.config["save_directory"]).expanduser()
        if not base.is_absolute() : base = self.project_root / base
        session = f"Session{self.get_session_id():03d}"
        return (base / session).resolve()
    
    def set_save_directory(self, directory: str | Path):
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        self.config["save_directory"] = str(directory)
        self.save()

    # 현재 설정을 config.json에 저장
    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(
                self.config,
                file,
                indent=4,
                ensure_ascii=False
            )
    
    # grip_id 관리
    def get_next_grip_id(self):
        self.current_grip_id += 1
        return self.current_grip_id
    
    # session_id 관리
    def create_new_session(self) -> int:

        self.current_grip_id = 0
        self.config["last_session_id"] += 1
        self.current_session_id = self.config["last_session_id"]
        self.save()

        self.get_save_directory().mkdir(parents=True, exist_ok=True)

        return self.config["last_session_id"]
    
    def get_session_id(self) -> int:
        return self.current_session_id

    # -------------------------
    # Getter
    # -------------------------

    def get_user(self) -> str:
        return self.config["user"]

    def get_com_port(self) -> str:
        return self.config["com_port"]

    # -------------------------
    # Setter
    # -------------------------

    def set_user(self, user: str):
        self.config["user"] = user
        self.save()

    def set_com_port(self, port: str):
        self.config["com_port"] = port
        self.save()