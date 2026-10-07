envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=review-apparatus
kind=finding
created=2026-08-08T16:27:14Z

## Routed lessons cluster C05 — review-bot participation and reliability (9 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Why you**: the three-way routing rule — the PR/review test fires first and wins outright.
**You decide**: fold onto the named existing plans, stage a new spec, or decline. I am NOT
asserting a fold; nothing was written into your tree.

### The cluster

Nine active lessons describe review-bot participation and reliability failures. Deduplicated
from the 203-lesson active corpus; every member is corroborating evidence for work you already
own, not new scope.

| Lesson | Claim | Suggested home |
|--------|-------|----------------|
| 2026-07-28-19-002 | participation must be derived from review CONTENT; a bot review can arrive AFTER the merge — the bot's own status prose and the finalize-time comment snapshot are both non-oracles | `PLAN-PR-005` |
| 2026-07-28-23-001 | a bot's stated rate-limit ETA is a lower bound, never a wait budget | `PLAN-PR-007` |
| 2026-07-28-23-002 | a size-keyed bot refusal is unrecoverable by any wait-and-retry strategy | `PLAN-PR-007` |
| 2026-07-29-19-002 | a negative read of async remote state is provisional exactly as a positive one is | `PLAN-PR-007` |
| 2026-08-03-14-002 | the re-review that caught 14 unseen findings fired incidentally, not by design | `PLAN-PR-013` |
| 2026-06-21-21-001 | re-review freshness matcher shipped with naive-datetime comparison; only adversarial PR bots caught it | `PLAN-PR-013` |
| 2026-07-16-17-004 | a review-bot fix recipe can specify a vacuous test that passes both pre- and post-regression; prove discrimination by mutation before accepting done | `PLAN-PR-013` |
| 2026-08-03-14-007 | the triage leaf writes tests it structurally cannot run, with CI as the only covering gate | no obvious home |
| 2026-07-17-09-001 | `finalize-step-simplify` can propose reverting a fix `automatic-review` committed in the SAME run; the pipeline has no reconciliation contract and relies on ad-hoc orchestrator judgement | **no home — new spec candidate** |

### Claim labels

- **OBSERVED**: every lesson id, component, category and title (read from `manage-lessons list`);
  every `PLAN-PR-*` id, slug and status (read from your `status.json`).
- **HYPOTHESIS (verify-at-outline)**: that each premise still holds against current main.
  This run was scoped by the operator to cluster-level validity; per-lesson ground truth is
  owed by you at outline. Confirm/refute artifact: `automatic-review`'s participation
  classifier and the `ci pr comments` verb — the only surface your own standing rule accepts
  as evidence of participation.

### Two members worth your attention specifically

`2026-07-17-09-001` names a reconciliation gap between `finalize-step-simplify` and
`automatic-review` that no plan in your queue covers: simplify can revert, in the same run, a
fix the reviewer just committed. That is an in-run contradiction between two finalize steps,
not a bot-behaviour issue — it may belong to `truthful-signals` instead. Your call.

`2026-08-03-14-007` is adjacent to `PLAN-PR-012` (feed-pr-findings-back-into-local-review) but
is about the triage leaf's own executability, not the feedback path.

### Provenance

The corpus was snapshotted verbatim before analysis at
`.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`. Full
per-lesson dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
No lesson has been retired — corpus retirement is deferred behind `PLAN-TRUTH-044`.
