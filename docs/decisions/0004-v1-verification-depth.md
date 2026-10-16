# 0004. v1 verification depth

- Status: Accepted
- Date: M0

## Context

v1 targets core workflows across mechanical, civil, electrical and
electronics engineering. Domains were listed, not a verification depth.
Choosing the smallest depth that still delivers the thesis keeps the core
shippable.

## Decision

v1 verification depth is: equations, units, constraints, sensitivities, and
manual test entry.

The solver verifies: each relation is dimensionally consistent (units), each
constraint is evaluated, and each target is solved with a recorded derivation
chain. Sensitivities are computed. Test results are entered manually.

## Consequences

- CAD generation and simulation (FEA, CFD, SPICE) are out of v1 and arrive
  later through adapters (M3).
- No time-domain simulation in v1.
- Depth is limited to what closed-form and coupled relations can express; see
  the solver specification.
