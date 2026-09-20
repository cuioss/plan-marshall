envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:35:25Z

component=plan-marshall:manage-ci-artifacts
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# A red CI run is never archived, so the offline record shows an unbroken green history

## What happened

On PR #1366, CI went red once. `decision.log` entry `70f088` (2026-08-29T21:52:54Z):

> CI red on first PR HEAD e7299d8e6 — verify/verify failed on a single mypy
> no-any-return in test_orchestrator_corpus.py:3235 (_own_unreadable_tally). Root
> cause: pre-push-quality-gate's three arms ran green BEFORE the six self-review
> rounds added that helper; every post-round re-verification re-ran quality-gate +
> module-tests but never test-compile, and only test-compile reads test/ with mypy.
> Fixed and pushed as ba5bd9f27.

The plan's CI artifact store contains **three** runs, all post-fix:

| run_id | head_sha | final_status |
|---|---|---|
| 33277182473 | ba5bd9f27 | success |
| 33279606884 | 48260c928 | success |
| 33281321704 | e60da719c | success |

There is **no** `artifacts/ci-runs/` entry for the red run on `e7299d8e6`.
`status.json` corroborates the same clean picture: `ci-verify` has
`firing_count: 3` with `prior_firings: [done, done]` and a final `done` — no failed
firing anywhere.

## Why it matters

`plan-retrospective` exists to audit a plan **offline**, from its persisted
artifacts. Reading the artifact store and `status.json` — the two structured sources —
yields the conclusion that CI was never red on this plan. **This retrospective
reached exactly that wrong conclusion** and was corrected only by reading a single
WARNING line of `decision.log` prose.

The consequence is not cosmetic. The red run is the sole evidence for a real,
generalisable process defect (a *partial* re-run of a complete gate: quality-gate and
module-tests re-ran after every self-review round, `test-compile` never did, and only
`test-compile` type-checks `test/`). That defect is invisible to every structured
consumer.

`manage-ci-artifacts` appears to persist only the run `ci-verify` waits through to
completion, not the runs it rejected and re-ran past.

## Remedy shape

Persist the run manifest and job logs on **every** `ci-verify` observation, not only
the terminal green one. The capture capability already exists; only the trigger
condition needs widening. A red run should additionally be reachable from
`status.json` — a `prior_firings` entry that records `done` for a firing whose
observed run was red makes the step ledger agree with the fiction rather than with
the event.
