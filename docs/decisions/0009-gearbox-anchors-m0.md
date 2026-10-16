# 0009. Gearbox anchors M0

- Status: Accepted
- Date: M0

## Context

The M0 milestone is a schema and solver spike that must exercise parameters,
units, relations, constraints and provenance end to end. Which worked example
anchors each domain was an open question (Q6).

## Decision

A mechanical gearbox demonstration anchors M0. It carries roughly 29
parameters and is the input to the R-gate tests.

## Consequences

- Every M0 deliverable is demonstrated on the gearbox graph: load, solve,
  report, verify and undo.
- The `gearbox-demo` project under `projects/` is the canonical worked example
  for the CLI and the quickstart.
- Anchors for the other domains are chosen alongside their packs (M2).
