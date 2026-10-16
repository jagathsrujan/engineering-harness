from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .provenance import Provenance, SourceRef, Tag
from .review import Review

NODE_KINDS = ("parameter", "relation", "constraint", "requirement", "decision", "unknown", "test_result")


class GraphError(Exception):
    pass


@dataclass(slots=True)
class Port:
    id: str
    role: str
    unit: str
    pair: str | None = None
    description: str = ""


@dataclass(slots=True)
class Component:
    id: str
    name: str
    description: str = ""
    ports: list[Port] = field(default_factory=list)


@dataclass(slots=True)
class Parameter:
    id: str
    symbol: str
    unit: str
    owner: str
    value: float | None = None
    description: str = ""
    provenance: Provenance | None = None


@dataclass(slots=True)
class Relation:
    id: str
    declarer: str
    params: list[str]
    equations: list[str]
    valid_domain: dict[str, list[float]] = field(default_factory=dict)
    source: SourceRef | None = None
    review: Review = field(default_factory=Review)
    rationale: str = ""
    rationale_by: str | None = None
    description: str = ""


@dataclass(slots=True)
class Constraint:
    id: str
    declarer: str
    expression: str
    params: list[str]
    severity: str = "error"
    source: SourceRef | None = None
    review: Review = field(default_factory=Review)
    description: str = ""


@dataclass(slots=True)
class Requirement:
    id: str
    declarer: str
    condition: str
    params: list[str]
    owner: str = ""
    rationale: str = ""
    mode: str = "required"
    source: SourceRef | None = None
    review: Review = field(default_factory=Review)
    description: str = ""


@dataclass(slots=True)
class Decision:
    id: str
    declarer: str
    options: list[str]
    chosen: str
    question: str = ""
    reason: str = ""
    activates: list[str] = field(default_factory=list)
    deactivates: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(slots=True)
class Unknown:
    id: str
    declarer: str
    description: str
    blocks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TestResult:
    id: str
    declarer: str
    param: str
    value: float
    unit: str
    provenance: Provenance | None = None
    note: str = ""
    method: str = ""
    recorded: str = ""
    recalibrates: str | None = None


@dataclass(slots=True)
class Project:
    id: str
    name: str
    root: Path
    components: dict[str, Component] = field(default_factory=dict)
    params: dict[str, Parameter] = field(default_factory=dict)
    relations: dict[str, Relation] = field(default_factory=dict)
    constraints: dict[str, Constraint] = field(default_factory=dict)
    requirements: dict[str, Requirement] = field(default_factory=dict)
    decisions: dict[str, Decision] = field(default_factory=dict)
    unknowns: dict[str, Unknown] = field(default_factory=dict)
    test_results: dict[str, TestResult] = field(default_factory=dict)
    component_files: dict[str, Path] = field(default_factory=dict)
    settings: dict[str, Any] = field(default_factory=dict)

    def total_nodes(self) -> int:
        return (
            len(self.components)
            + len(self.params)
            + len(self.relations)
            + len(self.constraints)
            + len(self.requirements)
            + len(self.decisions)
            + len(self.unknowns)
            + len(self.test_results)
        )


