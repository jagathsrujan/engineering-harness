from __future__ import annotations

import re

import sympy as sp

from ..units.units import (
    UnitError,
    check_equation_dimensions,
    parse_boolean,
    parse_equation,
    unit_of,
)
from .ids import IdKind, kind_of
from .model import Project
from .provenance import SourceRef
from .review import Review

SYMBOL_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_PORT_ROLES = {"potential", "flow"}
_SEVERITIES = {"error", "warning", "info"}
_REQUIREMENT_MODES = {"assumed", "required"}
_SOURCE_KINDS = {"inline", "textbook", "standard", "pack-entry", "citation"}
_REVIEW_STATUSES = {"unreviewed", "reviewed", "disputed"}
_RELATION_TARGET_KINDS = ("relations", "constraints", "requirements")


def validate_project(project: Project) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: dict[str, str] = {}

    def mark(node_id: str, where: str) -> None:
        if node_id in seen:
            errors.append(f"duplicate id {node_id!r} declared in {seen[node_id]!r} and {where!r}")
        else:
            seen[node_id] = where

    symbol_owner: dict[str, str] = {}
    for parameter in project.params.values():
        mark(parameter.id, "parameter")
        _check_id(parameter.id, IdKind.PARAMETER, errors)
        if not SYMBOL_PATTERN.match(parameter.symbol):
            errors.append(f"{parameter.id}: symbol {parameter.symbol!r} is not a valid sympy symbol")
        elif parameter.symbol in symbol_owner:
            errors.append(
                f"{parameter.id}: symbol {parameter.symbol!r} already used by {symbol_owner[parameter.symbol]!r}"
            )
        else:
            symbol_owner[parameter.symbol] = parameter.id
        _check_unit(parameter.unit, parameter.id, errors)
        if parameter.provenance is None:
            errors.append(f"{parameter.id}: provenance is required (R3)")

    components = set(project.components)
    for component in project.components.values():
        mark(component.id, "component")
        _check_id(component.id, IdKind.COMPONENT, errors)
        port_ids = {p.id for p in component.ports}
        for port in component.ports:
            mark(port.id, f"port of {component.id}")
            _check_id(port.id, IdKind.PARAMETER, errors)
            if port.role not in _PORT_ROLES:
                errors.append(f"{port.id}: role {port.role!r} must be potential or flow")
            _check_unit(port.unit, port.id, errors)
            if port.pair and port.pair not in port_ids:
                errors.append(f"{port.id}: paired port {port.pair!r} is not declared in component {component.id!r}")

    for relation in project.relations.values():
        mark(relation.id, "relation")
        _check_id(relation.id, IdKind.RELATION, errors)
        _check_source(relation.source, relation.id, errors)
        _check_review(relation.review, relation.id, errors)
        missing_owner = set(relation.params) - set(project.params)
        if missing_owner:
            errors.append(f"{relation.id}: references unknown parameters {sorted(missing_owner)}")
        symbol_units: dict[str, str] = {}
        for parameter_id in relation.params:
            relation_param = project.params.get(parameter_id)
            if relation_param is not None and relation_param.symbol not in symbol_units:
                symbol_units[relation_param.symbol] = relation_param.unit
        used_params: set[str] = set()
        for equation in relation.equations:
            try:
                lhs, rhs = parse_equation(equation, {name: sp.Symbol(name) for name in symbol_units})
            except UnitError as err:
                errors.append(f"{relation.id}: equation {equation!r} rejected: {err}")
                continue
            used = {str(s) for s in (lhs.free_symbols | rhs.free_symbols) if str(s) not in {"pi", "e", "inf"}}
            undeclared = used - set(symbol_units)
            if undeclared:
                errors.append(f"{relation.id}: equation {equation!r} uses undeclared symbols {sorted(undeclared)}")
                continue
            used_params |= {symbol_owner[s] for s in used if s in symbol_owner}
            try:
                check_equation_dimensions(lhs, rhs, symbol_units)
            except UnitError as err:
                errors.append(f"{relation.id}: equation {equation!r} rejected (R2): {err}")
        orphans = set(relation.params) - used_params
        if orphans:
            warnings.append(f"{relation.id}: params never used by equations: {sorted(orphans)}")
        for domain_key, pair in relation.valid_domain.items():
            if domain_key not in relation.params:
                errors.append(f"{relation.id}: validity domain key {domain_key!r} is not a relation param")
            elif len(pair) != 2 or pair[0] >= pair[1]:
                errors.append(f"{relation.id}: invalid validity domain {pair!r}")

    for constraint in project.constraints.values():
        mark(constraint.id, "constraint")
        _check_id(constraint.id, IdKind.CONSTRAINT, errors)
        _check_source(constraint.source, constraint.id, errors)
        _check_review(constraint.review, constraint.id, errors)
        if constraint.severity not in _SEVERITIES:
            errors.append(f"{constraint.id}: severity {constraint.severity!r} invalid")
        _check_boolean(constraint.expression, constraint.params, project, symbol_owner, constraint.id, errors)

    for requirement in project.requirements.values():
        mark(requirement.id, "requirement")
        _check_id(requirement.id, IdKind.REQUIREMENT, errors)
        if requirement.mode not in _REQUIREMENT_MODES:
            errors.append(f"{requirement.id}: mode {requirement.mode!r} must be assumed or required")
        _check_source(requirement.source, requirement.id, errors)
        _check_review(requirement.review, requirement.id, errors)
        _check_boolean(requirement.condition, requirement.params, project, symbol_owner, requirement.id, errors)

    for decision in project.decisions.values():
        mark(decision.id, "decision")
        _check_id(decision.id, IdKind.DECISION, errors)
        if not decision.options:
            errors.append(f"{decision.id}: options is empty")
        elif decision.chosen and decision.chosen not in decision.options:
            errors.append(f"{decision.id}: chosen {decision.chosen!r} is not among options")
        for target in decision.activates + decision.deactivates:
            if any(target in getattr(project, kind) for kind in _RELATION_TARGET_KINDS):
                continue
            errors.append(f"{decision.id}: activate/deactivate target {target!r} does not exist")

    for unknown in project.unknowns.values():
        mark(unknown.id, "unknown")
        _check_id(unknown.id, IdKind.UNKNOWN, errors)
        for blocked in unknown.blocks:
            if blocked not in project.params and blocked not in project.relations:
                errors.append(f"{unknown.id}: blocks {blocked!r} which does not exist")

    for test_result in project.test_results.values():
        mark(test_result.id, "test-result")
        _check_id(test_result.id, IdKind.TEST_RESULT, errors)
        measured_target = project.params.get(test_result.param)
        if measured_target is None:
            errors.append(f"{test_result.id}: measured parameter {test_result.param!r} does not exist")
        else:
            _check_unit(test_result.unit, test_result.id, errors)
            if test_result.unit and measured_target.unit:
                try:
                    left = unit_of(test_result.unit).dimensionality
                    right = unit_of(measured_target.unit).dimensionality
                    if left != right:
                        errors.append(
                            f"{test_result.id}: unit {test_result.unit!r} incompatible with {measured_target.unit!r}"
                        )
                except UnitError:
                    pass
        if test_result.recalibrates and test_result.recalibrates not in project.params:
            errors.append(f"{test_result.id}: recalibrates {test_result.recalibrates!r} does not exist")

    for kind_name, nodes in (
        ("parameter", project.params),
        ("relation", project.relations),
        ("constraint", project.constraints),
        ("requirement", project.requirements),
        ("decision", project.decisions),
        ("unknown", project.unknowns),
    ):
        for node in nodes.values():
            declarer = getattr(node, "declarer", None) or getattr(node, "owner", None)
            if declarer not in components:
                errors.append(f"{node.id}: declarer {declarer!r} is not a declared component ({kind_name})")

    return errors, warnings


