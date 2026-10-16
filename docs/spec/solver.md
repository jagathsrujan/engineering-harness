# Specification: solver

Normative. Numbered rules are requirements. The solver is the only component
that produces numeric results (P2).

## 1. Propagation and locality

1.1 On an edit, mark dependents dirty and recompute only those.

1.2 The recompute set must equal the dependents of the edit, exactly (R5).

1.3 The LLM is invoked only where the solver cannot continue.

## 2. Solution strategy

2.1 Per target, follow a strategy ladder:

- explicit or analytic inverse;
- sympy symbolic solve;
- iterative fixed point for coupled loops.

2.2 Choose the earliest rung of the ladder that resolves the target.

## 3. Unsolved nodes

3.1 A node that cannot be solved is marked unsolved with a structured reason,
one of: `missing-inputs`, `under-determined`, `dimension-mismatch`,
`iteration-no-convergence`, `out-of-validity-domain`, `blocked-by-unknown`.

3.2 The solver never guesses silently. Unsolved means unsolved (R8).

3.3 A relation is evaluated only within its validity domain; a target whose
inputs fall outside the domain is unsolved with `out-of-validity-domain`.

## 4. Units

4.1 Units are mandatory and checked on every relation (P5).

4.2 A dimensionally inconsistent relation is rejected at load (R2).

4.3 Evaluation happens in SI base units. Results are converted back to each
parameter's declared unit.

4.4 Equations must be written unit-invariant in SI base units. Unit conversion
factors (for example rpm to rad/s) belong in the parameter's unit, not in the
equation. Engine-authored graph checks enforce this indirectly; violations
surface as dimensional mismatches or silently wrong factors in review.

4.5 Pure numeric factors in an equation (2*pi, 1e6, 0.7) are physical facts of
the model, not unit conversions.

## 5. Sensitivities

5.1 A sensitivity is the computed change in an output per unit change in an
input at the current operating point.

5.2 Compute sensitivities symbolically where possible, by finite difference
otherwise.

5.3 Sensitivities are solver outputs. They are never scores assigned by an LLM.

## 6. Determinism

6.1 Same graph plus same library versions gives identical numbers (R1, P9).

6.2 The numeric path uses sorted-id traversal, pinned lockfiles, and no
wall-clock or randomness.

6.3 Golden tests assert byte-stable results for a fixed input graph.

## 7. Drivers

7.1 Drivers sit above the solver: what-if sweeps, constraint search, and
optimization (later).
