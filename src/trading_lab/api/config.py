from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApiConfig:
    project_root: Path
    frontend_origin: str = "http://localhost:5173"

    @property
    def output_root(self) -> Path:
        return (self.project_root / "output").resolve()

    @property
    def docs_root(self) -> Path:
        return (self.project_root / "docs").resolve()


def default_config() -> ApiConfig:
    return ApiConfig(Path(__file__).resolve().parents[3])
