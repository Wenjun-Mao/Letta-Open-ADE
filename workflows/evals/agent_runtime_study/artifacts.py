from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def json_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_value(item) for item in value]
    return value


class StudyArtifactWriter:
    def __init__(self, output_dir: Path, run_id: str) -> None:
        self.run_dir = output_dir / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.turns_path = self.run_dir / "turns.jsonl"
        self.summary_path = self.run_dir / "summary.json"
        self.provenance_path = self.run_dir / "provenance.json"
        self.retrieval_path = self.run_dir / "retrieval.json"
        self.qualification_path = self.run_dir / "qualification.json"
        self._turns = self.turns_path.open("w", encoding="utf-8", newline="\n")

    def write_turn(self, payload: dict[str, Any]) -> None:
        self._turns.write(
            json.dumps(json_value(payload), ensure_ascii=False, sort_keys=True) + "\n"
        )
        self._turns.flush()

    def write_summary(self, payload: dict[str, Any]) -> None:
        self.summary_path.write_text(
            json.dumps(
                json_value(payload), ensure_ascii=False, indent=2, sort_keys=True
            ),
            encoding="utf-8",
        )

    def write_provenance(self, payload: dict[str, Any]) -> None:
        self.provenance_path.write_text(
            json.dumps(
                json_value(payload), ensure_ascii=False, indent=2, sort_keys=True
            ),
            encoding="utf-8",
        )

    def write_retrieval(self, payload: dict[str, Any]) -> None:
        self._write_json(self.retrieval_path, payload)

    def write_qualification(self, payload: dict[str, Any]) -> None:
        self._write_json(self.qualification_path, payload)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(
                json_value(payload), ensure_ascii=False, indent=2, sort_keys=True
            ),
            encoding="utf-8",
        )

    def close(self) -> None:
        self._turns.close()

    def __enter__(self) -> "StudyArtifactWriter":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
