from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import networkx as nx
import sympy as sp

from ..graph.model import Parameter, Project
from ..graph.provenance import Provenance, Tag, effective_tag, weakest_tag
from ..units import units as u
from .sensitivity import coupled_sensitivities, step_sensitivities
from .topology import CoupledGroup, SolvePlan, Step, build_plan


@dataclass
class CheckResult:
    id: str
    expression: str
    satisfied: bool | None
    severity: str = ""
    mode: str = ""


@dataclass
class Derivation:
    relation_ids: list[str]
    input_ids: list[str]


@dataclass
class SolveResult:
    values: dict[str, float] = field(default_factory=dict)
    provenance: dict[str, Provenance] = field(default_factory=dict)
    derivations: dict[str, Derivation] = field(default_factory=dict)
    unsolved: dict[str, str] = field(default_factory=dict)
    flow: dict[str, list[str]] = field(default_factory=dict)
    recompute_set: set[str] = field(default_factory=set)
    sensitivity: dict[tuple[str, str], float] = field(default_factory=dict)
    constraints: list[CheckResult] = field(default_factory=list)
    requirements: list[CheckResult] = field(default_factory=list)
    plan_steps: int = 0


def run(project: Project, edited: set[str] | None = None, base: SolveResult | None = None) -> SolveResult:
    if edited is None:
        return _full_solve(project)
    if base is None:
        base = _full_solve(project)
    return _edit_solve(project, base, set(edited))


def _full_solve(project: Project) -> SolveResult:
    plan = build_plan(project)
    graph = _flow_graph(plan)
    result = SolveResult(plan_steps=len(plan.steps))

    result.values = {p.id: float(p.value) for p in project.params.values() if p.value is not None}
    for parameter in project.params.values():
        if parameter.provenance is not None:
            result.provenance[parameter.id] = parameter.provenance

    result.recompute_set = {step.target_id for step in plan.steps}
    result.recompute_set |= {pid for group in plan.coupled_groups for pid in group.param_ids}

    for parameter_id in plan.unsolved_params:
        result.unsolved[parameter_id] = "missing-inputs"

    result.flow = {node: sorted(graph.successors(node)) for node in sorted(graph.nodes) if graph.out_degree(node) > 0}

    _execute_steps(project, plan, result, None)
    _execute_coupled_groups(project, plan, result, None)
    _check_conditions(project, result)
    return result


def _edit_solve(project: Project, base: SolveResult, edited: set[str]) -> SolveResult:
    graph = nx.DiGraph()
    for node, successors in base.flow.items():
        for successor in successors:
            graph.add_edge(node, successor)
    recompute = _affected(graph, edited)

    plan = build_plan(project, force=recompute)
    result = SolveResult(plan_steps=len(plan.steps))
    result.values = dict(base.values)
    result.provenance = dict(base.provenance)
    result.derivations = dict(base.derivations)
    result.sensitivity = dict(base.sensitivity)
    result.unsolved = dict(base.unsolved)
    result.recompute_set = recompute
    result.flow = base.flow

    for parameter_id, parameter in project.params.items():
        if parameter.value is not None:
            result.values[parameter_id] = float(parameter.value)
            if parameter.provenance is not None:
                result.provenance[parameter_id] = parameter.provenance

    _execute_steps(project, plan, result, recompute)
    _execute_coupled_groups(project, plan, result, recompute)
    _check_conditions(project, result)
    return result


def _flow_graph(plan: SolvePlan) -> nx.DiGraph:
    graph = nx.DiGraph()
    for step in plan.steps:
        for input_id in step.input_ids:
            graph.add_edge(input_id, step.target_id)
    for group in plan.coupled_groups:
        for first in group.param_ids:
            for second in group.param_ids:
                if first != second:
                    graph.add_edge(first, second)
    return graph


def _affected(graph: nx.DiGraph, edited: set[str]) -> set[str]:
    affected: set[str] = set()
    stack = deque(sorted(edited))
    seen = set(edited)
    while stack:
        node = stack.popleft()
        for successor in sorted(graph.successors(node)):
            if successor not in seen:
                seen.add(successor)
                affected.add(successor)
                stack.append(successor)
    return affected


