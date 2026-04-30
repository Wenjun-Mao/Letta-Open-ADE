from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

CSV_FIELDS = [
    "run_id",
    "round",
    "persona_key",
    "persona_label",
    "persona_description",
    "status",
    "elapsed_seconds",
    "content",
    "content_length",
    "finish_reason",
    "content_source",
    "usage_prompt_tokens",
    "usage_completion_tokens",
    "usage_total_tokens",
    "error",
    "model_key",
    "prompt_key",
    "task_shape",
    "max_tokens",
    "timeout_seconds",
    "retry_count",
]


def write_artifacts(
    *,
    csv_path: Path,
    jsonl_path: Path,
    rows: list[dict[str, Any]],
    raw_records: list[dict[str, Any]],
) -> None:
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in raw_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_summary(run_id: str, csv_path: Path, jsonl_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = sum(1 for row in rows if row.get("status") == "ok")
    failures = len(rows) - successes
    slowest = sorted(rows, key=lambda row: float(row.get("elapsed_seconds", 0)), reverse=True)[:5]
    return {
        "run_id": run_id,
        "total_attempts": len(rows),
        "successes": successes,
        "failures": failures,
        "csv_path": str(csv_path),
        "jsonl_path": str(jsonl_path),
        "slowest": [
            {
                "persona_key": row.get("persona_key", ""),
                "round": row.get("round", ""),
                "elapsed_seconds": row.get("elapsed_seconds", 0),
                "status": row.get("status", ""),
            }
            for row in slowest
        ],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"run_id: {summary['run_id']}")
    print(f"attempts: {summary['total_attempts']}  successes: {summary['successes']}  failures: {summary['failures']}")
    print(f"csv: {summary['csv_path']}")
    print(f"jsonl: {summary['jsonl_path']}")
    if summary.get("slowest"):
        print("slowest:")
        for item in summary["slowest"]:
            print(
                f"  {item['persona_key']} round={item['round']} "
                f"elapsed={item['elapsed_seconds']}s status={item['status']}"
            )


def row_id(row: dict[str, Any]) -> str:
    return f"{row['run_id']}::{row['round']}::{row['persona_key']}"
