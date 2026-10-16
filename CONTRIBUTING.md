# Contributing

Thanks for contributing to `harness`. This document states the working rules
for code, packs and documentation.

## Getting set up

Requires Python >= 3.12, managed with [uv](https://docs.astral.sh/uv/).

```
uv sync --directory core
uv run --directory core harness verify ../projects/gearbox-demo
```

`harness verify` exits non-zero on any R1-R9 violation.

## Pull requests

- One focused change per pull request, with a clear problem statement and scope.
- Describe the design impact: which graph nodes, relations or constraints change.
- Keep the diff reviewable. Do not mix refactors with behaviour changes.
- Reference the requirement or decision the change serves (R1-R9, D1-D10).
- A change is not merged until it is reviewed by a human maintainer.

## Tests are required

- Every behaviour change ships with tests. No test, no merge.
- Solver, unit and provenance changes must include a golden test: fixed input
  graph plus pinned library versions give a byte-stable result (R1, R9).
- Tests for R2-R5 must assert the failure mode, not only the happy path: a
  dimensionally inconsistent relation is rejected (R2), a value without a
  provenance tag is refused (R3), a computed value carries the weakest
  provenance of its inputs (R4), and the recompute set equals the dependents of
  the edit (R5).
- `harness verify` must pass on the repository demo projects before review.

## Human relation review

- Only humans change a relation's review status. No change the LLM applies is
  ever counted as reviewed without a human (hard floor A2a).
- A value may be shown as verified only when every relation upstream of it is
  reviewed and no Unknown node blocks it.
- Reviewers record who reviewed, when, and against which graph version.
- Do not mark a relation reviewed to silence a warning. Reviewer fatigue
  erodes the meaning of review status; treat it as a real gate.

## Pack evaluation gate

- First-party starter packs are maintained in this repository.
- Community packs arrive by pull request and pass a mandatory evaluation gate
  before they are listed: the pack must load, pass `harness verify`, and meet
  the evaluation suite for its domain (R6 paraphrase invariance and
  propagation correctness against hand calculations).
- Pack authors cite their sources. Relation library entries are reviewable:
  formula choice, validity domain and source reference are all part of the
  review.
- Packs may cite a standard by clause number and encode their own formulation.
  Do not reproduce copyrighted standard text, tables or figures. Cited
  material properties and data tables must carry a source column.

## Graph files stay plain text

- Graph serialization is plain-text YAML, one file per component, designed for
  git diffs (P10). Pull requests must keep it that way.
- Do not reformat unrelated YAML, reorder keys gratuitously, or introduce
  encoding or line-ending churn. A graph diff should show the engineering
  change and nothing else.
- Stable ids are never reused. See `docs/spec/graph-format.md`.
- The database mirror is a rebuildable cache; the files on disk are canonical.
  Never make a change that exists only in the database.

## Documentation and decisions

- Substantive design changes are recorded as short ADRs under
  `docs/decisions/`, in the Status / Context / Decision / Consequences form.
- Specification language is normative and numbered where it states rules.

## Code of conduct

Participation is governed by `CODE_OF_CONDUCT.md`.
