envelope_version=1
sender_type=plan
sender_id=hook-timeout-unit-confusion
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T20:57:22Z

# architecture --plan-id is a top-level router flag and is rejected after the verb

component=plan-marshall:manage-architecture
category=anti-pattern
confidence=high
source_plan=hook-timeout-unit-confusion
source_pr=1131

## Context

Five identical argparse rejections across five hours and five separate dispatched envelopes:

| Time | Envelope context |
|---|---|
| `14:45:24Z` | self-review-fix |
| `16:03:07Z` | pre-submission-self-review round 2 |
| `16:30:30Z` | pre-submission-self-review round 3 |
| `19:18:22Z` | pre-submission-self-review, post-loop-back |
| `19:24:23Z` | plugin-doctor / self-review round |

Each failed with `architecture.py: error: unrecognized arguments: --plan-id hook-timeout-unit-confusion`.
The `script-failure-analysis` aspect classified this as `invented_flag` with `occurrence_count: 5` —
the highest-recurrence failure of the run.

It is not an invented flag. `architecture.py` declares `--plan-id` at the **router** level —
`usage: architecture.py [-h] [--project-dir PROJECT_DIR] [--plan-id PLAN_ID] {discover,init,…}` —
consumed before subcommand dispatch. It must therefore **precede** the verb. All five calls placed it
after.

## Root cause

The flag is real but invisible where an agent looks for it. An agent that reads the subparser's
`add_argument` table sees no `--plan-id` on the verb and concludes the flag is unsupported; an agent
that reads the usage line sees `--plan-id` and appends it in the position every other
`manage-*` script accepts. Both readings are locally sound, and only reading the router source
disambiguates. Five independent envelopes made the same choice, which is the signature of a
misleading surface rather than five careless calls.

This is the same shape already recorded elsewhere in the project for `ci.py --project-dir` — a
top-level router flag consumed before dispatch, which an argparse-table grep misses. The rule
generalises: **verify an absent flag against the router, never against the argparse table.**

## Proposed action

1. **Tooling.** The executor's invocation validator already produces a clean, actionable message for
   the analogous manage-* case — at `17:30:17Z` this same run got
   `Use a declared flag for 'plan-marshall:manage-status:manage-status get': ['plan-id', 'store']`
   instead of a raw argparse dump. Extend it to recognise a **known top-level router flag supplied in
   trailing position** and say so ("`--plan-id` is a top-level flag for
   `plan-marshall:manage-architecture:architecture`; place it before the subcommand"). That converts
   five blind retries into zero.
2. **Documentation.** `manage-architecture`'s Canonical invocations block should show the router
   flags in their required position in at least one worked example, since the block is what the D4
   plugin-doctor analyzer treats as source of truth and what callers copy.
3. **Consistency.** Consider accepting `--plan-id` on the subparsers too. Every sibling `manage-*`
   script takes it after the verb, so the asymmetry is the actual trap; if the router-level
   consumption is load-bearing, a subparser-level alias that forwards is cheaper than teaching every
   caller the exception.

## Evidence

- `logs/work.log` — five `[ERROR] … script_failure notation=plan-marshall:manage-architecture:architecture
  exit_code=2 failure_kind=argparse_rejection` entries at the timestamps above.
- `work/fragment-script-failure-analysis.toon` — `anti-pattern, invented_flag,
  plan-marshall:manage-architecture:architecture, search, 2, occurrence_count: 5`.
- `logs/work.log` `17:30:17Z` — the contrasting, actionable validator message for `manage-status get`.
- aspects `script_failure_analysis`, `llm_to_script_opportunities`.

## Why this belongs to truthful-signals

The failure classifier calls this an `invented_flag`, and it is not invented — it is a real flag in
the wrong position. A triage reading that label files it as caller carelessness and closes it; the
label is confident and points away from the fixable surface. Both the classifier's category and the
script's usage line are individually defensible and jointly misleading.
