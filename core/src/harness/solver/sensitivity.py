from __future__ import annotations

from collections.abc import Callable

import sympy as sp

from ..units import units as u
from .topology import CoupledGroup


def step_sensitivities(
    solved_expr: sp.Expr,
    symbol_to_param: dict[str, str],
    si_inputs: dict[str, float],
    target_id: str,
) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for s in sorted(solved_expr.free_symbols, key=str):
        name = str(s)
        if name not in symbol_to_param:
            continue
        derivative = sp.diff(solved_expr, s)
        try:
            value = u.evaluate_expression(derivative, si_inputs)
        except u.UnitError:
            continue
        out[(target_id, symbol_to_param[name])] = value
    return out


def coupled_sensitivities(
    group: CoupledGroup,
    resolve: Callable[[dict[str, float]], dict[str, float]],
    base_si: dict[str, float],
    symbol_to_param: dict[str, str],
    param_ids: list[str],
) -> dict[tuple[str, str], float]:
    symbol_of = {pid: sym for sym, pid in symbol_to_param.items()}
    outputs = set(param_ids)
    out: dict[tuple[str, str], float] = {}
    for symbol in sorted(symbol_to_param):
        parameter_id = symbol_to_param[symbol]
        if parameter_id in outputs:
            continue
        base = base_si.get(symbol)
        if base is None:
            continue
        h = max(abs(base) * 1e-4, 1e-6)
        try:
            lower = resolve({**base_si, symbol: base - h})
            upper = resolve({**base_si, symbol: base + h})
        except u.UnitError:
            continue
        for out_id in sorted(outputs):
            out_symbol = symbol_of[out_id]
            low = lower.get(out_symbol)
            high = upper.get(out_symbol)
            if low is None or high is None:
                continue
            out[(out_id, parameter_id)] = (high - low) / (2 * h)
    return out
