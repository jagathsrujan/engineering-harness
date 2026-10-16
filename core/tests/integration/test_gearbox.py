from __future__ import annotations

from pathlib import Path

import pytest

from conftest import temp_copy
from harness.graph.io import load_project
from harness.history.journal import apply_test_result
from harness.persistence import mirror
from harness.solver.report import build_report, format_report, report_to_dict, verify_exit_code
from harness.solver.solve import run


def test_gearbox_solves_with_flags(gearbox) -> None:
    result = run(gearbox)
    assert not result.unsolved
    report = build_report(gearbox, result)

    tooth = {row.id: row for row in report.requirements}["rq.tooth-safety"]
    shaft = {row.id: row for row in report.requirements}["rq.shaft-safety"]
    life = {row.id: row for row in report.requirements}["rq.bearing-life"]
    assert tooth.satisfied is True
    assert shaft.satisfied is True
    assert life.satisfied is True

    envelope = {row.id: row for row in report.constraints}["cs.shaft-envelope"]
    assert envelope.satisfied is False

    assert verify_exit_code(report) == 1


def test_verified_gate_respects_reviews(gearbox) -> None:
    result = run(gearbox)
    report = build_report(gearbox, result)
    by_id = {row.id: row for row in report.params}
    assert by_id["cmp.drive-motor#omega_in"].verified is True
    assert by_id["cmp.gear-stage#d1"].verified is True
    assert by_id["cmp.gear-stage#p_out"].verified is False
    assert by_id["cmp.bearing-1#h_life"].verified is False
    assert by_id["cmp.bearing-1#n_out"].verified is True


def test_unknown_blocks_verified_status(gearbox) -> None:
    result = run(gearbox)
    assert result.values.get("cmp.bearing-1#h_life") is not None
    report = build_report(gearbox, result)
    by_id = {row.id: row for row in report.params}
    assert by_id["cmp.bearing-1#h_life"].verified is False


def test_disputed_relation_never_verifies_downstream(gearbox) -> None:
    result = run(gearbox)
    assert gearbox.relations["rl.gear-force"].review.status == "disputed"
    report = build_report(gearbox, result)
    by_id = {row.id: row for row in report.params}
    assert by_id["cmp.gear-stage#f_t"].verified is False
    assert by_id["cmp.shaft-1#sigma_e"].verified is False


def test_report_text_is_renderable(gearbox) -> None:
    result = run(gearbox)
    text = format_report(build_report(gearbox, result))
    assert "VIOLATED" in text
    assert "UNKNOWNS" in text
    assert "TEST RESULTS" in text
    payload = report_to_dict(build_report(gearbox, result))
    assert payload["project_id"] == "prj.gearbox-demo"


def test_mirror_rebuild_counts_nodes(gearbox) -> None:
    db = mirror.rebuild(gearbox)
    assert mirror.count_nodes(db) == gearbox.total_nodes()


def test_apply_test_result_and_undo_end_to_end(gearbox_root: Path, tmp_path: Path) -> None:
    project = load_project(temp_copy(gearbox_root, tmp_path))
    before = run(project).values
    assert apply_test_result(project, "tr.rig-eta") is not None
    after = run(project, edited={"cmp.gear-stage#eta"}).values
    assert after["cmp.gear-stage#p_out"] == pytest.approx(0.93 * 5.0)

    from harness.history.journal import Journal

    assert Journal(project).undo() is not None
    restored = load_project(project.root)
    assert run(restored).values == pytest.approx(before, rel=1e-12)
