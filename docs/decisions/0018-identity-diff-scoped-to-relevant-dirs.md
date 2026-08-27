# ADR 0018 — The run-identity diff is scoped to RELEVANT_DIRS

- **Status:** accepted
- **Date:** 2026-08-19
- **Affects:** `src/perp_lab/tracking/identity.py::worktree_state`
- **Depends on:** ADR 0006 (run tracking)

## Context

A run's identity is commit + config + data hashes + a hash of everything
uncommitted. Until this ADR, the uncommitted part was asymmetric: untracked
files were filtered to `RELEVANT_DIRS = ("src", "tests", "configs",
"docs/methodology")`, but the diff of tracked files hashed `git diff HEAD`
over the **whole tree**.

The consequence was measured, not hypothetical. On 2026-08-17 the running
CRT_INTRADAY_V1 round was invalidated three times by edits that could not
change a single line of executed code — landing-page components under
`apps/web/` and documentation outside the methodology contract. Each time the
fingerprint flipped, resume refused to continue, and ~23 completed compute
units were discarded to keep provenance honest
(`artifacts/runs/crt_v1_budget100/_DESCARTADO_huella_arbol_sucio/POR_QUE.md`).

## Decision

`worktree_state` computes the tracked diff as
`git diff HEAD -- src tests configs docs/methodology` — the same scope the
untracked scan has always used. A change outside those directories no longer
alters `diff_sha256`, `dirty`, or `reproducible_from_commit_alone`.

`tests/unit/test_identity_scope.py` pins the property in both directions on a
throwaway repository: edits under `apps/web/` and plain `docs/` leave the
fingerprint untouched; edits and untracked files under `src/` flip it; and
`docs/methodology/` remains part of the contract while sibling docs do not.

## Consequences

- Web and documentation work can proceed while a round is running. The
  operational workaround this replaces — every edit exiled to a git worktree
  until a round finished — is no longer required for correctness, though
  worktrees remain useful for isolation.
- Fingerprints computed before and after this change are not comparable when
  the tree carried out-of-scope modifications at run time. Historical runs are
  unaffected: every retained study in `artifacts/runs/` was produced from a
  clean tree (`git_dirty: false` in their checkpoints), where both definitions
  coincide.
- The scope list itself is now load-bearing in two places. Anything added to
  `RELEVANT_DIRS` widens both the untracked scan and the diff consistently.
