# 0002. Local-first web app

- Status: Accepted
- Date: M0

## Context

Designs are plain text and diffable (P10), and the database is a working copy,
not the only copy. Engineers need the immediacy of an interactive tool without
surrendering ownership of their files.

## Decision

The product is a local-first web app. Files on disk are canonical. A SQLite
mirror is a rebuildable cache for the live application.

## Consequences

- The graph is loaded from and written back to plain-text files; the SQLite
  mirror can be deleted and rebuilt at any time.
- No change may exist only in the database.
- The app can run on a single machine with no server round-trip to a hosted
  service.
- Git remains the version and diff surface (see 0007).
