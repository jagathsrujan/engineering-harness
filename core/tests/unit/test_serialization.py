from __future__ import annotations

from pathlib import Path

import pytest

from conftest import temp_copy
from harness.graph.diff import structural_diff
from harness.graph.io import load_project, save_component
from harness.graph.model import GraphError


def test_component_roundtrip_is_semantically_stable(gearbox) -> None:
    before = structural_diff(gearbox, gearbox)
    assert before == []
    for component_id in sorted(gearbox.components):
        save_component(gearbox, component_id)
    reloaded = load_project(gearbox.root)
    assert structural_diff(gearbox, reloaded) == []


def _edit_component_yaml(component_file: Path, fn) -> None:
    import yaml

    data = yaml.safe_load(component_file.read_text(encoding="utf-8"))
    fn(data)
    component_file.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )


def test_duplicate_id_is_rejected(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    fasteners = target / "components" / "fasteners.yaml"

    def rename(data: dict) -> None:
        for relation in data["relations"]:
            if relation["id"] == "rl.preload":
                relation["id"] = "rl.bearing-life"

    _edit_component_yaml(fasteners, rename)
    with pytest.raises(GraphError, match="duplicate"):
        load_project(target)


def test_missing_reference_is_rejected(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    motor = target / "components" / "drive-motor.yaml"

    def point_to_nothing(data: dict) -> None:
        for relation in data["relations"]:
            if relation["id"] == "rl.omega-in":
                relation["params"] = ["cmp.nothing#n_in", "cmp.drive-motor#omega_in"]

    _edit_component_yaml(motor, point_to_nothing)
    with pytest.raises(GraphError, match="references unknown parameters"):
        load_project(target)
