from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from .ids import IdKind, validate_id
from .model import (
    GraphError,
    Project,
    component_file_to_dict,
    component_from_dict,
    constraint_from_dict,
    decision_from_dict,
    parameter_from_dict,
    relation_from_dict,
    requirement_from_dict,
    test_result_from_dict,
    unknown_from_dict,
)
from .validation import validate_project

_MAIN_FILE = "main.yaml"

_PROJECT_PREFIX = "prj."


def load_project(path: Path | str) -> Project:
    location = Path(path)
    root = (location if location.is_dir() else location.parent).resolve()
    main_path = root / _MAIN_FILE
    try:
        data = _yaml(main_path)
    except FileNotFoundError as err:
        raise GraphError(f"missing {_MAIN_FILE} under {root}") from err

    project_section = _required(data, "project", _MAIN_FILE)
    project_id = str(_required(project_section, "id", "project"))
    if not project_id.startswith(_PROJECT_PREFIX):
        raise GraphError(f"project id must start with {_PROJECT_PREFIX!r}")
    _validate_id(project_id, f"{_PROJECT_PREFIX}...", allow_prefix=_PROJECT_PREFIX)

    project = Project(
        id=project_id,
        name=str(project_section.get("name", project_id)),
        root=root.resolve(),
        settings=dict(data.get("settings", {})),
    )

    declared = [str(p) for p in _required(data, "components", _MAIN_FILE)]
    seen_components: set[str] = set()
    for rel_path in declared:
        component_path = root / rel_path
        payload = _yaml(component_path)
        component = component_from_dict(_required(payload, "component", rel_path))
        if component.id in seen_components:
            raise GraphError(f"duplicate component id {component.id!r}")
        seen_components.add(component.id)
        project.components[component.id] = component
        project.component_files[component.id] = component_path
        _fill_sections(project, payload, component.id, rel_path)

    errors, warnings = validate_project(project)
    if errors:
        raise GraphError("invalid graph:\n" + "\n".join(f"- {e}" for e in errors))
    project.settings.setdefault("warnings", warnings)
    return project


def _fill_sections(project: Project, payload: dict[str, Any], owner: str, source: str) -> None:
    factories: dict[str, tuple[IdKind, Callable[[dict[str, Any]], Any]]] = {
        "parameters": (IdKind.PARAMETER, lambda d: parameter_from_dict(d, owner)),
        "relations": (IdKind.RELATION, lambda d: relation_from_dict(d, owner)),
        "constraints": (IdKind.CONSTRAINT, lambda d: constraint_from_dict(d, owner)),
        "requirements": (IdKind.REQUIREMENT, lambda d: requirement_from_dict(d, owner)),
        "decisions": (IdKind.DECISION, lambda d: decision_from_dict(d, owner)),
        "unknowns": (IdKind.UNKNOWN, lambda d: unknown_from_dict(d, owner)),
        "test_results": (IdKind.TEST_RESULT, lambda d: test_result_from_dict(d, owner)),
    }
    registries: dict[str, dict[str, Any]] = {
        "parameters": project.params,
        "relations": project.relations,
        "constraints": project.constraints,
        "requirements": project.requirements,
        "decisions": project.decisions,
        "unknowns": project.unknowns,
        "test_results": project.test_results,
    }
    for section, (kind, factory) in factories.items():
        entries = payload.get(section, [])
        if not isinstance(entries, list):
            raise GraphError(f"{source}: section {section!r} must be a list")
        registry = registries[section]
        for entry in entries:
            node = factory(entry)
            try:
                validate_id(node.id, kind)
            except ValueError as err:
                raise GraphError(f"{source}: {err}") from err
            if node.id in registry:
                raise GraphError(f"{source}: duplicate id {node.id!r}")
            registry[node.id] = node


def _validate_id(node_id: str, context: str, allow_prefix: str | None = None) -> None:
    if not allow_prefix or not node_id.startswith(allow_prefix):
        raise GraphError(f"{context}: id {node_id!r} is malformed")
    body = node_id[len(allow_prefix) :]
    if not body or not all(c.islower() or c.isdigit() or c == "-" for c in body):
        raise GraphError(f"{context}: id {node_id!r} is malformed")
    if "__" in body or body.startswith("-") or body.endswith("-"):
        raise GraphError(f"{context}: id {node_id!r} is malformed")


def save_component(project: Project, component_id: str) -> Path:
    component = project.components[component_id]
    payload = component_file_to_dict(component, project)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=120)
    path = project.component_files[component_id]
    path.write_text(text, encoding="utf-8")
    return path


def _yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _required(data: Any, key: str, context: str) -> Any:
    if not isinstance(data, dict) or key not in data:
        raise GraphError(f"{context}: missing required key {key!r}")
    return data[key]
