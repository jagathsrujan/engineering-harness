from __future__ import annotations

import math
from pathlib import Path

import pytest

from harness.graph.io import load_project
from harness.graph.model import GraphError

REPO = Path(__file__).parents[2]
GEARBOX = REPO / "projects" / "gearbox-demo"


@pytest.fixture(scope="session")
def gearbox_root() -> Path:
    return GEARBOX


@pytest.fixture()
def gearbox(gearbox_root: Path):
    return load_project(gearbox_root)


def temp_copy(gearbox_root: Path, tmp_path: Path) -> Path:
    import shutil

    target = tmp_path / "gearbox-copy"
    shutil.copytree(gearbox_root, target)
    return target


@pytest.fixture(scope="session")
def expects() -> dict[str, float]:
    p_in = 5.0
    eta = 0.95
    n_in_rpm = 1450.0
    z1, z2, m_module, b1 = 17.0, 43.0, 4.0, 28.0
    d_shaft, lever_a = 25.0, 40.0
    sigma_flim, y_f, sigma_y = 220.0, 2.8, 650.0
    c_bear_kn = 19.5
    a_s, sigma_y_bolt = 58.0, 640.0

    omega_in = n_in_rpm * 2 * math.pi / 60
    p_out = eta * p_in
    i = z2 / z1
    d1 = m_module * z1
    t1 = p_out * 1e3 / omega_in
    f_t = 2 * t1 / (d1 * 1e-3)
    sigma_f = f_t * y_f / (m_module * 1e-3 * b1 * 1e-3) / 1e6
    s_f = sigma_flim / sigma_f
    m_b = f_t * lever_a * 1e-3
    sigma_b = 32 * m_b / (math.pi * (d_shaft * 1e-3) ** 3) / 1e6
    tau = 16 * t1 / (math.pi * (d_shaft * 1e-3) ** 3) / 1e6
    sigma_e = math.sqrt((sigma_b * 1e6) ** 2 + 3 * (tau * 1e6) ** 2) / 1e6
    n_sf = sigma_y / sigma_e
    n_out = n_in_rpm / i
    l10_rad = 2 * math.pi * 1e6 * ((c_bear_kn * 1e3) / f_t) ** 3
    h_life = l10_rad / (n_out * 2 * math.pi / 60) / 3600
    f_i = 0.7 * a_s * sigma_y_bolt
    return {
        "cmp.drive-motor#omega_in": omega_in,
        "cmp.gear-stage#p_out": p_out,
        "cmp.gear-stage#i": i,
        "cmp.gear-stage#d1": d1,
        "cmp.gear-stage#t1": t1,
        "cmp.gear-stage#f_t": f_t,
        "cmp.gear-stage#sigma_f": sigma_f,
        "cmp.gear-stage#s_f": s_f,
        "cmp.shaft-1#m_b": m_b,
        "cmp.shaft-1#sigma_b": sigma_b,
        "cmp.shaft-1#tau": tau,
        "cmp.shaft-1#sigma_e": sigma_e,
        "cmp.shaft-1#n_sf": n_sf,
        "cmp.bearing-1#n_out": n_out,
        "cmp.bearing-1#l10": l10_rad,
        "cmp.bearing-1#h_life": h_life,
        "cmp.fasteners#f_i": f_i,
    }


__all__ = ["GEARBOX", "REPO", "GraphError", "expects", "gearbox", "gearbox_root", "temp_copy"]
