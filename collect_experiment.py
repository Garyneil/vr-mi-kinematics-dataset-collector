"""Run overt-execution, motor-imagery, or closed-loop acquisition sessions."""

from __future__ import annotations

import argparse
import random
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

from event_logger import EventLogger
from protocol import get_task, get_tasks, validate_stage
from randomization import constrained_shuffle
from recorder import SessionRecorder
from serial_reader import SerialSignalReader, SignalSample


def load_config(path: str) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise ValueError("Config root must be a YAML mapping")
    for key in ("runtime", "hardware", "protocol", "stages"):
        if key not in config:
            raise ValueError(f"Missing required config section: {key}")
    return config


def wait_with_countdown(message: str, seconds: float, dry_run: bool) -> None:
    print(message)
    if dry_run:
        time.sleep(min(float(seconds), 0.05))
        return
    deadline = time.monotonic() + float(seconds)
    last_value = None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        value = int(remaining + 0.999)
        if value != last_value:
            print(f"  {value:02d}s remaining", end="\r", flush=True)
            last_value = value
        time.sleep(0.02)
    print(" " * 30, end="\r")


def collect_samples(
    reader: SerialSignalReader,
    duration_sec: float,
    dry_run: bool,
    nominal_fs: float,
) -> List[SignalSample]:
    if dry_run:
        count = max(1, int(round(duration_sec * nominal_fs)))
        return [
            SignalSample(
                host_timestamp=index / nominal_fs,
                packet_id=index,
                dropped_before=0,
                eeg=[0.0] * 8,
                ecg=[0.0] * 4,
            )
            for index in range(count)
        ]

    samples: List[SignalSample] = []
    deadline = time.monotonic() + float(duration_sec)
    while time.monotonic() < deadline:
        samples.append(reader.read_sample())
    return samples


def stage_active_label(stage: str) -> str:
    if stage == "overt_execution":
        return "execution"
    if stage == "motor_imagery":
        return "imagery"
    return "decoding_window"


