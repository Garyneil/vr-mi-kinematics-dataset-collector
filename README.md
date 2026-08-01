# VR-MI Kinematics Dataset Collector

A research-oriented acquisition framework for synchronized **8-channel EEG**, **4-channel ECG**, task events, VR cues, robot feedback, and overt-execution kinematics.

本项目面向论文实验：在统一 VR 范式下采集 `grasp / handover / place / press` 四类任务的显式执行数据、运动想象数据与闭环评估数据。运动学只在训练阶段用于构建任务结构先验；闭环推理阶段仅使用 EEG。

## Experimental stages

1. `overt_execution`: real action execution with synchronized physiology and kinematics.
2. `motor_imagery`: VR-cued motor imagery without overt movement.
3. `closed_loop`: EEG-only decoding followed by VR/robot feedback.

## Core design

- 8 EEG + 4 ECG serial acquisition at a nominal 250 Hz
- four robot-relevant tasks: grasp, handover, place, press
- block-wise constrained randomization
- randomized inter-trial interval
- explicit event markers for fixation, cue, imagery/action, feedback, and trial end
- trial-level CSV files and session-level JSON/CSV metadata
- packet counter support and dropped-packet detection
- dry-run mode for validating the full protocol without hardware
- Windows, Ubuntu, and NVIDIA Jetson compatible

## Repository structure

```text
.
├── collect_experiment.py
├── config.yaml
├── protocol.py
├── randomization.py
├── serial_reader.py
├── recorder.py
├── event_logger.py
├── requirements.txt
├── .gitignore
└── docs/
    └── protocol.md
```

## Quick start

```bash
git clone https://github.com/Garyneil/vr-mi-kinematics-dataset-collector.git
cd vr-mi-kinematics-dataset-collector
python -m venv .venv
```

Ubuntu / Jetson:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python collect_experiment.py --subject sub001 --stage motor_imagery --dry-run
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python collect_experiment.py --subject sub001 --stage motor_imagery --dry-run
```

Formal acquisition:

```bash
python collect_experiment.py --subject sub001 --stage overt_execution
python collect_experiment.py --subject sub001 --stage motor_imagery
python collect_experiment.py --subject sub001 --stage closed_loop
```

## Important hardware note

The parser supports two serial-frame modes:

- `legacy26`: `header + 12 x int16 + tail`
- `counter30`: `header + uint32 packet_id + 12 x int16 + tail`

For publication-grade synchronization, use `counter30` or extend the firmware with a device timestamp and CRC. Host receive timestamps alone are not sufficient for precise EEG--kinematics alignment.

## Data layout

```text
data/raw/sub001/session_YYYYMMDD_HHMMSS/
├── trial_0001_motor_imagery_grasp_signals.csv
├── trial_0001_events.csv
├── trial_0001_kinematics.csv        # overt execution only, when available
├── metadata.csv
├── metadata.json
└── config_snapshot.yaml
```

## Scientific constraint

The project does **not** assume that low-density EEG directly recovers the complete intrinsic neural manifold. Kinematics are treated as an observable behavioral geometry that provides training-time structure for EEG representation learning.

## Status

This repository provides the acquisition and protocol-control layer. VR rendering, robot control, and motion-capture adapters are exposed through event/kinematics interfaces and should be connected to the laboratory-specific hardware.
