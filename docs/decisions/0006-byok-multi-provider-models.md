# 0006. BYOK multi-provider models

- Status: Accepted
- Date: M0

## Context

The project must work with local or offline models for proprietary designs
(Q3), and changing the model must never change the numbers (R9). A single
hosted provider would couple the tool to one vendor and one network path.

## Decision

Model access is bring-your-own-key and multi-provider. DeepSeek is the first
provider wired up. Providers are interchangeable behind one client interface.

## Consequences

- Users supply their own API keys; the project does not host model access.
- Local and offline providers are reachable through the same interface.
- The numeric path never depends on the chosen model, so R9 holds by
  construction.
- Model choice affects only proposal quality, never computed values.
