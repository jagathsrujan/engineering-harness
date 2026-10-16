# 0010. Naming deferred

- Status: Accepted
- Date: M0

## Context

The project name and license were open questions (Q1). The license is settled
(0003). The public name is not, and publishing under a name that collides with
an existing project would be costly to reverse.

## Decision

Naming is deferred. The internal package name is `harness`. The public name
shortlist is Torsion, Kerf and Truss. Candidate handles are to be verified
before the first publish.

## Consequences

- All code, imports and docs use `harness`; the package name is internal and
  user-invisible.
- No public handle, domain or package registry name is claimed yet.
- The first publish is gated on a handle-availability check across the
  shortlist.
- A rename to the chosen public name is a documentation and packaging change,
  not a format change.
