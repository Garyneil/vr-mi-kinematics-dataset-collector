"""Constrained block randomization for balanced task presentation."""

from __future__ import annotations

import random
from typing import Iterable, List, Sequence


def _valid_prefix(sequence: Sequence[str], max_same_in_row: int) -> bool:
    if len(sequence) < max_same_in_row + 1:
        return True
    tail = sequence[-(max_same_in_row + 1):]
    return len(set(tail)) > 1


def constrained_shuffle(
    tasks: Iterable[str],
    repetitions_per_task: int,
    max_same_in_row: int,
    rng: random.Random,
    max_attempts: int = 10000,
) -> List[str]:
    """Return a balanced randomized task order with a run-length constraint."""
    if repetitions_per_task <= 0:
        raise ValueError("repetitions_per_task must be positive")
    if max_same_in_row <= 0:
        raise ValueError("max_same_in_row must be positive")

    pool = [task for task in tasks for _ in range(repetitions_per_task)]
    if not pool:
        raise ValueError("At least one task is required")

    for _ in range(max_attempts):
        rng.shuffle(pool)
        if all(
            _valid_prefix(pool[: index + 1], max_same_in_row)
            for index in range(len(pool))
        ):
            return list(pool)

    # Deterministic fallback that greedily selects from the most frequent valid task.
    remaining = {task: repetitions_per_task for task in set(pool)}
    sequence: List[str] = []
    while sum(remaining.values()) > 0:
        candidates = [
            task
            for task, count in remaining.items()
            if count > 0 and _valid_prefix(sequence + [task], max_same_in_row)
        ]
        if not candidates:
            raise RuntimeError("Unable to construct a valid randomized sequence")
        rng.shuffle(candidates)
        selected = max(candidates, key=lambda task: remaining[task])
        sequence.append(selected)
        remaining[selected] -= 1
    return sequence
