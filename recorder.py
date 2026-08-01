"""Session-level metadata and trial-level physiological signal recording."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from serial_reader import SignalSample


class SessionRecorder:
    def __init__(
        self,
        root_dir: str,
        subject_id: str,
        stage: str,
        config: Dict[str, Any],
    ) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.subject_id = subject_id
        self.stage = stage
        self.session_id = f"session_{timestamp}_{stage}"
        self.session_dir = Path(root_dir) / subject_id / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=False)
        self.config = config
        self.trial_rows: List[Dict[str, Any]] = []

        with (self.session_dir / "config_snapshot.yaml").open("w", encoding="utf-8") as file:
            yaml.safe_dump(config, file, allow_unicode=True, sort_keys=False)

    def trial_signal_path(self, trial_id: int, stage: str, task_name: str) -> Path:
        return self.session_dir / f"trial_{trial_id:04d}_{stage}_{task_name}_signals.csv"

    def write_signals(
        self,
        path: Path,
        samples: Iterable[SignalSample],
        eeg_names: List[str],
        ecg_names: List[str],
    ) -> Dict[str, int]:
        fieldnames = [
            "host_timestamp",
            "packet_id",
            "dropped_before",
            *eeg_names,
            *ecg_names,
        ]
        sample_count = 0
        dropped_packets = 0
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for sample in samples:
                row: Dict[str, Any] = {
                    "host_timestamp": f"{sample.host_timestamp:.9f}",
                    "packet_id": "" if sample.packet_id is None else sample.packet_id,
                    "dropped_before": sample.dropped_before,
                }
                row.update(dict(zip(eeg_names, sample.eeg)))
                row.update(dict(zip(ecg_names, sample.ecg)))
                writer.writerow(row)
                sample_count += 1
                dropped_packets += sample.dropped_before
        return {"sample_count": sample_count, "dropped_packets": dropped_packets}

    def add_trial_metadata(self, row: Dict[str, Any]) -> None:
        self.trial_rows.append(row)

    def finalize(self, extra: Optional[Dict[str, Any]] = None) -> Path:
        metadata_csv = self.session_dir / "metadata.csv"
        if self.trial_rows:
            keys: List[str] = []
            for row in self.trial_rows:
                for key in row:
                    if key not in keys:
                        keys.append(key)
            with metadata_csv.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.trial_rows)

        payload = {
            "subject_id": self.subject_id,
            "session_id": self.session_id,
            "stage": self.stage,
            "trial_count": len(self.trial_rows),
            "session_dir": str(self.session_dir.resolve()),
            "trials": self.trial_rows,
            "extra": extra or {},
        }
        with (self.session_dir / "metadata.json").open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
        return self.session_dir
