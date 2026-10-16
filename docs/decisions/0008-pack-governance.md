# 0008. Pack governance

- Status: Accepted
- Date: M0

## Context

Community packs will vary in quality, and formula selection is the main risk
in the system. Packs supply relations, standards references, validators and
tool adapters (P8), so their quality bounds the trustworthiness of results.

## Decision

Pack governance has two tiers:

- First-party starter packs (mechanical, civil, electrical, electronics) are
  maintained in this repository.
- Community packs arrive by pull request and pass a mandatory evaluation gate
  before they are listed.

The evaluation gate requires a pack to load, pass `harness verify`, and meet
the evaluation suite for its domain (paraphrase invariance, R6, and
propagation correctness against hand calculations).

## Consequences

- A pack is not listed until it passes the gate; this keeps an unvetted pack
  from looking authoritative.
- Pack authors cite their sources; formula choice, validity domain and source
  reference are all reviewable.
- Standards are cited by clause number; copyrighted text is not reproduced,
  and cited data must carry a source column.
