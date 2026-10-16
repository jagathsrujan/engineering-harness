from __future__ import annotations

import pytest

from harness.graph.ids import IdKind, is_kind, kind_of


@pytest.mark.parametrize(
    "node_id,expected",
    [
        ("cmp.gearbox", IdKind.COMPONENT),
        ("cmp.gear-stage-a1", IdKind.COMPONENT),
        ("cmp.shaft-1#d", IdKind.PARAMETER),
        ("cmp.x#p_out", IdKind.PARAMETER),
        ("cmp.shaft-1#p-port-torque", IdKind.PARAMETER),
        ("rl.shaft-bending", IdKind.RELATION),
        ("cs.envelope-1", IdKind.CONSTRAINT),
        ("rq.bearing-life", IdKind.REQUIREMENT),
        ("dc.mounting", IdKind.DECISION),
        ("uk.lubrication", IdKind.UNKNOWN),
        ("tr.rig-eta", IdKind.TEST_RESULT),
    ],
)
def test_kind_of_accepts_valid_ids(node_id: str, expected: IdKind) -> None:
    assert kind_of(node_id) == expected


@pytest.mark.parametrize(
    "node_id",
    [
        "cmp.Upper",
        "cmp.gear stage",
        "cmp.gearbox#D_underscore_cap",
        "rl.REL",
        "bogus.shaft",
        "cmp.gearbox#1st",
        "cmp#gear",
        "cmp.gearbox#",
    ],
)
def test_kind_of_rejects_bad_ids(node_id: str) -> None:
    with pytest.raises(ValueError):
        kind_of(node_id)


def test_is_kind_is_total() -> None:
    assert is_kind("cmp.gearbox#d", IdKind.PARAMETER)
    assert not is_kind("cmp.gearbox#d", IdKind.COMPONENT)
    assert not is_kind("not-an-id", IdKind.PARAMETER)