def _require(d: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise GraphError(f"{ctx}: missing required key {key!r}")
    return d[key]


def _str(value: Any) -> str:
    return str(value)


def component_from_dict(d: dict[str, Any]) -> Component:
    ports = [_port_from_dict(p) for p in d.get("ports", [])]
    return Component(
        id=_str(_require(d, "id", "component")),
        name=_str(d.get("name", d["id"])),
        description=_str(d.get("description", "")),
        ports=ports,
    )


def _port_from_dict(d: dict[str, Any]) -> Port:
    return Port(
        id=_str(_require(d, "id", "port")),
        role=_str(d.get("role", "potential")),
        unit=_str(d.get("unit", "")),
        pair=d.get("pair"),
        description=_str(d.get("description", "")),
    )


def parameter_from_dict(d: dict[str, Any], owner: str) -> Parameter:
    provenance = d.get("provenance")
    return Parameter(
        id=_str(_require(d, "id", "parameter")),
        symbol=_str(_require(d, "symbol", "parameter")),
        unit=_str(d.get("unit", "")),
        owner=owner,
        value=float(d["value"]) if d.get("value") is not None else None,
        description=_str(d.get("description", "")),
        provenance=None if provenance is None else _provenance(provenance),
    )


def _provenance(d: dict[str, Any] | str) -> Provenance:
    if isinstance(d, str):
        return Provenance(tag=Tag(d))
    return Provenance.from_dict(d)


def relation_from_dict(d: dict[str, Any], declarer: str) -> Relation:
    params = [str(p) for p in _require(d, "params", "relation")]
    equations = [str(e) for e in _require(d, "equations", "relation")]
    return Relation(
        id=_str(_require(d, "id", "relation")),
        declarer=declarer,
        params=params,
        equations=equations,
        valid_domain=_domain(d.get("valid_domain")),
        source=_source(d.get("source")),
        review=_review(d.get("review")),
        rationale=_str(d.get("rationale", "")),
        rationale_by=d.get("rationale_by"),
        description=_str(d.get("description", "")),
    )


def constraint_from_dict(d: dict[str, Any], declarer: str) -> Constraint:
    return Constraint(
        id=_str(_require(d, "id", "constraint")),
        declarer=declarer,
        expression=_str(_require(d, "expression", "constraint")),
        params=[str(p) for p in d.get("params", [])],
        severity=_str(d.get("severity", "error")),
        source=_source(d.get("source")),
        review=_review(d.get("review")),
        description=_str(d.get("description", "")),
    )


def requirement_from_dict(d: dict[str, Any], declarer: str) -> Requirement:
    return Requirement(
        id=_str(_require(d, "id", "requirement")),
        declarer=declarer,
        condition=_str(_require(d, "condition", "requirement")),
        params=[str(p) for p in d.get("params", [])],
        owner=_str(d.get("owner", "")),
        rationale=_str(d.get("rationale", "")),
        mode=_str(d.get("mode", "required")),
        source=_source(d.get("source")),
        review=_review(d.get("review")),
        description=_str(d.get("description", "")),
    )


def decision_from_dict(d: dict[str, Any], declarer: str) -> Decision:
    return Decision(
        id=_str(_require(d, "id", "decision")),
        declarer=declarer,
        options=[str(o) for o in d.get("options", [])],
        chosen=_str(d.get("chosen", "")),
        question=_str(d.get("question", "")),
        reason=_str(d.get("reason", "")),
        activates=[str(a) for a in d.get("activates", [])],
        deactivates=[str(dd) for dd in d.get("deactivates", [])],
        description=_str(d.get("description", "")),
    )


def unknown_from_dict(d: dict[str, Any], declarer: str) -> Unknown:
    return Unknown(
        id=_str(_require(d, "id", "unknown")),
        declarer=declarer,
        description=_str(_require(d, "description", "unknown")),
        blocks=[str(b) for b in d.get("blocks", [])],
    )


def test_result_from_dict(d: dict[str, Any], declarer: str) -> TestResult:
    return TestResult(
        id=_str(_require(d, "id", "test-result")),
        declarer=declarer,
        param=_str(_require(d, "param", "test-result")),
        value=float(_require(d, "value", "test-result")),
        unit=_str(d.get("unit", "")),
        provenance=_provenance(d["provenance"]) if "provenance" in d else None,
        note=_str(d.get("note", "")),
        method=_str(d.get("method", "")),
        recorded=_str(d.get("recorded", "")),
        recalibrates=d.get("recalibrates"),
    )


def _domain(d: dict[str, Any] | None) -> dict[str, list[float]]:
    if not d:
        return {}
    out = {}
    for key, value in d.items():
        pair = [float(value[0]), float(value[1])]
        out[str(key)] = pair
    return out


def _source(d: dict[str, Any] | None) -> SourceRef | None:
    return None if d is None else SourceRef.from_dict(d)


def _review(d: dict[str, Any] | None) -> Review:
    return Review() if d is None else Review.from_dict(d)


_PORT_FIELDS = ("id", "role", "unit", "pair", "description")


def port_to_dict(port: Port) -> dict[str, Any]:
    return _nonempty({f: getattr(port, f) for f in _PORT_FIELDS})


def component_to_dict(component: Component) -> dict[str, Any]:
    out: dict[str, Any] = {"id": component.id, "name": component.name}
    if component.description:
        out["description"] = component.description
    if component.ports:
        out["ports"] = [port_to_dict(p) for p in component.ports]
    return out


def parameter_to_dict(parameter: Parameter) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": parameter.id,
        "symbol": parameter.symbol,
        "unit": parameter.unit,
        "value": parameter.value,
        "provenance": parameter.provenance.to_dict() if parameter.provenance else None,
    }
    if parameter.description:
        out["description"] = parameter.description
    return out


