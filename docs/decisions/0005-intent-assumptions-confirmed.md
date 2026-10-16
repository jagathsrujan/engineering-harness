# 0005. Intent assumptions A2-A6 confirmed

- Status: Accepted
- Date: M0

## Context

The intent draft carried assumptions A2-A6, marked for confirmation. Each one
shapes the core contract and the test gates, so they are confirmed as written
before M0.

## Decision

Assumptions A2-A6 are confirmed as written:

- A2. The hard autonomy floors apply at every level: a new or changed relation
  is never counted as reviewed without a human; nothing is shown as verified
  without human review; every applied change is one undoable commit with a
  diff; the LLM cannot change the autonomy setting or the constraints that
  bound it.
- A3. Weakest-provenance propagation is the rule.
- A4. Plain-text serialization with a database mirror.
- A5. No time-domain simulation in v1.
- A6. SysML v2 import and export is a later feature, not v1.

## Consequences

- These become normative: A2a in the review rules, A3 as R4, A4 as P10, A5 in
  0004, A6 in the M4 milestone.
- Changing any of them later requires a superseding ADR.
