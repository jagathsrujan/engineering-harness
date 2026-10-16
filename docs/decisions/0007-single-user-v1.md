# 0007. Single-user v1

- Status: Accepted
- Date: M0

## Context

Multi-user collaboration was an open question (Q7). Concurrent editing of
shared state would add presence, locking and conflict resolution to the core
before the solver and graph format are stable.

## Decision

v1 is single-user. Git is the collaboration story.

## Consequences

- The app assumes one writer at a time; there is no presence or live
  multi-cursor editing.
- Sharing, review and history use git branches and diffs over the plain-text
  graph (P10).
- Collaboration features are deferred; the M4 milestone covers collaboration,
  SysML v2 import and export.
