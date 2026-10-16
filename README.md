# harness

An open-source harness in which an engineering design lives as a typed,
unit-aware graph of parameters, relations, constraints and decisions, not as
prose or code. A person or an LLM changes the design by editing the graph; a
deterministic solver propagates the change; the LLM never produces a computed
value. Every value and relation carries provenance (stated / computed /
looked-up / assumed / estimated / measured) and a review status, so a human can
see what was verified and why.

Version 1 targets core workflows in mechanical, civil, electrical and
electronics engineering. The public project name is deferred; `harness` is the
internal package name (shortlist: Torsion, Kerf, Truss).

## Principles

| Id | Principle |
| -- | --------- |
| P1 | The graph is the source of truth. |
| P2 | Numbers come from code (the solver) only. |
| P3 | The LLM proposes; the autonomy setting decides what it may apply. |
| P4 | Every value and relation has provenance and a review status. |
| P5 | Units are mandatory and checked on every relation. |
| P6 | Edits are local: only dependents are recomputed. |
| P7 | Relations are declared, not directed (acausal). |
| P8 | The core is domain-agnostic; disciplines plug in as packs. |
| P9 | Reproducible: same graph plus same library versions gives the same numbers. |
| P10 | Plain-text, git-diffable serialization. |

## Quickstart

Requires Python >= 3.12, managed with [uv](https://docs.astral.sh/uv/).

```
uv sync --directory core
uv run --directory core harness solve ../projects/gearbox-demo
```

On Windows, quote the paths.

## CLI (M0)

| Command | Purpose |
| ------- | ------- |
| `harness load <project>` | Load and validate a project graph. |
| `harness solve <project>` | Propagate and solve the graph. |
| `harness report <project>` | Report results (`--json` for machine output). |
| `harness verify <project>` | Check sweep (units, constraints, requirements, unknowns, review gating); non-zero exit on violations. |
| `harness undo <project>` | Revert the last applied change. |
| `harness sweep <project> <parameter> --start A --stop B --steps N` | What-if sweep over a parameter. |

## Repository layout

| Path | Contents |
| ---- | -------- |
| `core/` | Python engine (graph model, solver, CLI) and FastAPI server. |
| `packs/` | Domain packs (mechanical, civil, electrical, electronics), from M2. |
| `projects/` | Graphs, including the `gearbox-demo` worked example. |
| `docs/` | Vision, specifications and decisions. |
| `web/` | TypeScript React UI, from M1. |

## Testable requirements

- **R1 Determinism.** Same graph and library versions give identical numbers.
- **R2 Units.** A dimensionally inconsistent relation is rejected.
- **R3 Provenance.** No value exists without a tag.
- **R4 Weakest-provenance propagation** holds for every computed value.
- **R5 Locality.** The recompute set after an edit equals the dependents of that edit.
- **R6 Paraphrase invariance.** N paraphrases of one intent produce equivalent graphs; report the rate.
- **R7 Undo.** Every applied change can be reverted.
- **R8 No silent fallback.** Unsolved means unsolved.
- **R9 Model independence.** Changing the model never changes the numbers.

## Milestones

| Milestone | Scope |
| --------- | ----- |
| M0 | Schema and solver spike: core engine, the ~29-parameter gearbox demo, and R-gate tests. |
| M1 | Graph UI and chat-to-diff. |
| M2 | Pack format, four starter packs (mechanical, civil, electrical, electronics), evaluation suite. |
| M3 | Adapters: one geometry path and one simulation path. |
| M4 | Collaboration, SysML v2 subset import and export. |

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
