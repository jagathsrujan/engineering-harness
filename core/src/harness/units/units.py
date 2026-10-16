from __future__ import annotations

import math
import re

import sympy as sp
from pint import UnitRegistry

_REG = UnitRegistry()

_CONSTANTS: dict[str, object] = {"pi": sp.pi, "e": sp.E, "inf": sp.oo}


class UnitError(ValueError):
    pass


def unit_of(text: str):
    try:
        return _REG.Unit(text)
    except Exception as err:
        raise UnitError(f"cannot parse unit {text!r}: {err}") from err


def dimensionality(text: str):
    unit = unit_of(text)
    return unit.dimensionality


def dimension_expr(text: str) -> sp.Expr:
    if not text:
        return sp.Integer(1)
    container = dimensionality(text)
    expr: sp.Expr = sp.Integer(1)
    for dim, exponent in container.items():
        name = "D_" + re.sub(r"[^A-Za-z0-9_]", "_", str(dim).strip("[]"))
        if exponent != 0:
            expr = expr * sp.Symbol(name, positive=True) ** sp.Integer(exponent)
    return sp.expand(expr)


def parse_side(text: str, symbols: dict[str, sp.Symbol]) -> sp.Expr:
    local = {**_CONSTANTS, **symbols}
    try:
        expr = sp.parse_expr(text, local_dict=local)
    except (SyntaxError, TypeError, ValueError) as err:
        raise UnitError(f"cannot parse expression {text!r}: {err}") from err
    if (
        expr.free_symbols
        - set(local.values())
        - {_CONSTANTS[k] for k in _CONSTANTS if isinstance(_CONSTANTS[k], sp.Basic)}
    ):
        unknown = {str(s) for s in expr.free_symbols if s not in set(local.values())}
        raise UnitError(f"expression {text!r} uses unknown symbols {sorted(unknown)}")
    return expr


def parse_equation(text: str, symbols: dict[str, sp.Symbol]) -> tuple[sp.Expr, sp.Expr]:
    parts = [p.strip() for p in text.split("=")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise UnitError(f"equation {text!r} must have exactly one '=' separating two sides")
    return parse_side(parts[0], symbols), parse_side(parts[1], symbols)


def parse_boolean(text: str, symbols: dict[str, sp.Symbol]) -> sp.Basic:
    expr = parse_side(text, symbols)
    if not isinstance(expr, (sp.core.relational.Relational,)) and not expr.is_Boolean:
        raise UnitError(f"expression {text!r} must be a boolean condition")
    return expr


def dimensions_of(expr: sp.Expr, symbol_units: dict[str, str]) -> sp.Expr:
    mapping = {}
    for s in expr.free_symbols:
        name = str(s)
        if name in symbol_units:
            mapping[s] = dimension_expr(symbol_units[name])
        else:
            mapping[s] = sp.Integer(1)
    return sp.simplify(sp.expand(expr.subs(mapping)))


def check_equation_dimensions(lhs: sp.Expr, rhs: sp.Expr, symbol_units: dict[str, str]) -> None:
    lhs_dim = dimensions_of(lhs, symbol_units)
    rhs_dim = dimensions_of(rhs, symbol_units)
    if rhs_dim == 0:
        raise UnitError("right-hand side is identically zero")
    ratio = sp.simplify(lhs_dim / rhs_dim)
    dim_symbols = set(lhs_dim.free_symbols) | set(rhs_dim.free_symbols)
    if ratio.free_symbols & dim_symbols:
        raise UnitError(f"dimensional mismatch: left {lhs_dim} vs right {rhs_dim}")


def si_value(value: float, unit_text: str) -> float:
    if not unit_text:
        return float(value)
    try:
        return float(_REG.Quantity(value, unit_text).to_base_units().magnitude)
    except Exception as err:
        raise UnitError(f"cannot convert {value} {unit_text!r} to SI: {err}") from err


def from_si(value: float, unit_text: str) -> float:
    if not unit_text:
        return float(value)
    try:
        base = _REG.Quantity(1.0, unit_text).to_base_units()
        return float(_REG.Quantity(value, base.units).to(unit_text).magnitude)
    except Exception as err:
        raise UnitError(f"cannot convert SI value {value} unit {unit_text!r}: {err}") from err


def evaluate_expression(expr: sp.Expr, si_values: dict[str, float]) -> float:
    names = sorted({str(s) for s in expr.free_symbols})
    missing = [n for n in names if n not in si_values]
    if missing:
        raise UnitError(f"missing input values for {missing}")
    subs_symbols = [sp.Symbol(n) for n in names]
    func = sp.lambdify(subs_symbols, expr, modules=["math"])
    try:
        result = float(func(*[float(si_values[n]) for n in names]))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as err:
        raise UnitError(f"cannot evaluate expression: {err}") from err
    if not math.isfinite(result):
        raise UnitError("expression evaluated to a non-finite value")
    return result


def evaluate_boolean(expr: sp.Basic, si_values: dict[str, float]) -> bool:
    mapping = {}
    undetermined = []
    for s in expr.free_symbols:
        name = str(s)
        if name in si_values:
            mapping[s] = float(si_values[name])
        else:
            undetermined.append(name)
    if undetermined:
        raise UnitError(f"condition has undetermined symbols {sorted(undetermined)}")
    try:
        return bool(expr.subs(mapping))
    except TypeError as err:
        raise UnitError(f"cannot evaluate boolean {expr!r}: {err}") from err
