from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..graph.ids import IdKind, is_kind
from ..graph.model import Project
from ..graph.provenance import effective_tag, inherits_weak_provenance
from .solve import Derivation, SolveResult


@dataclass
class ParamRow:
    id: str
    symbol: str
    unit: str
    value: float | None
    tag: str | None
    weakest: str | None
    verified: bool | None
    unsolved_reason: str | None


@dataclass
class RelationRow:
    id: str
    declarer: str
    review: str
    source: str | None


@dataclass
class CheckRow:
    id: str
    expression: str
    satisfied: bool | None
    kind: str


@dataclass
class UnknownRow:
    id: str
    description: str
    blocks: list[str]


@dataclass
class TestRow:
    id: str
    param: str
    value: float
    unit: str
    note: str
    method: str
    applied: bool


@dataclass
class Report:
    project_id: str
    project_name: str
    params: list[ParamRow] = field(default_factory=list)
    relations: list[RelationRow] = field(default_factory=list)
    constraints: list[CheckRow] = field(default_factory=list)
    requirements: list[CheckRow] = field(default_factory=list)
    unknowns: list[UnknownRow] = field(default_factory=list)
    test_results: list[TestRow] = field(default_factory=list)
    assumption_dependent: list[str] = field(default_factory=list)
    sensitivities: list[tuple[str, str, float]] = field(default_factory=list)
    node_count: int = 0
    plan_steps: int = 0
    recompute_set: list[str] = field(default_factory=list)


def build_report(project: Project, result: SolveResult) -> Report:
    report = Report(
        project_id=project.id,
        project_name=project.name,
        node_count=project.total_nodes(),
        plan_steps=result.plan_steps,
        recompute_set=sorted(result.recompute_set),
    )
    blocked_parameters: set[str] = set()
    for unknown in project.unknowns.values():
        blocked_parameters |= {b for b in unknown.blocks if is_kind(b, IdKind.PARAMETER)}

    for parameter in sorted(project.params.values(), key=lambda p: p.id):
        provenance = result.provenance.get(parameter.id)
        tag = provenance.tag.value if provenance else None
        weakest = effective_tag(provenance).value if provenance else None
        value = result.values.get(parameter.id)
        is_verified = _verification_of(parameter.id, project, result, blocked_parameters) if value is not None else None
        report.params.append(
            ParamRow(
                parameter.id,
                parameter.symbol,
                parameter.unit,
                value,
                tag,
                weakest,
                is_verified,
                result.unsolved.get(parameter.id),
            )
        )
        if provenance is not None and inherits_weak_provenance(effective_tag(provenance)):
            report.assumption_dependent.append(parameter.id)

    for relation in sorted(project.relations.values(), key=lambda r: r.id):
        report.relations.append(
            RelationRow(
                relation.id,
                relation.declarer,
                relation.review.status,
                relation.source.ref if relation.source else None,
            )
        )
    for check in result.constraints:
        report.constraints.append(CheckRow(check.id, check.expression, check.satisfied, check.severity))
    for check in result.requirements:
        report.requirements.append(CheckRow(check.id, check.expression, check.satisfied, check.mode))
    for unknown in sorted(project.unknowns.values(), key=lambda x: x.id):
        report.unknowns.append(UnknownRow(unknown.id, unknown.description, list(unknown.blocks)))
    for test_result in sorted(project.test_results.values(), key=lambda x: x.id):
        target = project.params[test_result.param]
        applied = target.value is not None and test_result.value == target.value
        report.test_results.append(
            TestRow(
                test_result.id,
                test_result.param,
                test_result.value,
                test_result.unit,
                test_result.note,
                test_result.method,
                applied,
            )
        )
    report.sensitivities = sorted((t, i, s) for (t, i), s in result.sensitivity.items())
    return report