def print_instruction(stage: str, task_name: str) -> None:
    task = get_task(task_name)
    if stage == "overt_execution":
        print(f"ACTION: {task.display_name} | {task.instruction_execution}")
    elif stage == "motor_imagery":
        print(f"IMAGINE: {task.display_name} | {task.instruction_imagery}")
    else:
        print(f"CLOSED LOOP: Imagine {task.display_name}; decoder output will trigger feedback.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VR task-oriented motor-imagery and kinematics dataset collector"
    )
    parser.add_argument("--subject", required=True, help="Subject ID, e.g. sub001")
    parser.add_argument(
        "--stage",
        required=True,
        choices=("overt_execution", "motor_imagery", "closed_loop"),
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--blocks", type=int, default=None)
    args = parser.parse_args()

    stage = validate_stage(args.stage)
    config = load_config(args.config)
    runtime_cfg = config["runtime"]
    serial_cfg = runtime_cfg["serial"]
    protocol_cfg = config["protocol"]
    hardware_cfg = config["hardware"]
    qc_cfg = config.get("quality_control", {})

    blocks = args.blocks or int(protocol_cfg["blocks"])
    repetitions = int(protocol_cfg["trials_per_task_per_block"])
    base_seed = int(runtime_cfg.get("random_seed", 42))
    session_seed = base_seed + sum(ord(character) for character in args.subject) + blocks
    rng = random.Random(session_seed)

    recorder = SessionRecorder(
        root_dir=runtime_cfg["output_dir"],
        subject_id=args.subject,
        stage=stage,
        config=config,
    )
    event_logger = EventLogger(recorder.session_dir / "events.csv", stage=stage)

    eeg_names = list(hardware_cfg["eeg_channel_names"])
    ecg_names = list(hardware_cfg["ecg_channel_names"])
    nominal_fs = float(serial_cfg["sampling_rate_hz"])

    reader = None
    if not args.dry_run:
        reader = SerialSignalReader(**serial_cfg)

    event_logger.emit("session_start", value=recorder.session_id, payload={"seed": session_seed})
    print(f"Session: {recorder.session_id}")
    print(f"Stage: {stage}")
    print(f"Dry run: {args.dry_run}")

    try:
        wait_with_countdown("Relax and keep still. Baseline starts now.", 1.0, args.dry_run)
        event_logger.emit("baseline_onset")
        baseline_samples = collect_samples(
            reader,
            float(protocol_cfg["baseline_duration_sec"]),
            args.dry_run,
            nominal_fs,
        )
        event_logger.emit("baseline_offset")
        baseline_path = recorder.session_dir / "baseline_signals.csv"
        baseline_stats = recorder.write_signals(
            baseline_path,
            baseline_samples,
            eeg_names,
            ecg_names,
        )

        trial_id = 1
        task_names = [task.name for task in get_tasks()]
        for block_id in range(1, blocks + 1):
            order = constrained_shuffle(
                task_names,
                repetitions_per_task=repetitions,
                max_same_in_row=int(protocol_cfg["max_same_task_in_row"]),
                rng=rng,
            )
            event_logger.emit(
                "block_start",
                block_id=block_id,
                payload={"task_order": order},
            )

            for task_name in order:
                task = get_task(task_name)
                iti = rng.uniform(
                    float(protocol_cfg["iti_min_sec"]),
                    float(protocol_cfg["iti_max_sec"]),
                )

                event_logger.emit(
                    "trial_start",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                    payload={"iti_sec": iti},
                )

                event_logger.emit(
                    "fixation_onset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )
                wait_with_countdown("Fixation: keep still and look at the center.", float(protocol_cfg["fixation_duration_sec"]), args.dry_run)
                event_logger.emit(
                    "fixation_offset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )

                event_logger.emit(
                    "cue_onset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                    value=task.display_name,
                    payload={
                        "task_id": task.task_id,
                        "object_state_transition": task.object_state_transition,
                    },
                )
                print_instruction(stage, task_name)
                wait_with_countdown("Task cue", float(protocol_cfg["cue_duration_sec"]), args.dry_run)
                event_logger.emit(
                    "cue_offset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )

                active_duration = float(
                    protocol_cfg[
                        "execution_duration_sec"
                        if stage == "overt_execution"
                        else "imagery_duration_sec"
                    ]
                )
                active_event = stage_active_label(stage)
                event_logger.emit(
                    f"{active_event}_onset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )
                samples = collect_samples(reader, active_duration, args.dry_run, nominal_fs)
                event_logger.emit(
                    f"{active_event}_offset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )

                signal_path = recorder.trial_signal_path(trial_id, stage, task_name)
                stats = recorder.write_signals(signal_path, samples, eeg_names, ecg_names)
                expected_samples = int(round(active_duration * nominal_fs))
                sample_error_ratio = abs(stats["sample_count"] - expected_samples) / max(expected_samples, 1)
                packet_loss_ratio = stats["dropped_packets"] / max(
                    stats["sample_count"] + stats["dropped_packets"], 1
                )
                valid = sample_error_ratio <= float(qc_cfg.get("expected_sampling_tolerance", 0.08))
                if bool(qc_cfg.get("reject_on_packet_loss", False)):
                    valid = valid and packet_loss_ratio <= float(
                        qc_cfg.get("maximum_packet_loss_ratio", 0.01)
                    )

                if bool(config["stages"][stage].get("enable_feedback", False)):
                    event_logger.emit(
                        "feedback_onset",
                        trial_id=trial_id,
                        block_id=block_id,
                        task_name=task_name,
                        value="adapter_pending",
                    )
                    wait_with_countdown("VR/robot feedback adapter placeholder", float(protocol_cfg["feedback_duration_sec"]), args.dry_run)
                    event_logger.emit(
                        "feedback_offset",
                        trial_id=trial_id,
                        block_id=block_id,
                        task_name=task_name,
                    )

                event_logger.emit(
                    "trial_end",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                    payload={"valid": valid},
                )
                recorder.add_trial_metadata(
                    {
                        "subject_id": args.subject,
                        "session_id": recorder.session_id,
                        "stage": stage,
                        "block_id": block_id,
                        "trial_id": trial_id,
                        "task_id": task.task_id,
                        "task_name": task_name,
                        "object_state_transition": task.object_state_transition,
                        "iti_sec": round(iti, 6),
                        "active_duration_sec": active_duration,
                        "expected_samples": expected_samples,
                        "actual_samples": stats["sample_count"],
                        "dropped_packets": stats["dropped_packets"],
                        "packet_loss_ratio": packet_loss_ratio,
                        "sample_error_ratio": sample_error_ratio,
                        "trial_valid": valid,
                        "signal_file": signal_path.name,
                        "kinematics_required": bool(config["stages"][stage].get("record_kinematics", False)),
                    }
                )

                event_logger.emit(
                    "iti_onset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )
                wait_with_countdown("Rest", iti, args.dry_run)
                event_logger.emit(
                    "iti_offset",
                    trial_id=trial_id,
                    block_id=block_id,
                    task_name=task_name,
                )
                trial_id += 1

            event_logger.emit("block_end", block_id=block_id)
            if block_id < blocks:
                wait_with_countdown(
                    "Block complete. Please rest.",
                    float(protocol_cfg["block_break_sec"]),
                    args.dry_run,
                )

        event_logger.emit("session_end")
        event_logger.flush()
        session_dir = recorder.finalize(
            extra={
                "random_seed": session_seed,
                "baseline_file": baseline_path.name,
                "baseline_stats": baseline_stats,
                "event_file": "events.csv",
                "dry_run": args.dry_run,
            }
        )
        print(f"Session saved to: {session_dir}")
    finally:
        if reader is not None:
            reader.close()


if __name__ == "__main__":
    main()
