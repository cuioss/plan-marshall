envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:29:49Z

component=plan-marshall:manage-change-ledger
category=bug
bundle=plan-marshall

# Build rows are attributed to `NO_PLAN`, so the build-time oracle reports zero for a plan that built for hours

## Rule

An oracle is only authoritative over the population it can attribute. When the attribution key is a
sentinel, the oracle still answers — with a well-formed, structurally complete zero — and every
consumer downstream inherits a measurement nobody made.

## Observation

Observed in PLAN `preference-admissibility-prose-vs-auditor-code`.

The retrospective's `analyze-logs` fact extractor computes `build_time` from the change-ledger, the
designated build-time ORACLE. For this plan it reported:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0 / error: 0 / timeout: 0 / killed: 0 / status_unknown: 0
```

Three independent sources say that is wrong:

1. `script-execution.log` records **103** `plan-marshall:build-pyproject:pyproject_build` calls
   totalling **31,166,590 ms** — 61.5% of all script time on the plan, the single largest cost line
   in `script_cost_rollup`, with a max single call of 1,930,110 ms.
2. The plan directory holds **30** build-result logs dated inside the plan's own window
   (`build-results/default/` and `build-results/plan-marshall/`, 21 KB to 7 MB each).
3. The operator transcript for this plan records `verify` being **OOM-killed twice**, which is not
   something that happens to a plan that ran no builds.

Querying the ledger directly: `manage-change-ledger query --kind build` returns `count: 444` from
`/Users/oliver/git/plan-marshall/.plan/work/change-ledger.jsonl`. Every row in the sampled head
(6 rows) and tail (12 rows) carries `plan_id: null` or `plan_id: NO_PLAN` — **including rows
timestamped `2026-09-04T09:55:38Z`, inside this plan's `6-finalize` window** — with `log_file`
paths under `.plan/local/plans/NO_PLAN/build-results/`. Not one sampled row carries the plan id.
(The 444 rows were not exhaustively enumerated; head and tail were sampled.)

So the builds were recorded. They were recorded against the sentinel.

## Why this is not caught downstream

The `plan-efficiency` aspect's "absent is not zero" rule fires correctly: `build_count: 0` renders
`total_build_seconds: unavailable` rather than `0`, so the retrospective report does not claim the
plan built instantly. **That guard works, and it is the only reason this is visible at all.** But it
converts a wrong number into a missing one — the ~8.7 hours of build wall time this plan actually
spent is now unavailable to every consumer, and a cross-plan roll-up sees a plan with no build data
rather than a plan whose build data was misfiled.

## How to apply

- **Find where `plan_id` is lost on the append path.** The ledger schema carries the field and the
  writer supplies `NO_PLAN`; the question is whether the caller has the plan id at that point or
  whether the wrapper drops it. Both the direct `./pw` rows and the executor-wrapped rows are
  stamped `NO_PLAN`, so the loss is upstream of the wrapper distinction.
- **Make a sentinel attribution loud where the plan context exists.** A build invoked from inside a
  plan-scoped envelope that records `NO_PLAN` is a defect, not a valid state; the append path can
  detect that mismatch.
- **Publish the attributed population.** `build_time` should report how many ledger rows were
  examined and how many were attributable, so `build_count: 0` is distinguishable from "0 of 444
  rows matched this plan".
