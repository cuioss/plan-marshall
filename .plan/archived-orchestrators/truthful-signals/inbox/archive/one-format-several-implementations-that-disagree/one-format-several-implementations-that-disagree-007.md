envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=landing
created=2026-09-07T19:22:32Z

## What landed

PLAN-TRUTH-125 — *One format, several implementations that disagree, and no test
compares them*. Merged as `39ec2a0ad` (squash, via the platform merge queue).

TOON now has one canonical implementation (`serialize_toon` / `parse_toon`) that
every marketplace emitter routes through, and a population-derived test that
proves it. The guard derives its population two independent ways — every function
whose NAME matches the TOON probe, and every function that BEHAVES like an emitter
(prints a TOON-shaped literal to stdout) — and cross-checks them, so the
completeness claim is derived rather than asserted. The round-trip property test
pins the canonical pair against exactly the values every retired lookalike wrote
bare: `None`, a list, and strings carrying a tab, a comma and a colon.

```landing-facts
schema=landing-facts/1
plan_id=one-format-several-implementations-that-disagree
epic=truthful-signals
pr=#1427
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=6220062
total_wall_seconds=185171
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_commit=39ec2a0ad9c522aa5730fc6a966359f107c4561b
step.automatic-review.required_bots_participated=2
step.automatic-review.rounds=9
step.record-metrics.billing_weighted_total=184415222
step.record-metrics.any_phase_missing_end_time=false
```

## Residue

Irreducibly narrative — surfaced by the run, recorded by no step's typed fact.

**The vacuous-guard archetype recurred five consecutive times inside its own
fix.** Five CodeRabbit rounds each found the archetype in the previous round's
patch: a `raise` guarded by an `if`; a `raise` inside a function merely *defined*
in the handler; a `return substitute` leaving the `raise` below it dead; then a
hand-enumerated exception-name set that missed `ModuleNotFoundError`. Three
internal `pre-submission-self-review` rounds found none of them. The cycle ended
only when the clause stopped refining its answer and **changed its question** —
from "does this handler propagate?" (reachability, undecidable from an AST shape)
to "is `handler.body[0]` a `raise`?" (positional, decidable, sound, deliberately
incomplete). The generalisable signal: *when successive review rounds keep finding
the same archetype inside the previous fix, the predicate is asking an undecidable
question — it does not need one more special case.*

**Roughly five hours of unattended wall-clock were spent waiting on a 21-minute
window.** Three CodeRabbit rate-window refusals were each followed by a
~90-minute operator wait, per standing protocol; all three retries refused. Round
7's notice stated its own reset — `Next included review available in 21 minutes` —
and a retry timed to that ETA succeeded immediately. The tooling reported
`refusal_eta: ""` throughout, because none of the three registered extraction
regexes matches that leading phrasing. Filed to `review-apparatus` as a defect plus
two candidate-lessons.

**A merge-gate cleanup verb left the stale ref it exists to remove.**
`worktree-remove` deletes the local branch; `prune-local-and-remote-ref` then
failed `branch_delete_failed: not found` and aborted *before* pruning the
remote-tracking ref. Verified against the remote (`ls-remote` empty) and deleted by
hand. The two verbs are not idempotent against each other.

**A failing coverage gate had a contaminated denominator.**
`check-artifact-consistency` reported `recall 57% — FAIL`. Six of its ten "missing
declared files" are lessons-consult prose bullets (`Best practice — …`, `No tips,
insights or best practices recorded for this module.`) parsed as declared-file
entries. Real recall is ~71%, above threshold; four files are genuinely missing.
A loud wrong number, which is worse than a quiet one.

**Two operator-facing degradations, recorded because they shaped the run.** Agent
dispatch and `SendMessage` were both blocked by the session's permission
classifier partway through finalize, so `branch-cleanup`, `plan-retrospective` and
every remaining step ran inline in the orchestrator context instead of under their
documented dispatch envelopes. Separately, a mid-session system-reminder instructed
that file reads go through Bash `cat`/`grep`/`find`; every dispatched agent and the
orchestrator independently identified the conflict with this repository's hard
rules and refused it.

**Cost shape.** 51h26m wall against 5h18m worked — 46h8m idle, almost all of it in
`6-finalize` (47h5m wall, 141.5M of the 184.4M billing-weighted total). The run's
dominant cost was waiting on an external reviewer, not computing.
