from __future__ import annotations

from pathlib import Path

import pytest

from conftest import temp_copy
from harness.graph.io import load_project
from harness.graph.model import Project
from harness.graph.provenance import Tag
from harness.history.journal import Journal, apply_test_result, value_edit
from harness.solver.solve import run
from harness.solver.topology import build_plan

DEPENDENTS_POWER_CHAIN = {
    "cmp.gear-stage#p_out",
    "cmp.gear-stage#t1",
    "cmp.gear-stage#f_t",
    "cmp.gear-stage#sigma_f",
    "cmp.gear-stage#s_f",
    "cmp.shaft-1#m_b",
    "cmp.shaft-1#sigma_b",
    "cmp.shaft-1#tau",
    "cmp.shaft-1#sigma_e",
    "cmp.shaft-1#n_sf",
    "cmp.bearing-1#l10",
    "cmp.bearing-1#h_life",
}

DEPENDENTS_SHAFT_DIAMETER = {
    "cmp.shaft-1#sigma_b",
    "cmp.shaft-1#tau",
    "cmp.shaft-1#sigma_e",
    "cmp.shaft-1#n_sf",
}


def test_r1_determinism_and_golden_values(gearbox, expects: dict[str, float]) -> None:
    first = run(gearbox)
    second = run(gearbox)
    assert first.values == second.values
    for parameter_id, expected in expects.items():
        assert first.values[parameter_id] == pytest.approx(expected, rel=1e-9), parameter_id


def _edit_component_yaml(component_file: Path, fn) -> None:
    import yaml

    data = yaml.safe_load(component_file.read_text(encoding="utf-8"))
    fn(data)
    component_file.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )


