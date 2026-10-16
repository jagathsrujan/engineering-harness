from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from ..graph.model import Project, Relation


@dataclass(frozen=True)
class Step:
    relation_id: str
    equation: str
    target_id: str
    input_ids: tuple[str, ...]


@dataclass
class CoupledGroup:
    relation_ids: tuple[str, ...]
    param_ids: tuple[str, ...]
    equations: tuple[tuple[str, str], ...]


@dataclass
class SolvePlan:
    steps: list[Step] = field(default_factory=list)
    coupled_groups: list[CoupledGroup] = field(default_factory=list)
    unsolved_params: list[str] = field(default_factory=list)
    seeded: list[str] = field(default_factory=list)


def sorted_relations(project: Project) -> list[Relation]:
    return sorted(project.relations.values(), key=lambda r: r.id)


def build_plan(project: Project, force: set[str] | None = None) -> SolvePlan:
    forced = set(force or ())
    known: set[str] = {p.id for p in project.params.values() if p.value is not None} - forced
    seeded = sorted({p.id for p in project.params.values() if p.value is not None})
    pending: list[tuple[str, str, Relation]] = []
    for relation in sorted_relations(project):
        for equation in relation.equations:
            pending.append((relation.id, equation, relation))
    pending.sort(key=lambda item: (item[0], item[1]))

    steps: list[Step] = []
    changed = True
    while changed:
        changed = False
        for item in list(pending):
            relation_id, equation, relation = item
            unknown = [p for p in relation.params if p not in known]
            if len(unknown) == 1:
                target = unknown[0]
                inputs = tuple(p for p in relation.params if p != target)
                steps.append(Step(relation_id, equation, target, inputs))
                known.add(target)
                pending.remove(item)
                changed = True

    remaining_unknowns: set[str] = set()
    for _relation_id, _equation, relation in pending:
        remaining_unknowns |= {p for p in relation.params if p not in known}

    graph = nx.Graph()

    equation_meta: dict[str, tuple[str, str, Relation]] = {}
    for index, (relation_id, equation, relation) in enumerate(pending):
        unknown = [p for p in relation.params if p not in known]
        if not unknown:
            continue
        eq_node = f"eq:{index}:{relation_id}"
        equation_meta[eq_node] = (relation_id, equation, relation)
        graph.add_node(eq_node)
        for parameter_id in unknown:
            graph.add_node(parameter_id)
            graph.add_edge(eq_node, parameter_id)

    coupled_groups: list[CoupledGroup] = []
    grouped_params: set[str] = set()
    for component in sorted(nx.connected_components(graph), key=lambda members: sorted(str(m) for m in members)):
        equations_in_component = sorted(n for n in component if n.startswith("eq:"))
        if not equations_in_component:
            continue
        params = sorted(str(p) for p in component if not p.startswith("eq:"))
        grouped_params |= set(params)
        coupled_groups.append(
            CoupledGroup(
                relation_ids=tuple(equation_meta[e][0] for e in equations_in_component),
                param_ids=tuple(params),
                equations=tuple((equation_meta[e][0], equation_meta[e][1]) for e in equations_in_component),
            )
        )

    reachable_targets: set[str] = {step.target_id for step in steps} | grouped_params
    valueless = {p.id for p in project.params.values() if p.value is None}
    unsolved = sorted(valueless - reachable_targets)

    return SolvePlan(steps=steps, coupled_groups=coupled_groups, unsolved_params=unsolved, seeded=seeded)