def _verification_of(parameter_id: str, project: Project, result: SolveResult, blocked: set[str]) -> bool:
    visited: set[str] = set()
    stack = [parameter_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if result.values.get(current) is None:
            return False
        if current in blocked:
            return False
        derivation = result.derivations.get(current) or Derivation([], [])
        for relation_id in derivation.relation_ids:
            relation = project.relations.get(relation_id)
            if relation is None or relation.review.status != "reviewed":
                return False
        stack.extend(derivation.input_ids)
    return True


def format_report(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"project {report.project_id} ({report.project_name}): {report.node_count} nodes")
    lines.append("")
    lines.append(f"PARAMETERS ({len(report.params)})")
    for row in report.params:
        value = "-" if row.value is None else f"{row.value:g}"
        flags = []
        if row.unsolved_reason:
            flags.append(f"UNSOLVED[{row.unsolved_reason}]")
        if row.verified is True:
            flags.append("verified")
        elif row.verified is False and row.value is not None:
            flags.append("unverified")
        weakest = row.weakest if row.weakest not in (None, "computed") else None
        lines.append(
            f"  {row.symbol:<14} {value:>12} {row.unit or '-':<10} tag={row.tag or '-':<12}"
            + (f" weakest={weakest}" if weakest and weakest != row.tag else "")
            + (f" [{' '.join(flags)}]" if flags else "")
        )
    if report.assumption_dependent:
        lines.append("")
        lines.append(f"ASSUMPTION-DEPENDENT VALUES ({len(report.assumption_dependent)})")
        for parameter_id in report.assumption_dependent:
            lines.append(f"  {parameter_id}")
    lines.append("")
    lines.append(f"RELATIONS ({len(report.relations)})")
    for rel_row in report.relations:
        lines.append(f"  {rel_row.id:<40} review={rel_row.review:<12} source={rel_row.source or '-'}")
    if report.constraints:
        lines.append("")
        lines.append(f"CONSTRAINTS ({len(report.constraints)})")
        for check_row in report.constraints:
            state = "undetermined" if check_row.satisfied is None else ("ok" if check_row.satisfied else "VIOLATED")
            lines.append(f"  {check_row.id:<40} {state:<14} [{check_row.kind}] {check_row.expression}")
    if report.requirements:
        lines.append("")
        lines.append(f"REQUIREMENTS ({len(report.requirements)})")
        for req_row in report.requirements:
            state = "undetermined" if req_row.satisfied is None else ("ok" if req_row.satisfied else "VIOLATED")
            lines.append(f"  {req_row.id:<40} {state:<14} [{req_row.kind}] {req_row.expression}")
    if report.unknowns:
        lines.append("")
        lines.append(f"UNKNOWNS ({len(report.unknowns)})")
        for unknown_row in report.unknowns:
            blocked = ", ".join(unknown_row.blocks) or "nothing yet"
            lines.append(f"  {unknown_row.id}: {unknown_row.description} (blocks: {blocked})")
    if report.test_results:
        lines.append("")
        lines.append(f"TEST RESULTS ({len(report.test_results)})")
        for test_row in report.test_results:
            state = "applied" if test_row.applied else "pending recalibration"
            detail = f"{test_row.value:g} {test_row.unit} -> {test_row.param} ({state})"
            lines.append(f"  {test_row.id}: {detail} {test_row.note}".rstrip())
    if report.sensitivities:
        lines.append("")
        lines.append(f"SENSITIVITIES ({len(report.sensitivities)})")
        for target_id, source_id, gradient in report.sensitivities:
            lines.append(f"  d[{target_id.split('#', 1)[-1]}]/d[{source_id.split('#', 1)[-1]}] = {gradient:+.4g}")
    return "\n".join(lines)


def report_to_dict(report: Report) -> dict[str, Any]:
    def _rows(rows):
        return [r.__dict__ for r in rows]

    return {
        "project_id": report.project_id,
        "project_name": report.project_name,
        "node_count": report.node_count,
        "plan_steps": report.plan_steps,
        "parameters": _rows(report.params),
        "relations": _rows(report.relations),
        "constraints": _rows(report.constraints),
        "requirements": _rows(report.requirements),
        "unknowns": _rows(report.unknowns),
        "test_results": _rows(report.test_results),
        "assumption_dependent": report.assumption_dependent,
        "sensitivities": [list(x) for x in report.sensitivities],
        "recompute_set": report.recompute_set,
    }


def verify_exit_code(report: Report) -> int:
    for row in report.constraints:
        if row.satisfied is False and row.kind == "error":
            return 1
    for row in report.requirements:
        if row.satisfied is False and row.kind == "required":
            return 1
    return 0
