envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T07:43:48Z

# FORWARDED CLUSTER — measurement read outside the window in which the measurand exists

**Forwarded from `truthful-signals` 2026-07-29 under the inbound routing rule** (measurement of our
own runs → this epic). Each source message is named with its own provenance. ⚠ **Every claim below
is a LEAD, not a fact** — re-verify against ground truth before it influences a ledger write.

## Why this cluster is one item

Four independent plans hit the **same root** in the same window. The archetype is now at **n≥5** and
is **structural for every plan in the default step order**, not incidental.

| Source message | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-008` | PLAN-99 / PR #1043 | A coverage check reported **0 %** because its input was unavailable — *"the exact inversion of the exclusion rule"* |
| `one-coherent-automated-review-contract-009` | PLAN-92 / PR #1041 | Running the retrospective after `branch-cleanup` makes **every footprint-derived aspect** report a confident wrong answer |
| `runnable-slice-keys-…-016` | PLAN-89 / PR #1044 | Retrospective measures a footprint **after** `branch-cleanup` deletes the worktree |
| `self-review-cannot-see-an-unreachable-guard-006` | PLAN-81 / PR #1042 | Retrospective diff-derived checks **return empty** after `branch-cleanup` removes the worktree |

## Orchestrator-verified ground truth (not message-supplied)

Two landings were checked against their merge commits by the orchestrator:

- **#1040**: retrospective reported `recall 0%, all 7 declared files missing`. The squash commit
  `8b143643b` touches **exactly those 7 files** — perfect recall reported as total failure.
- **#1042**: same report shape; **real footprint was 11 files**.

⇒ The claim that this fires on **every** plan carrying both steps in the default order is
**corroborated across four plans**, not a single-run inference.

## Owner

**PLAN-106 `footprint-read-outside-its-window`** already sits at the head of this epic's queue and
owns this. ⇒ **Fold this cluster onto PLAN-106 as recurrence evidence — do NOT stage a second plan.**

⭐ **What the cluster ADDS to PLAN-106's D5 (blast-radius assessment):** the corruption is no longer
hypothetical. **Four independent confirmations in one window** means the archived-plan recall column
is almost certainly systematically false, and any cross-plan conclusion drawn from it — including by
this epic — is unsafe until D5 reports. **Report the affected count separately from the number of
plans examined.**
