envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T18:49:45Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=documented-invocations-cannot-succeed-as-written
source_pr=1386

# analyze-logs build_time publishes bare zeros beside a sibling block attributing 69% of script time to builds

## Context

The `log_analysis` fragment's `build_time` block reported, for a plan that ran
builds for hours:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0
  error: 0
  timeout: 0
  killed: 0
  status_unknown: 0
```

Eight fields, every one a zero, no population marker and no could-not-look
discriminator. In the SAME fragment, `script_cost_rollup` ranks
`plan-marshall:build-pyproject:pyproject_build` FIRST at 50 calls and
19,009,450 ms — 69.107% of all script time, `max_ms` 1,754,830 — and 25
build-result logs sit in the plan directory under `build-results/`.

## Root cause

`build_time` is derived from the structured change-ledger, and the ledger holds
no build rows attributable to this plan (sampled rows carry `plan_id: null` and
empty `duration_seconds`). The block then renders "the oracle returned nothing"
as a set of measured zeros. Downstream this is known to be untrustworthy — the
`plan-efficiency` reference explicitly mandates rendering `total_build_seconds`
as `unavailable`, never `0`, when `build_count == 0`, because "a 0 asserts a
measurement nobody made, and it averages into every cross-plan roll-up as though
the plan had built instantly". The consumer knows the discriminator is needed;
the producer declines to publish it.

## Proposed action

Have `build_time` publish its own could-not-look state — a `ledger_rows_scanned`
population and a `build_oracle_state` of `present` / `absent` — so `build_count: 0`
is legible without a consumer having to know the special case. Separately,
investigate why builds run inside a plan's worktree do not land plan-attributed
rows in the change ledger, since that is what empties the oracle.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0` beside
  `script_cost_rollup.ranked[0]: pyproject_build, 50 calls, 19009450 ms,
  share_pct 69.107`
- aspect: plan_efficiency — reference § "Build time is READ from the
  change-ledger": "Absent is not zero ... Render `totals.total_build_seconds` as
  `unavailable`, never as `0`"
- artifact: 25 files under `build-results/` in the plan directory, the largest
  7.4 MB
