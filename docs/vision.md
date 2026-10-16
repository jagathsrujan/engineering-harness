# Vision

## Intent in one paragraph

We are building an open-source harness in which an engineering design lives as
a typed, unit-aware graph of parameters, relations, constraints and decisions,
not as prose or code. A person or an LLM changes the design by editing the
graph. A deterministic solver propagates the change. The LLM is used only for
what arithmetic cannot decide: proposing structure, selecting and justifying
formulas, translating intent into graph edits, and flagging gaps. Every value
and every relation carries provenance, so a human can see what was stated,
computed, assumed or guessed, and why. Version 1 targets core workflows in
mechanical, civil, electrical and electronics engineering.

## The problem

1. Coding harnesses assume the unit of work is a file and a diff, and that
   passing tests means done. In engineering the unit of work is a parameter or
   a relationship, and a wrong answer shows up as a physical failure after
   money has been spent on material, printing or machining.
2. Prose is a poor source of truth. It is not canonical; it cannot be diffed
   meaningfully; and every change forces the model to re-read and re-interpret
   a large context, which costs tokens and invites drift.
3. Prose hides uncertainty. Assumptions, guesses and looked-up values read the
   same as verified ones.
4. The failures that matter most are not arithmetic. Formula selection and
   fabricated constants are larger problems than computation slips.

## Principles (normative)

- **P1. The graph is the source of truth.** Chat, documents and drawings are
  views or inputs.
- **P2. Numbers come from code.** The LLM never produces a computed value
  directly; it calls the solver.
- **P3. The LLM proposes; the project's autonomy setting decides what it may
  apply.**
- **P4. Every value and relation has provenance and a review status.**
- **P5. Units are mandatory** and checked on every relation.
- **P6. Edits are local.** A change recomputes only its dependents, and the
  LLM is invoked only where the solver cannot continue.
- **P7. Relations are declared, not directed**, wherever possible (acausal).
  Direction is a solver decision, not a modeling decision.
- **P8. The core is domain-agnostic.** Disciplines plug in as packs of
  relations, standards references, validators and tool adapters.
- **P9. Reproducible.** Same graph plus same library versions gives the same
  numbers.
- **P10. Plain-text, git-diffable serialization.** The database is a working
  copy, not the only copy.

## Scope

**Users.** Engineers, students and makers who want auditable design reasoning,
and contributors who write domain packs.

**In v1.** Core workflows in mechanical, civil, electrical and electronics
engineering. Verification depth for v1 is equations, units, constraints,
sensitivities, and manual entry of test results. CAD generation and simulation
(FEA, CFD, SPICE) arrive through adapters after the core is stable.

**Non-goals.** Replacing CAD, FEA or SPICE tools. Professional sign-off or code
certification. Autonomous release to manufacturing. Being a general coding
agent.
