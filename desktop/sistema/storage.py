from __future__ import annotations

import json
import os
from pathlib import Path

from .game import PlayerState


def default_data_dir() -> Path:
    override = os.environ.get("SISTEMA_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / "Sistema"
    return Path.home() / ".sistema"


class PlayerStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or default_data_dir()
        self.path = self.data_dir / "progress.json"
        self.backup_path = self.data_dir / "progress.backup.json"

    def load(self) -> PlayerState:
        if not self.path.exists():
            return PlayerState()
        try:
            with self.path.open("r", encoding="utf-8") as source:
                data = json.load(source)
            if not isinstance(data, dict):
                raise ValueError("Progress root must be an object")
            return PlayerState.from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            if self.backup_path.exists():
                try:
                    with self.backup_path.open("r", encoding="utf-8") as source:
                        return PlayerState.from_dict(json.load(source))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    pass
            return PlayerState()

    def save(self, state: PlayerState) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.data_dir / "progress.tmp.json"
        with temporary.open("w", encoding="utf-8") as target:
            json.dump(state.to_dict(), target, ensure_ascii=False, indent=2)
            target.flush()
            os.fsync(target.fileno())
        if self.path.exists():
            self.path.replace(self.backup_path)
        temporary.replace(self.path)