def relation_to_dict(relation: Relation) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": relation.id,
        "equations": list(relation.equations),
        "params": list(relation.params),
    }
    if relation.valid_domain:
        out["valid_domain"] = relation.valid_domain
    if relation.source is not None:
        out["source"] = relation.source.to_dict()
    out["review"] = relation.review.to_dict()
    if relation.rationale:
        out["rationale"] = relation.rationale
        out["rationale_by"] = relation.rationale_by
    if relation.description:
        out["description"] = relation.description
    return out


def constraint_to_dict(constraint: Constraint) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": constraint.id,
        "expression": constraint.expression,
        "params": list(constraint.params),
        "severity": constraint.severity,
    }
    if constraint.source is not None:
        out["source"] = constraint.source.to_dict()
    out["review"] = constraint.review.to_dict()
    if constraint.description:
        out["description"] = constraint.description
    return out


def requirement_to_dict(requirement: Requirement) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": requirement.id,
        "condition": requirement.condition,
        "params": list(requirement.params),
        "owner": requirement.owner,
        "rationale": requirement.rationale,
        "mode": requirement.mode,
    }
    if requirement.source is not None:
        out["source"] = requirement.source.to_dict()
    out["review"] = requirement.review.to_dict()
    if requirement.description:
        out["description"] = requirement.description
    return out


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": decision.id,
        "question": decision.question,
        "options": list(decision.options),
        "chosen": decision.chosen,
        "reason": decision.reason,
    }
    if decision.activates:
        out["activates"] = list(decision.activates)
    if decision.deactivates:
        out["deactivates"] = list(decision.deactivates)
    if decision.description:
        out["description"] = decision.description
    return out


def unknown_to_dict(unknown: Unknown) -> dict[str, Any]:
    out: dict[str, Any] = {"id": unknown.id, "description": unknown.description}
    if unknown.blocks:
        out["blocks"] = list(unknown.blocks)
    return out


def test_result_to_dict(test_result: TestResult) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": test_result.id,
        "param": test_result.param,
        "value": test_result.value,
    }
    if test_result.unit:
        out["unit"] = test_result.unit
    if test_result.provenance is not None:
        out["provenance"] = test_result.provenance.to_dict()
    if test_result.note:
        out["note"] = test_result.note
    if test_result.method:
        out["method"] = test_result.method
    if test_result.recorded:
        out["recorded"] = test_result.recorded
    if test_result.recalibrates is not None:
        out["recalibrates"] = test_result.recalibrates
    return out


_NODE_SERIALIZERS: dict[str, Any] = {
    "Parameter": parameter_to_dict,
    "Relation": relation_to_dict,
    "Constraint": constraint_to_dict,
    "Requirement": requirement_to_dict,
    "Decision": decision_to_dict,
    "Unknown": unknown_to_dict,
    "TestResult": test_result_to_dict,
    "Component": component_to_dict,
}


def _serializer(node: Any):
    return _NODE_SERIALIZERS[type(node).__name__]


def component_file_to_dict(component: Component, project: Project) -> dict[str, Any]:
    out: dict[str, Any] = {"component": component_to_dict(component)}
    owned_params = [parameter_to_dict(p) for p in project.params.values() if p.owner == component.id]
    if owned_params:
        out["parameters"] = owned_params
    for key, kind in _node_sections():
        registry = getattr(project, key, {})
        entries = [_serializer(n)(n) for n in registry.values() if getattr(n, "declarer", None) == component.id]
        if entries:
            out[f"{kind}s"] = entries
    return _ordered(
        out,
        [
            "component",
            "parameters",
            "relations",
            "constraints",
            "requirements",
            "decisions",
            "unknowns",
            "test_results",
        ],
    )


def _declarer(node: Any) -> str:
    return getattr(node, "declarer", getattr(node, "owner", ""))


def _node_sections() -> tuple[tuple[str, str], ...]:
    return (
        ("relations", "relation"),
        ("constraints", "constraint"),
        ("requirements", "requirement"),
        ("decisions", "decision"),
        ("unknowns", "unknown"),
        ("test_results", "test_result"),
    )


def _ordered(d: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {k: d[k] for k in keys if k in d}


def _nonempty(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != ""}
