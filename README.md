# VR 运动想象与动捕运动学数据采集系统

本项目面向论文实验，目标是在统一 VR 场景下完成以下三阶段数据采集：

1. **显式动作执行阶段**：受试者真实完成 `grasp / handover / place / press` 四类任务，同时采集 EEG、ECG、动捕服骨架数据与实验事件。
2. **运动想象阶段**：受试者保持身体静止，在 VR 中根据任务提示进行运动想象，主要采集 EEG、ECG 与事件标记；动捕服可选用于检测无意识动作污染。
3. **闭环评估阶段**：仅使用 EEG 进行在线意图解码，并驱动 VR 或机器人反馈。

本项目对应论文中的核心约束是：

> 动捕运动学只在训练阶段用于构建任务结构先验；在线推理阶段仅使用 EEG。

---

## 一、当前实验室设备基础

当前已知设备包括：

- 8 通道 EEG；
- 4 通道 ECG；
- 动作捕捉服；
- VR 设备；
- NVIDIA Jetson 或 Windows 主机。

由于动捕服品牌、型号、SDK、输出协议、骨架节点名称和采样率暂未最终确认，因此本仓库采用“通用适配器”设计，不预先写死具体厂商接口。

当前支持的接入思路：

- 动捕服通过 UDP、TCP、OSC、CSV 或厂商 SDK 接入；
- VR 通过 Unity、Unreal 或其他程序发送事件标记；
- EEG/ECG 通过串口输入；
- 所有数据通过统一 session、trial 和事件时间轴进行组织。

---

## 二、四类任务

| 类别 | 英文标签 | 任务含义 |
|---|---|---|
| 抓取 | `grasp` | 接近目标并抓住物体 |
| 递交 | `handover` | 持物并向交互对象转移 |
| 放置 | `place` | 将物体移动到目标位置并释放 |
| 按压 | `press` | 接近控制元件并完成局部按压 |

这四类任务不是彼此完全独立的离散标签。它们共享部分上肢运动成分，但在目标、阶段顺序、物体状态变化和终止条件上存在差异，因此适合构建任务运动学关系。

---

## 三、实验阶段设计

### 1. 显式动作执行 `overt_execution`

受试者穿戴 EEG/ECG、动捕服和 VR 设备，真实执行四类任务。

建议同步记录：

- 8 通道 EEG；
- 4 通道 ECG；
- 上肢骨架位置与姿态；
- VR cue；
- 动作开始；
- 接触事件；
- 释放事件；
- 按压事件；
- 动作结束。

显式动作数据用于构建四类任务的运动学原型。

### 2. 运动想象 `motor_imagery`

受试者在 VR 中看到相同任务场景，但保持身体静止，仅进行运动想象。

建议流程：

```text
注视点 -> 任务提示 -> 运动想象 -> 可选反馈 -> 随机间隔
```

动捕服在这一阶段不作为模型输入，而可以用于检测试次是否存在实际动作污染。

### 3. 闭环评估 `closed_loop`

闭环阶段仅使用 EEG：

```text
EEG -> 意图解码 -> VR/机器人反馈
```

运动学数据不参与在线推理。

---

## 四、项目功能

- 8 EEG + 4 ECG 串口采集；
- 四类任务协议；
- 三阶段实验控制；
- block 内受约束随机化；
- 随机试次间隔；
- fixation、cue、execution、imagery、feedback 等事件标记；
- 每个 trial 独立保存；
- 自动生成 session 级 JSON/CSV 元数据；
- 支持 packet counter 与丢包检测；
- 支持 dry-run；
- 预留动捕服、VR 与机器人适配接口；
- 支持 Windows、Ubuntu 和 NVIDIA Jetson。

---

## 五、项目结构

```text
.
├── collect_experiment.py      # 主实验采集程序
├── config.yaml                # 实验与硬件配置
├── protocol.py                # 四类任务与阶段定义
├── randomization.py           # 受约束随机化
├── serial_reader.py           # EEG/ECG 串口读取
├── recorder.py                # trial/session 数据保存
├── event_logger.py            # 实验事件记录
├── adapters/
│   ├── base_mocap.py          # 动捕服统一接口
│   └── generic_udp_mocap.py   # 通用 UDP 动捕适配器
├── requirements.txt
├── .gitignore
└── docs/
    ├── protocol.md
    └── hardware_setup.md
```

---

## 六、快速开始

### 克隆仓库

```bash
git clone https://github.com/Garyneil/vr-mi-kinematics-dataset-collector.git
cd vr-mi-kinematics-dataset-collector
python -m venv .venv
```

### Ubuntu / Jetson

```bash
source .venv/bin/activate
pip install -r requirements.txt
python collect_experiment.py --subject sub001 --stage motor_imagery --dry-run
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python collect_experiment.py --subject sub001 --stage motor_imagery --dry-run
```

### 正式采集

```bash
python collect_experiment.py --subject sub001 --stage overt_execution
python collect_experiment.py --subject sub001 --stage motor_imagery
python collect_experiment.py --subject sub001 --stage closed_loop
```

---

## 七、动捕服接入说明

当前默认配置：

```yaml
mocap:
  enabled: false
  adapter: "none"
```

在确认动捕服具体参数后，可改为：

```yaml
mocap:
  enabled: true
  adapter: "generic_udp"
  host: "0.0.0.0"
  port: 7001
  sampling_rate_hz: 60.0
```

后续还需要确认：

- 动捕服品牌和型号；
- 是否支持实时 SDK；
- 输出方式；
- 骨架节点名称；
- 位置和姿态单位；
- 坐标系定义；
- 采样率；
- 动捕时间戳来源；
- 与 VR 是否已经共享时钟。

在这些参数明确之前，仓库不会虚构具体设备字段。

---

## 八、串口帧模式

当前支持：

- `legacy26`：`header + 12 x int16 + tail`
- `counter30`：`header + uint32 packet_id + 12 x int16 + tail`

正式论文采集建议使用带 `packet_id` 的帧结构，以便检测丢包。若固件允许，后续还应增加设备时间戳和 CRC。

---

## 九、数据目录

```text
data/raw/sub001/session_YYYYMMDD_HHMMSS/
├── trial_0001_overt_execution_grasp_signals.csv
├── trial_0001_events.csv
├── trial_0001_kinematics.csv
├── metadata.csv
├── metadata.json
└── config_snapshot.yaml
```

运动想象阶段若启用动捕服进行静止检测，也可以保存对应的 `kinematics.csv`，但这些数据只用于质量控制，不作为 EEG 解码输入。

---

## 十、科研表述边界

本项目不声称低通道 EEG 能直接恢复完整的内在神经流形。动捕服获得的上肢运动学被视为可观测的行为几何，用于引导 EEG 表征学习。

当前仓库已经提供实验流程、串口采集、事件记录、数据管理和通用硬件适配框架。动捕服与 VR 的最终实时接入需要在设备品牌、SDK 和输出协议明确后完成。