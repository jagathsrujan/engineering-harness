from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..graph.model import (
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

_TABLE = "nodes"
_SERIALIZERS: dict[str, Callable[[Any], dict[str, Any]]] = {
    "relation": relation_to_dict,
    "constraint": constraint_to_dict,
    "requirement": requirement_to_dict,
    "decision": decision_to_dict,
    "unknown": unknown_to_dict,
    "test_result": test_result_to_dict,
}


def rebuild(project: Project) -> Path:
    directory = project.root / ".harness"
    directory.mkdir(parents=True, exist_ok=True)
    db_path = directory / "mirror.db"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            f"CREATE TABLE {_TABLE} (id TEXT PRIMARY KEY, kind TEXT, component TEXT, file TEXT, payload TEXT)"
        )
        rows = _snapshot(project)
        connection.executemany(
            f"INSERT INTO {_TABLE} (id, kind, component, file, payload) VALUES (?, ?, ?, ?, ?)",
            [
                (row_id, kind, component, file, json.dumps(payload, sort_keys=True, ensure_ascii=False))
                for row_id, kind, component, file, payload in rows
            ],
        )
        connection.execute("CREATE INDEX kind_idx ON nodes (kind)")
        connection.commit()
    finally:
        connection.close()
    return db_path


def _snapshot(project: Project) -> list[tuple[str, str, str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, str, str, dict[str, Any]]] = []
    file_of = {cid: str(path.relative_to(project.root)) for cid, path in project.component_files.items()}
    for component in project.components.values():
        rows.append(
            (component.id, "component", component.id, file_of.get(component.id, ""), component_to_dict(component))
        )
    for parameter in project.params.values():
        rows.append(
            (parameter.id, "parameter", parameter.owner, file_of.get(parameter.owner, ""), parameter_to_dict(parameter))
        )
    for _name, kind, registry in (
        ("relations", "relation", project.relations),
        ("constraints", "constraint", project.constraints),
        ("requirements", "requirement", project.requirements),
        ("decisions", "decision", project.decisions),
        ("unknowns", "unknown", project.unknowns),
        ("test_results", "test_result", project.test_results),
    ):
        for node in registry.values():
            rows.append((node.id, kind, node.declarer, file_of.get(node.declarer, ""), _SERIALIZERS[kind](node)))
    return rows


def count_nodes(db_path: Path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        return int(connection.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0])
    finally:
        connection.close()
