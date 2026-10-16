from __future__ import annotations

import re
from enum import StrEnum


class IdKind(StrEnum):
    COMPONENT = "component"
    PARAMETER = "parameter"
    RELATION = "relation"
    CONSTRAINT = "constraint"
    REQUIREMENT = "requirement"
    DECISION = "decision"
    UNKNOWN = "unknown"
    TEST_RESULT = "test_result"


_COMPONENT = r"cmp\.[a-z0-9]+(?:-[a-z0-9]+)*"
_PARAMETER = rf"{_COMPONENT}#[a-z][a-z0-9_-]*"
_SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"

_KIND_PATTERNS: tuple[tuple[IdKind, re.Pattern[str]], ...] = (
    (IdKind.PARAMETER, re.compile(rf"^{_PARAMETER}$")),
    (IdKind.COMPONENT, re.compile(rf"^{_COMPONENT}$")),
    (IdKind.RELATION, re.compile(rf"^rl\.{_SLUG}$")),
    (IdKind.CONSTRAINT, re.compile(rf"^cs\.{_SLUG}$")),
    (IdKind.REQUIREMENT, re.compile(rf"^rq\.{_SLUG}$")),
    (IdKind.DECISION, re.compile(rf"^dc\.{_SLUG}$")),
    (IdKind.UNKNOWN, re.compile(rf"^uk\.{_SLUG}$")),
    (IdKind.TEST_RESULT, re.compile(rf"^tr\.{_SLUG}$")),
)


def kind_of(node_id: str) -> IdKind:
    for kind, pattern in _KIND_PATTERNS:
        if pattern.match(node_id):
            return kind
    raise ValueError(f"malformed id: {node_id!r}")


def component_id_of_parameter(parameter_id: str) -> str:
    head, sep, _ = parameter_id.partition("#")
    if not sep:
        raise ValueError(f"not a parameter id: {parameter_id!r}")
    return head


def is_kind(node_id: str, kind: IdKind) -> bool:
    try:
        return kind_of(node_id) == kind
    except ValueError:
        return False


def validate_id(node_id: str, kind: IdKind) -> None:
    if not is_kind(node_id, kind):
        raise ValueError(f"id {node_id!r} is not a valid {kind.value} id")
