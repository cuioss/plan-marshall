envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T10:21:54Z

# pre-submission-self-review reports clean when its cognitive checks could not run

component: plan-marshall:phase-6-finalize
category: bug
confidence: high
source: plan-retrospective (plan-203-inbox-consumed-vs-missing)

## Context

During PLAN-203's finalize, the `pre-submission-self-review` step dispatched at 07:26:20 and its
envelope logged, at 07:27:40:

```
[ERROR] (plan-marshall:execution-context.pre-submission-self-review) Missing required candidates
input - cannot run Steps 2-3 cognitive checks
```

The step nonetheless completed and recorded `outcome: done` with

```
display_detail: "self-review clean: 26 candidates, no check matched"
```

The candidate count is real — `decision.log` shows `Candidate-count gate DISPATCH — total_candidates=26
(>5 threshold, cov_scope=inherit)`. What is not established is that any cognitive check ever ran over
those 26 candidates. The step's own error line says they could not.

## Root cause

The step's summary encodes "no check matched" for a run in which the checks were not executable. There
is no `done_degraded` outcome and no `skipped_checks[]` field, so a could-not-look result and a
looked-and-found-nothing result share one representation in `status.metadata.phase_steps`.

## Why it mattered on this plan

CodeRabbit subsequently found a genuine data-integrity defect on the PR: `inbox_state` was derived from
`inbox_dir.is_dir()` re-evaluated at return time while `count` came from an earlier scan, so the payload
could report `count: 3` with `inbox_state: missing`. That is a self-contradicting-state defect in a
same-document pair — squarely in the class `ext-self-review-plan-marshall` surfaces. It required an
unplanned TASK-008 and a full finalize loop-back to repair. The self-review reported clean.

## Proposed action

1. When the candidates input is missing, the step MUST NOT emit a `display_detail` asserting a check
   result. Emit a degraded outcome naming the checks that did not run.
2. Treat a non-empty `total_candidates` with zero executed checks as a hard error, not a pass.
3. Cross-check: the same "clean over an uninspected surface" shape appears in
   `project:finalize-step-plugin-doctor` ("plugin-doctor clean: 2 skills gated" over a logged WARNING
   that cross-skill rules were NOT evaluated).

## Evidence

- work.log 07:27:40 — `Missing required candidates input - cannot run Steps 2-3 cognitive checks`
- status.json `phase_steps["6-finalize"]["pre-submission-self-review"].display_detail`
- review-retrospective.md — the CodeRabbit inline finding at `_orchestrator_inbox.py:723`
- decision.log 07:28:55 — candidate-count gate, total_candidates=26