def _execute_steps(project: Project, plan: SolvePlan, result: SolveResult, targets: set[str] | None) -> None:
    for step in plan.steps:
        if targets is not None and step.target_id not in targets:
            continue
        _run_step(project, step, result)


def _run_step(project: Project, step: Step, result: SolveResult) -> None:
    relation = project.relations[step.relation_id]
    for pid in relation.params:
        if pid == step.target_id:
            continue
        if pid not in result.values:
            result.unsolved[step.target_id] = "missing-inputs"
            return

    for domain_key, (low, high) in sorted(relation.valid_domain.items()):
        value = result.values[domain_key]
        if not (low <= value <= high):
            result.unsolved[step.target_id] = "out-of-validity-domain"
            return

    symbols, symbol_params = _symbol_map_for(project, relation.params)
    input_ids = set(step.input_ids)
    si_inputs = {
        symbol: u.si_value(result.values[symbol_params[symbol]], project.params[symbol_params[symbol]].unit)
        for symbol in symbol_params
        if symbol_params[symbol] in input_ids and symbol_params[symbol] in result.values
    }
    try:
        lhs, rhs = u.parse_equation(step.equation, symbols)
    except u.UnitError as err:
        result.unsolved[step.target_id] = f"dimension-mismatch ({err})"
        return

    target_symbol = sp.Symbol(project.params[step.target_id].symbol)
    try:
        solutions = sp.solve(sp.Eq(lhs, rhs), target_symbol, dict=True)
    except Exception as err:
        result.unsolved[step.target_id] = f"iteration-no-convergence ({err})"
        return
    if not solutions:
        result.unsolved[step.target_id] = "under-determined"
        return
    if len(solutions) > 1:
        result.unsolved[step.target_id] = "under-determined"
        return

    solved_expr = solutions[0][target_symbol]
    provided = {s for s in solved_expr.free_symbols if str(s) in si_inputs}
    if provided != solved_expr.free_symbols:
        result.unsolved[step.target_id] = "under-determined"
        return

    result.sensitivity.update(step_sensitivities(solved_expr, symbol_params, si_inputs, step.target_id))

    target = project.params[step.target_id]
    try:
        si_target = u.evaluate_expression(solved_expr, si_inputs)
        value = u.from_si(si_target, target.unit)
    except u.UnitError as err:
        result.unsolved[step.target_id] = f"iteration-no-convergence ({err})"
        return

    result.values[step.target_id] = value
    result.unsolved.pop(step.target_id, None)
    result.provenance[step.target_id] = Provenance(
        tag=Tag.COMPUTED,
        inherited_weakest=weakest_tag(
            [effective_tag(result.provenance[p]) for p in step.input_ids if p in result.provenance]
        ),
        note=f"via {relation.id}",
    )
    result.derivations[step.target_id] = Derivation([relation.id], list(step.input_ids))


def _execute_coupled_groups(project: Project, plan: SolvePlan, result: SolveResult, targets: set[str] | None) -> None:
    for group in plan.coupled_groups:
        if targets is not None and not (set(group.param_ids) & targets):
            continue
        _run_coupled_group(project, group, result)


