from __future__ import annotations

import copy
from typing import Any

from ..graph.model import Project
from .solve import run


def sweep(project: Project, parameter_id: str, start: float, stop: float, steps: int) -> list[dict[str, Any]]:
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if parameter_id not in project.params:
        raise ValueError(f"unknown parameter {parameter_id!r}")
    records: list[dict[str, Any]] = []
    for index in range(steps + 1):
        value = start + (stop - start) * index / steps
        candidate = copy.deepcopy(project)
        candidate.params[parameter_id].value = value
        result = run(candidate)
        records.append(
            {
                "swept_value": value,
                "values": dict(result.values),
                "unsolved": dict(result.unsolved),
            }
        )
    return records
