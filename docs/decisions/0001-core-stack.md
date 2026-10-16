# 0001. Core stack

- Status: Accepted
- Date: M0

## Context

The core must express a typed, unit-aware graph; solve and propagate it
deterministically; and expose it to a UI. The engine must be domain-agnostic
(P8) and reproducible (P9). The LLM sits outside the numeric path (P2).

## Decision

The core stack is a Python engine plus a FastAPI server, with a TypeScript
React UI.

- Python engine: `sympy` (symbolic equations and inverses), `pint` (units),
  `networkx` (graph and dependents), `scipy` (numeric solve and iteration).
- Server: FastAPI.
- UI: TypeScript React.

## Consequences

- The engine is a library with a thin server on top; the UI is a separate
  consumer of the server API.
- Symbolic and numeric routes share one relation representation, matching the
  solver strategy ladder.
- Provenance, units and review status live in the engine, so they hold for
  every client.
