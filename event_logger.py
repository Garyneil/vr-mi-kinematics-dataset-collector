"""Event logging for experiment stages and external integrations."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EventRecord:
    host_time_monotonic: float
    event_name: str
    trial_id: Optional[int]
    block_id: Optional[int]
    task_name: Optional[str]
    stage: str
    value: Optional[str]
    payload_json: str


class EventLogger:
    def __init__(self, output_path: Path, stage: str) -> None:
        self.output_path = output_path
        self.stage = stage
        self._t0 = time.monotonic()
        self._records: List[EventRecord] = []

    def emit(
        self,
        event_name: str,
        *,
        trial_id: Optional[int] = None,
        block_id: Optional[int] = None,
        task_name: Optional[str] = None,
        value: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EventRecord:
        record = EventRecord(
            host_time_monotonic=time.monotonic() - self._t0,
            event_name=event_name,
            trial_id=trial_id,
            block_id=block_id,
            task_name=task_name,
            stage=self.stage,
            value=value,
            payload_json=json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
        )
        self._records.append(record)
        return record

    def flush(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(asdict(self._records[0]).keys()) if self._records else [
            "host_time_monotonic",
            "event_name",
            "trial_id",
            "block_id",
            "task_name",
            "stage",
            "value",
            "payload_json",
        ]
        with self.output_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for record in self._records:
                writer.writerow(asdict(record))

    @property
    def records(self) -> List[EventRecord]:
        return list(self._records)
