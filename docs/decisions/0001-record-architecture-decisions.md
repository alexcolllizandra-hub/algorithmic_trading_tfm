# ADR 0001: Record architecture decisions

- Status: Accepted
- Date: 2026-07-30

## Context

The thesis must be reproducible and its design choices auditable. Decisions
(data source, timeframes, holdout policy, tooling) evolve as the project
progresses and need a durable, reviewable record.

## Decision

We keep lightweight Architecture Decision Records (ADRs) in `docs/decisions/`,
one Markdown file per decision, numbered sequentially. Each records context,
the decision, and its consequences. Data-contract changes must reference an ADR.

## Consequences

- Every significant, hard-to-reverse choice is documented with its rationale.
- Reviewers (and the thesis defense) can trace *why* the project is built the
  way it is, not just *what* it does.
