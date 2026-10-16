from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ..graph.io import save_component
from ..graph.model import Parameter, Project
from ..graph.provenance import Provenance, Tag


def _project_files(project: Project) -> dict[str, str]:
    files: dict[str, str] = {}
    main = project.root / "main.yaml"
    if main.exists():
        files["main.yaml"] = main.read_text(encoding="utf-8")
    for _component_id, path in sorted(project.component_files.items()):
        rel = str(path.relative_to(project.root))
        files[rel] = path.read_text(encoding="utf-8")
    return files


def _relative(project: Project, path: Path) -> str:
    try:
        return str(path.relative_to(project.root))
    except ValueError:
        return str(path)


class Journal:
    def __init__(self, project: Project) -> None:
        self.project = project
        self.dir = project.root / ".harness"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "history.jsonl"

    def _entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def _append(self, entry: dict) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")

    def _next_seq(self, entries: list[dict]) -> int:
        return (entries[-1]["seq"] + 1) if entries else 1

    def apply_component_change(
        self, component_ids: list[str], author: str = "user", metadata: dict | None = None
    ) -> dict | None:
        before = _project_files(self.project)
        changed_paths = []
        for component_id in component_ids:
            path = save_component(self.project, component_id)
            changed_paths.append(_relative(self.project, path))
        after = _project_files(self.project)
        deltas = {
            rel: {"before": before[rel], "after": after[rel]}
            for rel in sorted(changed_paths)
            if before.get(rel) != after.get(rel)
        }
        if not deltas:
            return None
        entries = self._entries()
        entry = {
            "seq": self._next_seq(entries),
            "action": "apply",
            "author": author,
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
            "files": deltas,
        }
        if metadata:
            entry["metadata"] = metadata
        self._append(entry)
        return entry

    def undo(self) -> int | None:
        entries = self._entries()
        undone = {entry["ref"] for entry in entries if entry["action"] == "undo"}
        restorable = [entry for entry in entries if entry["action"] == "apply" and entry["seq"] not in undone]
        if not restorable:
            return None
        target = restorable[-1]
        for rel, delta in target["files"].items():
            path = self.project.root / rel
            path.write_text(delta["before"], encoding="utf-8")
        self._append(
            {
                "seq": self._next_seq(entries),
                "action": "undo",
                "ref": target["seq"],
                "author": "user",
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
        return target["seq"]


def set_parameter_value(project: Project, parameter_id: str, value: float, provenance: Provenance) -> Parameter:
    parameter = project.params[parameter_id]
    parameter.value = value
    parameter.provenance = provenance
    return parameter


def value_edit(
    project: Project, parameter_id: str, value: float, tag: Tag = Tag.STATED, note: str = "", author: str = "user"
) -> dict | None:
    set_parameter_value(project, parameter_id, value, Provenance(tag=tag, note=note))
    parameter = project.params[parameter_id]
    component_id = parameter.owner
    journal = Journal(project)
    return journal.apply_component_change([component_id], author=author, metadata={"edits": [parameter_id]})


def apply_test_result(project: Project, test_result_id: str, author: str = "user") -> dict | None:
    test_result = project.test_results[test_result_id]
    target_id = test_result.recalibrates or test_result.param
    parameter = project.params[target_id]
    set_parameter_value(
        project,
        target_id,
        test_result.value,
        Provenance(
            tag=Tag.MEASURED,
            note=f"recalibrated by {test_result.id}{' (' + test_result.method + ')' if test_result.method else ''}",
        ),
    )
    journal = Journal(project)
    return journal.apply_component_change(
        [parameter.owner], author=author, metadata={"test_recalibration": test_result_id}
    )
