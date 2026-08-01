# Experimental Protocol

## 1. Scientific objective

The protocol supports task-oriented motor-imagery research in VR-based human--robot interaction. Four manipulation intentions are studied:

- `grasp`
- `handover`
- `place`
- `press`

The classes are not assumed to be equally distant. Their shared and task-specific movement structure is captured during overt execution and may later be used as a training-time geometric prior for EEG representation learning.

## 2. Experimental stages

### Stage A: overt execution

Participants physically perform each task. The system records EEG, ECG, event markers, and task kinematics. Recommended external kinematic events include:

- movement onset
- first contact
- object closure or press onset
- release
- movement offset

The overt-execution data are used to construct task-level kinematic prototypes. They must not be passed to the model during online EEG-only inference.

### Stage B: motor imagery

Participants view a standardized VR cue and imagine the cued task without overt movement. The default trial is:

```text
fixation (2 s)
-> task cue (1 s)
-> motor imagery (4 s)
-> randomized ITI (2.0--3.5 s)
```

The experimenter should monitor overt movement and mark contaminated trials invalid.

### Stage C: closed-loop evaluation

Only EEG is supplied to the decoder. The predicted task triggers VR or robot feedback. Kinematics are unavailable to the decoder at inference time.

## 3. Block structure

The default configuration uses:

```text
6 blocks x 10 trials/task/block x 4 tasks = 240 trials/stage/participant
```

Each block contains an equal number of trials from every task. Trial order is randomized with a maximum of two identical tasks in succession. The actual sequence and random seed are saved for reproducibility.

## 4. Timing and event markers

The event log records at least:

- `session_start`
- `baseline_onset`, `baseline_offset`
- `block_start`, `block_end`
- `trial_start`, `trial_end`
- `fixation_onset`, `fixation_offset`
- `cue_onset`, `cue_offset`
- `execution_onset`, `execution_offset`
- `imagery_onset`, `imagery_offset`
- `decoding_window_onset`, `decoding_window_offset`
- `feedback_onset`, `feedback_offset`
- `iti_onset`, `iti_offset`
- `session_end`

Laboratory-specific VR, robot, and motion-capture software should emit additional markers through the same event interface or through a synchronized external stream.

## 5. Signal integrity

The preferred serial format is `counter30`, which includes a 32-bit packet counter. The software detects discontinuities and records dropped packets per trial. The legacy 26-byte frame remains supported for compatibility but cannot localize packet loss reliably.

A device-side timestamp and CRC should be added to the firmware when precise EEG--kinematics synchronization is required.

## 6. Required hardware documentation

Before publication, replace all `TBD` fields with verified laboratory specifications:

- EEG electrode locations
- reference and ground electrodes
- electrode type
- impedance threshold
- amplifier and ADC model
- ADC resolution and input range
- hardware gain
- hardware filters
- physical signal units
- ECG lead configuration
- electrical isolation
- VR headset and refresh rate
- kinematic sensor and sampling rate
- robot platform
- synchronization mechanism

## 7. Data-quality rules

A trial should be reviewed or rejected when one or more of the following occur:

- overt movement during motor imagery
- cue or feedback timing failure
- excessive packet loss
- implausible sample count
- electrode detachment
- severe motion or muscle artifact
- incomplete kinematic recording during overt execution

The raw data should remain unchanged. Trial validity and rejection reasons should be stored in metadata rather than implemented by deleting files.
