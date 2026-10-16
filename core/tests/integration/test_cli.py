from __future__ import annotations

import json
from pathlib import Path

from conftest import GEARBOX
from harness import cli


def test_cli_load(gearbox_root: Path, capsys) -> None:
    assert cli.main(["load", str(gearbox_root)]) == 0
    out = capsys.readouterr().out
    assert "components=5" in out
    assert "parameters=32" in out


def test_cli_solve(capsys) -> None:
    assert cli.main(["solve", str(GEARBOX)]) == 0
    out = capsys.readouterr().out
    assert "solved prj.gearbox-demo" in out
    assert "UNSOLVED" not in out


def test_cli_report_json(capsys) -> None:
    assert cli.main(["report", "--json", str(GEARBOX)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["project_id"] == "prj.gearbox-demo"
    assert len(payload["parameters"]) == 32


def test_cli_verify_exits_nonzero_on_violation(capsys) -> None:
    assert cli.main(["verify", str(GEARBOX)]) == 1
    out = capsys.readouterr().out
    assert "VIOLATED" in out


def test_cli_undo_without_history(capsys) -> None:
    assert cli.main(["undo", str(GEARBOX)]) in (0, 1)
    out = capsys.readouterr().out
    assert ("undid change" in out) or ("nothing to undo" in out)


def test_cli_sweep(capsys) -> None:
    assert cli.main(["sweep", str(GEARBOX), "cmp.drive-motor#p_in", "--start", "5", "--stop", "7", "--steps", "2"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    records = [json.loads(x) for x in lines]
    assert records[0]["swept_value"] == 5.0
    assert records[-1]["swept_value"] == 7.0


def test_cli_load_failure_exits_two(capsys) -> None:
    assert cli.main(["load", "/tmp/does-not-exist-harness-project"]) == 2
    assert "load failed" in capsys.readouterr().err
