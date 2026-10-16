# Pull request

## What changed

<!-- One or two sentences: which module or milestone (M0..M4) this touches. -->

## Relation review status

- [ ] Any new or changed Relation/Constraint/Requirement carries `review: { status: unreviewed }` or is reviewed **by a human**, named in the review block.
- [ ] No applied change is now counted as reviewed without a human (hard floor A2a).

## Provenance and units

- [ ] Every new Parameter has a provenance tag (R3).
- [ ] Every new Relation is unit-checked; a dimensionally inconsistent relation is rejected at load (R2).
- [ ] Computed values inherit the weakest provenance of their inputs (R4).

## Verification

- [ ] `uv run pytest -q` passes locally.
- [ ] `uv run mypy` and `uv run ruff check .` pass.
- [ ] If the change affects the solver or serializer: `uv run harness verify ../projects/gearbox-demo` output reviewed (expected exit 1 due to the deliberately violated demo constraint).
- [ ] New domain pack content (M2+) triggers the evaluation suite before merge.

## Notes for the reviewer

<!-- Citations for any newly encoded formulas, and the rationale for validity domains. -->