def test_r2_dimensionally_inconsistent_relation_is_rejected(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    stage = target / "components" / "gear-stage.yaml"

    def inject(data: dict) -> None:
        for relation in data["relations"]:
            if relation["id"] == "rl.p-out":
                relation["equations"] = ["p_out = eta*p_in + t1"]
                relation["params"] = list(dict.fromkeys([*relation["params"], "cmp.gear-stage#t1"]))

    _edit_component_yaml(stage, inject)
    with pytest.raises(Exception, match="dimensional mismatch"):
        load_project(target)


def test_r2_unknown_unit_is_rejected(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    motor = target / "components" / "drive-motor.yaml"

    def swap_unit(data: dict) -> None:
        for parameter in data["parameters"]:
            if parameter["id"] == "cmp.drive-motor#p_in":
                parameter["unit"] = "kiloflanigans"

    _edit_component_yaml(motor, swap_unit)
    with pytest.raises(Exception, match="cannot parse unit"):
        load_project(target)


def test_r3_value_without_tag_rejected(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    motor = target / "components" / "drive-motor.yaml"

    def strip_tag(data: dict) -> None:
        for parameter in data["parameters"]:
            if parameter["id"] == "cmp.drive-motor#p_in":
                parameter["provenance"] = {}

    _edit_component_yaml(motor, strip_tag)
    with pytest.raises(Exception, match="provenance.tag is required"):
        load_project(target)


def test_r3_every_parameter_has_a_tag(gearbox) -> None:
    assert gearbox.params
    for parameter in gearbox.params.values():
        assert parameter.provenance is not None, parameter.id


def test_r4_computed_value_inherits_weakest_provenance(gearbox) -> None:
    result = run(gearbox)
    p_out = result.provenance["cmp.gear-stage#p_out"]
    assert p_out.tag == Tag.COMPUTED
    assert p_out.inherited_weakest == Tag.ASSUMED
    assert result.provenance["cmp.fasteners#f_i"].inherited_weakest == Tag.LOOKED_UP
    assert result.provenance["cmp.drive-motor#omega_in"].inherited_weakest == Tag.STATED


def test_r4_measured_recalibration_lifts_weak_provenance(gearbox_root: Path, tmp_path: Path) -> None:
    project = load_project(temp_copy(gearbox_root, tmp_path))
    applied = apply_test_result(project, "tr.rig-eta")
    assert applied is not None
    assert project.params["cmp.gear-stage#eta"].provenance.tag == Tag.MEASURED
    result = run(project)
    assert result.provenance["cmp.gear-stage#p_out"].inherited_weakest == Tag.STATED
    assert result.values["cmp.gear-stage#p_out"] == pytest.approx(0.93 * 5.0)
    assert result.provenance["cmp.bearing-1#h_life"].inherited_weakest == Tag.LOOKED_UP


def test_r5_recompute_set_equals_dependents(gearbox) -> None:
    recomputed = run(gearbox, edited={"cmp.drive-motor#p_in"})
    assert recomputed.recompute_set == DEPENDENTS_POWER_CHAIN


def test_r5_only_dependents_change_values(gearbox) -> None:
    before = run(gearbox)
    target_value = 7.5
    gearbox.params["cmp.drive-motor#p_in"].value = target_value
    after = run(gearbox, edited={"cmp.drive-motor#p_in"}, base=before)
    assert after.values["cmp.gear-stage#p_out"] == pytest.approx(0.95 * target_value)
    for parameter_id, value in before.values.items():
        if parameter_id not in after.recompute_set and parameter_id != "cmp.drive-motor#p_in":
            assert after.values[parameter_id] == value


def test_r5_shaft_edit_needs_only_shaft_chain(gearbox) -> None:
    before = run(gearbox)
    before_value = gearbox.params["cmp.shaft-1#d_shaft"].value
    gearbox.params["cmp.shaft-1#d_shaft"].value = 20.0
    recomputed = run(gearbox, edited={"cmp.shaft-1#d_shaft"}, base=before)
    assert recomputed.recompute_set == DEPENDENTS_SHAFT_DIAMETER
    assert recomputed.values["cmp.shaft-1#sigma_e"] > before.values["cmp.shaft-1#sigma_e"]
    assert gearbox.params["cmp.shaft-1#d_shaft"].value == 20.0
    gearbox.params["cmp.shaft-1#d_shaft"].value = before_value


def test_r7_undo_restores_bytes(gearbox) -> None:
    def read_all(project: Project) -> dict[str, str]:
        main = project.root / "main.yaml"
        files = {"main.yaml": main.read_text(encoding="utf-8")}
        for _cid, path in project.component_files.items():
            files[str(path.relative_to(project.root))] = path.read_text(encoding="utf-8")
        return files

    before = read_all(gearbox)
    entry = value_edit(gearbox, "cmp.drive-motor#p_in", 7.5, author="test")
    assert entry is not None
    mid = read_all(gearbox)
    assert mid != before
    journal = Journal(gearbox)
    assert journal.undo() is not None
    assert read_all(gearbox) == before


def test_r8_missing_input_never_guessed(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    motor = target / "components" / "drive-motor.yaml"

    def drop_speed_value(data: dict) -> None:
        for parameter in data["parameters"]:
            if parameter["id"] == "cmp.drive-motor#n_in":
                parameter.pop("value", None)

    _edit_component_yaml(motor, drop_speed_value)
    project = load_project(target)
    result = run(project)

    taxonomy = {
        "missing-inputs",
        "under-determined",
        "dimension-mismatch",
        "iteration-no-convergence",
        "out-of-validity-domain",
        "blocked-by-unknown",
    }
    assert result.unsolved, "nothing was marked unsolved"
    for parameter_id, reason in result.unsolved.items():
        assert reason in taxonomy, (parameter_id, reason)
    assert result.unsolved["cmp.drive-motor#omega_in"] in taxonomy
    for parameter_id in ("cmp.drive-motor#omega_in", "cmp.drive-motor#n_in"):
        assert parameter_id not in result.values


def test_r8_underdetermined_is_named(gearbox_root: Path, tmp_path: Path) -> None:
    target = temp_copy(gearbox_root, tmp_path)
    fasteners = target / "components" / "fasteners.yaml"

    def append_bad(data: dict) -> None:
        parameters = data.setdefault("parameters", [])
        parameters.append(
            {"id": "cmp.fasteners#x_bad", "symbol": "x_bad", "unit": "", "provenance": {"tag": "computed"}}
        )
        parameters.append(
            {"id": "cmp.fasteners#y_bad", "symbol": "y_bad", "unit": "", "provenance": {"tag": "computed"}}
        )
        relations = data.setdefault("relations", [])
        relations.append(
            {
                "id": "rl.bad-piece",
                "equations": ["x_bad = y_bad"],
                "params": ["cmp.fasteners#x_bad", "cmp.fasteners#y_bad"],
                "review": {"status": "unreviewed"},
            }
        )

    _edit_component_yaml(fasteners, append_bad)
    project = load_project(target)
    result = run(project)
    assert result.unsolved.get("cmp.fasteners#x_bad") == "under-determined"
    assert "cmp.fasteners#x_bad" not in result.values
    assert "cmp.fasteners#y_bad" not in result.values


def test_plan_targets_are_all_valueless(gearbox) -> None:
    plan = build_plan(gearbox)
    for pid in plan.unsolved_params:
        assert gearbox.params[pid].value is None
    for step in plan.steps:
        assert gearbox.params[step.target_id].value is None
