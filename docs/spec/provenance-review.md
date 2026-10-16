# Specification: provenance and review

Normative. Numbered rules are requirements.

## 1. Provenance tags

1.1 A value carries exactly one of six tags:

| Tag | Meaning |
| --- | ------- |
| `stated` | Given by the user. |
| `computed` | Produced by the solver. |
| `looked-up` | Taken from a cited source. |
| `assumed` | A flagged default. |
| `estimated` | An unreviewed LLM suggestion. |
| `measured` | Taken from a test result. |

1.2 No value exists without a tag (R3).

1.3 `looked-up` requires a cited source.

1.4 `estimated` marks an unreviewed LLM suggestion. It is never treated as
verified.

1.5 `measured` comes from test-result nodes and may recalibrate parameters.

## 2. Weakest-provenance propagation

2.1 A computed value inherits the weakest provenance among its inputs.

2.2 The weakest order, from weakest to strongest, is:
`estimated < assumed < looked-up < stated < measured`.

2.3 A computed value is tagged `computed` and records `inherited_weakest`.

2.4 Weakest-provenance propagation holds for every computed value (R4).

2.5 Anything derived from an assumed value is visibly assumption-dependent.

## 3. Review status

3.1 Each relation is `unreviewed`, `reviewed` (with reviewer, timestamp and
graph version) or `disputed`.

3.2 Only humans change review status. No applied change is ever counted as
reviewed without a human (hard floor A2a).

3.3 A value may be shown as verified only when every relation upstream of it
(its recorded derivation chain) is reviewed and no Unknown node blocks it.

3.4 Unreviewed and assumed values must be visually prominent. A clean graph
must not look more authoritative than it is.

## 4. Interaction with the solver

4.1 An unresolved Unknown does not stop propagation; it blocks the VERIFIED
condition in 3.3 on the values in its `blocks` list and on everything
derivation-downstream of them. `blocked-by-unknown` is a reserved unsolved
reason (see `docs/spec/solver.md`) for adapter paths that cannot proceed at all.

4.2 A disputed relation is not treated as reviewed for the verified condition
in 3.3.
