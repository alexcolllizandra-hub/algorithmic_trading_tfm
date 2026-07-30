---
name: register-decision
description: Record a significant project decision as an Architecture Decision Record under docs/decisions. Use when the user makes or changes a hard-to-reverse choice (data source, timeframes, holdout policy, tooling, methodology) in the perp-lab thesis.
disable-model-invocation: true
---

# Register decision (ADR)

## Workflow

1. Find the next number: inspect `docs/decisions/` (files are `NNNN-title.md`).
2. Create `docs/decisions/NNNN-short-title.md` using the template below.
3. If the decision changes the data contract, also bump its `version` and edit
   `configs/data_contract.yaml` + `docs/data_contract.md`.

## Template

```markdown
# ADR NNNN: <short title>

- Status: Accepted
- Date: <YYYY-MM-DD>

## Context
<Why a decision is needed; constraints and forces.>

## Decision
<What was decided, unambiguously.>

## Consequences
<Trade-offs, follow-ups, alternatives rejected and why.>
```

## Rules

- One decision per ADR. Keep it short and specific.
- Never delete an ADR; supersede it with a new one and mark the old as
  `Superseded by ADR NNNN`.
