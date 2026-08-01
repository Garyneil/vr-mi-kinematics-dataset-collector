"""Experiment task and stage definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class TaskDefinition:
    task_id: int
    name: str
    display_name: str
    instruction_execution: str
    instruction_imagery: str
    object_state_transition: str


TASKS: Tuple[TaskDefinition, ...] = (
    TaskDefinition(
        1,
        "grasp",
        "Grasp",
        "Reach toward the object, grasp it, and stabilize it.",
        "Imagine reaching toward the object, grasping it, and stabilizing it without moving.",
        "free_to_held",
    ),
    TaskDefinition(
        2,
        "handover",
        "Handover",
        "Transport the held object toward the partner and stabilize at the transfer position.",
        "Imagine transporting the held object toward the partner and stabilizing it at the transfer position without moving.",
        "held_to_held",
    ),
    TaskDefinition(
        3,
        "place",
        "Place",
        "Transport the held object to the target, make contact, and release it.",
        "Imagine transporting the held object to the target, making contact, and releasing it without moving.",
        "held_to_free",
    ),
    TaskDefinition(
        4,
        "press",
        "Press",
        "Reach toward the control, press it, and retract the hand.",
        "Imagine reaching toward the control, pressing it, and retracting the hand without moving.",
        "no_held_object_transition",
    ),
)

TASK_BY_NAME: Dict[str, TaskDefinition] = {task.name: task for task in TASKS}

VALID_STAGES = ("overt_execution", "motor_imagery", "closed_loop")


def get_tasks() -> Tuple[TaskDefinition, ...]:
    return TASKS


def get_task(name: str) -> TaskDefinition:
    try:
        return TASK_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Unknown task: {name}") from exc


def validate_stage(stage: str) -> str:
    if stage not in VALID_STAGES:
        raise ValueError(f"Unknown stage '{stage}'. Expected one of: {VALID_STAGES}")
    return stage