def _check_id(node_id: str, kind: IdKind, errors: list[str]) -> None:
    try:
        if kind_of(node_id) != kind:
            errors.append(f"{node_id!r} does not follow the {kind.value} id convention")
    except ValueError as err:
        errors.append(str(err))


def _check_unit(unit_text: str, node_id: str, errors: list[str]) -> None:
    if not unit_text:
        return
    try:
        unit_of(unit_text)
    except UnitError as err:
        errors.append(f"{node_id}: {err}")


def _check_source(source: SourceRef | None, node_id: str, errors: list[str]) -> None:
    if source is not None and source.kind not in _SOURCE_KINDS:
        errors.append(f"{node_id}: source kind {source.kind!r} must be one of {sorted(_SOURCE_KINDS)}")


def _check_review(review: Review | None, node_id: str, errors: list[str]) -> None:
    if review is not None and review.status not in _REVIEW_STATUSES:
        errors.append(f"{node_id}: review status {review.status!r} invalid")


def _check_boolean(
    expression: str,
    parameter_ids: list[str],
    project: Project,
    symbol_owner: dict[str, str],
    node_id: str,
    errors: list[str],
) -> None:
    declared_symbols = {
        project.params[pid].symbol: sp.Symbol(project.params[pid].symbol)
        for pid in parameter_ids
        if pid in project.params
    }
    for parameter_id in parameter_ids:
        if parameter_id not in project.params:
            errors.append(f"{node_id}: references unknown parameter {parameter_id!r}")
    try:
        rel = parse_boolean(expression, declared_symbols)
    except (UnitError, ValueError, SyntaxError) as err:
        errors.append(f"{node_id}: expression {expression!r} rejected: {err}")
        return
    used = {str(s) for s in rel.free_symbols if str(s) not in {"pi", "e", "inf"}}
    undeclared = used - set(declared_symbols)
    if undeclared:
        errors.append(f"{node_id}: expression uses undeclared symbols {sorted(undeclared)}")
