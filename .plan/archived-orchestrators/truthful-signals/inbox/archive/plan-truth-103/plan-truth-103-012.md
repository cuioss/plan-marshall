envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=landing
created=2026-09-13T12:13:01Z

# Landing: PLAN-TRUTH-103

**Outcome**: shipped
**PR**: #1475 — https://github.com/cuioss/plan-marshall/pull/1475
**Merge commit**: `3103e9d6afa08697d5bab159afb09727882af1bc` (squash, via merge queue)
**Base**: `main`
**Deliverables**: 5/5
**Tasks**: 10/10 (5 planned + 5 allocated from review findings)
**Commits**: 14
**Files**: 13 (+699/−80 before review rounds)

## What landed

The premise that Claude's file-permission checks consult `Edit(...)` only — so a
`Write(...)` allow rule grants nothing — was propagated to the three places that still
modelled `Write` as live or `.claude/settings.json` as authoritative.

- **D0/D1** — 16 write-intent matcher sites re-keyed `Write(` → `Edit(` across 3 files.
  12 of them live in `permission_doctor.py`'s `SUSPICIOUS_PATTERNS`, which a plain
  `Write(` search cannot find because the patterns are regex-escaped. The audit was
  exactly inverted: its only high-severity filesystem-wide-*write* detector fired on
  `Write(/**)`, which grants nothing, while `Edit(/**)`, which genuinely grants
  filesystem-wide write, matched no pattern at all.
- **D2** — the shared `resolve_settings_arg` helper now resolves the READ-preference
  selector, so pruning reaches the file whose entries actually take effect. Operator
  chose the wide variant (all four subcommands sharing the helper) over the narrow one.
  The six subcommands routed through `permission_common.get_settings_path` were
  deliberately NOT switched; that four-vs-ten boundary is load-bearing and test-pinned.
- **D3** — the `deny`/`ask` never-pruned reachability finding recorded: no plan-marshall
  path emits a `Write(...)` deny rule, so the gap is reachable only from a hand-edited file.
- **D4/D5** — matched positive/negative controls and a dual-settings-file fixture.
  Before this plan, `Edit\(/` had **zero** hits across all 2793 test files: no test
  anywhere asserted the spelling that actually grants.

## Structural limit (carried forward deliberately)

The premise itself — that a `Write(...)` rule is inert at permission-check time — is a
claim about Claude's runtime that **no gate in this repository can verify**. Every check
in this run is downstream of it. It was published as its own section in the PR body
rather than left implicit.

## Review

`proves: participation_only`. Four CodeRabbit rounds across three HEADs:

| Round | HEAD | Findings |
|---|---|---|
| 1 | `11acd6452` | 4 (1 Major) — all fixed |
| 2 | `8dd5792e4` | 0 — edit-only publish, review object stayed stale |
| 3 | `8081dfbf7` | 1 — the round-1 Major's own fix re-introduced the archetype |
| 4 | `2d37e3a35` | 0 — converged |

`cuioss-review-bot` (required) participated on every HEAD but raised nothing on any, and
has no push trigger — it was stale after every push and needed three explicit triggers.
`sourcery` (optional) refused all rounds on a 7-day diff-character quota and never looked;
its green check is a check-level pass, not a review.

## Escapes worth the epic's attention

All 4 review escapes partitioned `gate_addressable`, **0 structural** — every one an
archetype the `ext-self-review-plan-marshall` surfacer already enumerates, and two of
them in `test/`, past two self-review firings.

The sharpest datum: finding `3c3297` is the round-1 Major's own fix re-introducing the
identical mirrored-set archetype one layer down. Neither a single gate pass nor a single
review pass could have seen it — only a later review round did.

## Cost

6.6M tokens / 156M billing-weighted / 6h55m worked / 26h33m wall.
`6-finalize` alone: 4.39M tokens (66%), 3h12m worked, 18h34m wall.

The cost is the review loop, not the change. All 5 self-review findings were real
defects fixed by deletion; all 4 CodeRabbit findings were real. But a self-review good
enough to keep finding real defects is also expensive enough to dominate the plan — and
it spends a budget **shared** with the external-review tier (finding `265638`).

## Findings routed to this epic

`265638` shared loop-back counter starves the external tier ·
`5cbc17` review_commitments clear over an empty population ·
`f0bd9d` head_sha_verified false negative on the comment path ·
`c8cccc` `--measured-diff-size ""` argparse rejection on the ordinary path ·
`10f565` unproven_bots includes optional bots ·
`3ee899` worktree-remove deletes the branch ref, making prune's remote half unreachable ·
`33858e` sync-plugin-cache re-opens the registry-pin gap (measured first-party this session) ·
`7cca7f` the change-ledger is worktree-relative, so every worktree plan's build records are
DESTROYED at finalize — corrects plan-retrospective's "build oracle dead six days", whose
observation was right but whose proposed remedy would chase a bug that does not exist ·
`cd5a69` plan-retrospective runs before record-metrics, so its cost-attribution finding
measures a pre-enrich state ·
`f03cdf` doc algorithm layer exists in no `.py` file ·
`5cf3c5` refine all-dimensions-100 confidence flag

Plus 11 candidate-lesson messages (`-001`…`-011`) from plan-retrospective and lessons-capture.