def _run_coupled_group(project: Project, group: CoupledGroup, result: SolveResult) -> None:
    outside = _external_params(group, project)
    params = dict(_params_map(project, list(group.param_ids) + outside))
    symbols, symbol_params = _symbol_map_for(project, list(params))
    unknown_symbols = [sp.Symbol(project.params[pid].symbol) for pid in group.param_ids]

    try:
        equalities = [sp.Eq(*u.parse_equation(equation, symbols)) for _, equation in group.equations]
    except u.UnitError as err:
        for pid in group.param_ids:
            result.unsolved[pid] = f"dimension-mismatch ({err})"
        return

    si_inputs = {
        symbol: u.si_value(result.values[symbol_params[symbol]], project.params[symbol_params[symbol]].unit)
        for symbol in symbol_params
        if symbol_params[symbol] in result.values
    }

    def numeric_solution(si_point: dict[str, float]) -> dict[str, float] | None:
        try:
            solutions = sp.solve(equalities, unknown_symbols, dict=True)
        except Exception:
            return None
        for solution in solutions:
            if any(not value.is_number for value in solution.values()):
                continue
            values: dict[str, float] = {}
            usable = True
            for symbol, value in solution.items():
                try:
                    values[str(symbol)] = float(sp.N(value))
                except (TypeError, ValueError):
                    usable = False
                    break
            if usable:
                return values
        return None

    found = numeric_solution(si_inputs)
    if found is None:
        for pid in group.param_ids:
            result.unsolved.setdefault(pid, "under-determined")
        return

    base = dict(si_inputs)
    for symbol_name, value in found.items():
        base[symbol_name] = value

    def resolve(si_point: dict[str, float]) -> dict[str, float]:
        local = numeric_solution(si_point)
        if local is None:
            raise u.UnitError("coupled iteration failed")
        return local

    external = outside
    inherit = weakest_tag([effective_tag(result.provenance[i]) for i in external if i in result.provenance])
    relation_ids = list(group.relation_ids)
    for pid in group.param_ids:
        target = project.params[pid]
        symbol_name = target.symbol
        if target.unit:
            value = u.from_si(base[symbol_name], target.unit)
        else:
            value = base[symbol_name]
        result.values[pid] = value
        result.unsolved.pop(pid, None)
        result.provenance[pid] = Provenance(
            tag=Tag.COMPUTED,
            inherited_weakest=inherit,
            note=f"via coupled {','.join(relation_ids)}",
        )
        result.derivations[pid] = Derivation(relation_ids, [p for p in group.param_ids if p != pid] + external)

    if len(group.param_ids) < 8:
        sensitivity_map = coupled_sensitivities(
            group,
            resolve,
            base,
            symbol_params,
            list(group.param_ids),
        )
        result.sensitivity.update(sensitivity_map)


def _external_params(group: CoupledGroup, project: Project) -> list[str]:
    external: set[str] = set()
    for relation_id in group.relation_ids:
        external |= set(project.relations[relation_id].params)
    return sorted(external - set(group.param_ids))


def _params_map(project: Project, parameter_ids: list[str]) -> dict[str, Parameter]:
    return {pid: project.params[pid] for pid in parameter_ids}


def _symbol_map_for(project: Project, parameter_ids: list[str]) -> tuple[dict[str, sp.Symbol], dict[str, str]]:
    symbols = {project.params[pid].symbol: sp.Symbol(project.params[pid].symbol) for pid in parameter_ids}
    symbol_params = {project.params[pid].symbol: pid for pid in parameter_ids}
    return symbols, symbol_params


def _check_conditions(project: Project, result: SolveResult) -> None:
    declared_all = {
        parameter.symbol: value
        for parameter in project.params.values()
        if (value := result.values.get(parameter.id)) is not None
    }
    result.constraints = _evaluate_checks(project, project.constraints, "expression", declared_all)
    result.requirements = _evaluate_checks(project, project.requirements, "condition", declared_all)


def _evaluate_checks(
    project: Project, checks: dict, expression_attribute: str, declared_all: dict[str, float]
) -> list[CheckResult]:
    out: list[CheckResult] = []
    for check in checks.values():
        symbols = {
            project.params[pid].symbol: sp.Symbol(project.params[pid].symbol)
            for pid in check.params
            if pid in project.params
        }
        expression = getattr(check, expression_attribute)
        try:
            relational = u.parse_boolean(expression, symbols)
            satisfied = u.evaluate_boolean(relational, declared_all)
        except u.UnitError:
            satisfied = None
        out.append(
            CheckResult(
                check.id,
                expression,
                satisfied,
                severity=getattr(check, "severity", ""),
                mode=getattr(check, "mode", ""),
            )
        )
    return out
