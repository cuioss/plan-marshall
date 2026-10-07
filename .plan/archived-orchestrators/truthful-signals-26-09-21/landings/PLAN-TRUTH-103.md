# Landing: PLAN-TRUTH-103

**Outcome**: shipped · **PR**: [#1475](https://github.com/cuioss/plan-marshall/pull/1475) ·
**Merge commit**: `3103e9d6afa08697d5bab159afb09727882af1bc` (squash, via merge queue) · **Base**: `main`

## Ground-truth corroboration

The merge was verified first-party through `ci pr view --pr-number 1475`, not from the landing
message: `state: merged`, `merge_commit_sha: 3103e9d6afa08697d5bab159afb09727882af1bc`, title
`fix(permissions): stop modelling Write() as a live grant`, head `feature/plan-truth-103` → `main`.
The sha the plan reported and the sha the PR carries agree.

## What landed

The already-settled premise — Claude's file-permission checks consult `Edit(...)` only, so a
`Write(...)` allow rule grants nothing — was propagated to the three surfaces that still modelled
`Write` as live, or `.claude/settings.json` as the authoritative grant file.

- **16 write-intent matcher sites re-keyed** `Write(` → `Edit(` across 3 files. **12 of the 16 sit in
  `permission_doctor.py`'s `SUSPICIOUS_PATTERNS`, which a plain `Write(` search cannot find** because
  the patterns are regex-escaped there.
- **The audit was exactly inverted.** Its only high-severity filesystem-wide-*write* detector fired on
  `Write(/**)`, which grants nothing, while `Edit(/**)`, which genuinely grants filesystem-wide write,
  matched no pattern at all. The same inversion held one tier down for `Write(/tmp/` vs `Edit(/tmp/`.
- **Pruning could not reach the file whose entries take effect.** `resolve_settings_arg` now resolves
  the READ-preference selector. The operator chose the WIDE variant (all four subcommands sharing the
  helper); the six routed through `permission_common.get_settings_path` were deliberately not switched,
  and that four-vs-ten boundary is test-pinned rather than left to inference.
- **Before this plan, `Edit\(/` had ZERO hits across all 2793 test files** — nothing anywhere asserted
  the spelling that actually grants.

## Structural limit, carried forward deliberately

The premise itself is a claim about Claude's runtime that **no gate in this repository can verify** —
not the suite, not the quality gate, not CI. Every check in the PR is downstream of it. The plan
published this as its own PR-body section rather than leaving it implicit. That is the correct
handling and is recorded here so a later reader does not mistake the green checks for confirmation.

## Review

Four CodeRabbit rounds across three HEADs, converged. `proves: participation_only`.

| Round | HEAD | Findings |
|---|---|---|
| 1 | `11acd6452` | 4 (1 Major) — all fixed |
| 2 | `8dd5792e4` | 0 — edit-only publish, review object stale |
| 3 | `8081dfbf7` | 1 — the round-1 Major's own fix re-introduced the archetype |
| 4 | `2d37e3a35` | 0 — converged |

⭐⭐ **The sharpest datum: finding `3c3297` is the round-1 Major's own fix re-introducing the identical
mirrored-set archetype one layer down.** Neither a single gate pass nor a single review pass could
have seen it — only a later review round did. This is direct evidence for multi-round review over
single-pass gating.

⛔ Participation was verified from comment bodies **every round, never from the green check**: rounds 2
and 4 were edit-only publishes where the review object stayed stale, so a check-trusting run would
have read non-participation. `cuioss-review-bot` (required) participated on every HEAD, raised nothing,
and has no push trigger — stale after every push, needing three explicit triggers. `sourcery`
(optional) refused all rounds on a 7-day diff-character quota and never looked; its green check is a
check-level pass, not a review.

All 4 review escapes partitioned `gate_addressable`, **0 structural** — every one an archetype
`ext-self-review-plan-marshall` already enumerates, and two of them in `test/`, past two self-review
firings.

## Cost

6.6M tokens / 156M billing-weighted / 6h55m worked / 26h33m wall.
`6-finalize` alone: 4.39M tokens (**66%**), 3h12m worked, 18h34m wall.

The cost is the review loop, not the change: all 5 self-review findings and all 4 CodeRabbit findings
were real defects. But a self-review good enough to keep finding real defects is also expensive enough
to dominate the plan — and it spends a budget **shared** with the external tier (finding `265638`).

## Open defects recorded at drain

- ⛔ **The landing message carried no `landing-facts` block.** `inbox landing-check` returned
  `complete: false` with all 9 required keys missing (`schema`, `plan_id`, `pr`, `merge_state`,
  `cleanup_owed`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`). This is the
  known pre-fix prose-only landing shape; the facts were recoverable from prose and from the PR, but
  the drain reconciled by hand rather than machine-readably. `PLAN-TRUTH-149` owns this surface.
- ⛔ **The registry-pin repair is half-done and the remaining half is operator-only.** The marker half
  completed (unmarked == `['0.1.1655']` on all 10, double-sampled, zero errors, `.in_use` untouched);
  the registry half was refused by the permission classifier as Self-Modification and the plan stopped
  rather than working around it — the correct call. State is the SAFE half: pin stale at `0.1.1644`,
  sole unmarked dir correct at `0.1.1655`, and **the loader follows the unmarked dir, not the pin**.
  The dangerous inversion is the reverse order, which markers-first deliberately avoids.

## Findings routed to this epic

`265638` shared loop-back counter starves the external tier ·
`5cbc17` review_commitments clear over an empty population ·
`f0bd9d` head_sha_verified false negative on the comment path ·
`c8cccc` `--measured-diff-size ""` argparse rejection on the ordinary path ·
`10f565` unproven_bots includes optional bots ·
`3ee899` worktree-remove deletes the branch ref, making prune's remote half unreachable ·
`33858e` sync-plugin-cache re-opens the registry-pin gap ·
`7cca7f` the change-ledger is worktree-relative, so every worktree plan's build records are destroyed
at finalize ·
`cd5a69` plan-retrospective runs before record-metrics ·
`f03cdf` doc algorithm layer exists in no `.py` file ·
`5cf3c5` refine all-dimensions-100 confidence flag

Plus 11 candidate-lesson messages (`-001`…`-011`).

### The three the orchestrator flags as more than routine

- ⭐⭐⭐ **`7cca7f` — the change-ledger is worktree-relative and is destroyed at finalize.** Every
  worktree plan's build records die with its worktree. **This CORRECTS candidate-lesson `-001`**, which
  measured the same outage ("build oracle dead six days", last row `2026-09-07T20:55:15Z`) but recorded
  its root cause as *unknown* and offered two candidates — one of which would have sent someone
  bisecting an append path that works fine. The observation was right; the proposed remedy was not.
  ⛔ Do not action `-001`'s bisect proposal; `7cca7f` supersedes it. `-001`'s SECOND proposal survives
  and is independently valuable: a `build_count: 0` over a window in which the plan's own script log
  proves build invocations is a **distinguishable third state** — not "no builds ran", not
  "unavailable" — and should be an `error` finding.
- ⭐⭐⭐ **`265638` — the loop-back counter is shared across tiers.** A 6-round self-review consumed all
  5 iterations before any external review ran, and handling CodeRabbit's findings needed the ceiling
  raised twice. **The better self-review performs, the more likely it starves the external tier.** This
  is a structural incentive inversion, not a tuning problem.
- ⭐⭐ **`33858e` — the registry-pin gap was measured opening inside one session.** Clean at session
  start, broken immediately after `sync-plugin-cache`, no other actor. This is first-party
  confirmation of the standing hypothesis that the pin is LEFT BEHIND by every sync rather than
  drifting.

### Routing note

Three of the eleven are PR/review-apparatus subject matter by the standing three-way rule (the PR test
wins outright): `5cbc17` (review_commitments), `f0bd9d` (head_sha_verified on the comment path), and
`10f565` (unproven_bots includes optional bots). They are recorded here and transferred to the
`review-apparatus` epic rather than actioned in this one.
