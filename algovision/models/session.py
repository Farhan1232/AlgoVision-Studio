"""Session save / load (PRD 7.9).

Sessions are stored locally as JSON - no cloud, accounts, or database.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .. import __version__


@dataclass
class Session:
    algorithm: str
    dataset: list[int]
    array_size: int
    speed: float
    theme: str
    mode: str = "single"
    compare_algorithm: str = "selection"
    app_version: str = __version__

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            algorithm=data.get("algorithm", "bubble"),
            dataset=list(data.get("dataset", [])),
            array_size=int(data.get("array_size", len(data.get("dataset", [])) or 15)),
            speed=float(data.get("speed", 1.0)),
            theme=data.get("theme", "dark"),
            mode=data.get("mode", "single"),
            compare_algorithm=data.get("compare_algorithm", "selection"),
            app_version=data.get("app_version", "unknown"),
        )


def save_session(session: Session, path: str | Path) -> None:
    Path(path).write_text(session.to_json(), encoding="utf-8")


def load_session(path: str | Path) -> Session:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Session.from_dict(data)
