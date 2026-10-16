from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .model import (
    Project,
    component_to_dict,
    constraint_to_dict,
    decision_to_dict,
    parameter_to_dict,
    relation_to_dict,
    requirement_to_dict,
    test_result_to_dict,
    unknown_to_dict,
)

_REGISTRIES = (
    "params",
    "relations",
    "constraints",
    "requirements",
    "decisions",
    "unknowns",
    "components",
    "test_results",
)
_KIND_NAMES = {
    "params": "parameter",
    "relations": "relation",
    "constraints": "constraint",
    "requirements": "requirement",
    "decisions": "decision",
    "unknowns": "unknown",
    "components": "component",
    "test_results": "test_result",
}
_SERIALIZERS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "Parameter": parameter_to_dict,
    "Relation": relation_to_dict,
    "Constraint": constraint_to_dict,
    "Requirement": requirement_to_dict,
    "Decision": decision_to_dict,
    "Unknown": unknown_to_dict,
    "TestResult": test_result_to_dict,
    "Component": component_to_dict,
}


def structural_diff(base: Project, target: Project) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for registry in _REGISTRIES:
        kind = _KIND_NAMES[registry]
        before = getattr(base, registry)
        after = getattr(target, registry)

        for node_id in sorted(set(after) - set(before)):
            ops.append({"op": "added", "kind": kind, "id": node_id, "after": _snapshot(after[node_id])})
        for node_id in sorted(set(before) - set(after)):
            ops.append({"op": "removed", "kind": kind, "id": node_id, "before": _snapshot(before[node_id])})
        for node_id in sorted(set(after) & set(before)):
            old = _snapshot(before[node_id])
            new = _snapshot(after[node_id])
            if old != new:
                ops.append({"op": "updated", "kind": kind, "id": node_id, "before": old, "after": new})
    return ops


def _snapshot(node: Any) -> dict[str, Any]:
    return _SERIALIZERS[type(node).__name__](node)
