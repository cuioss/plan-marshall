envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T16:37:57Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall
source_plan=inventory-blind-spot

# Two done-marked finalize steps emitted no work-log line, and one dispatched envelope emitted no [DISPATCH]

## Observation — this run

Cross-referencing `status.metadata.phase_steps["6-finalize"]` (17 steps, all `outcome: done`) against `logs/work.log`:

**Silent steps** — `push` and `ci-verify` appear **nowhere** in `work.log`. Neither a `[STEP]` line nor a `[DISPATCH]` line. Their recorded outcomes are consequential:

```
push:      outcome=done, "pushed feature/inventory-blind-spot"
ci-verify: outcome=done, "ci-verify: all checks green"
```

The only trace either leaves is a `record-step` line in `decision.log`. The work log — the audit surface a retrospective reads first — cannot confirm the branch was pushed or that CI was green.

**Missing dispatch emission** — `lessons-capture` has no `[DISPATCH]` line, yet `work.log` at 15:51:24 carries:

```
[STATUS] (plan-marshall:execution-context.lessons-capture) Complete
```

Only an `execution-context` envelope emits that line. The dispatch demonstrably happened; the emission contract in `ref-workflow-architecture/standards/dispatch-logging.md` was not honoured.

**Name mismatch** — the dispatch at 15:40:51 names `workflow=plan-marshall:plan-marshall/workflow/verification-feedback.md`; its completion at 15:43:20 reads `(plan-marshall:execution-context.wait-region-unified-triage) Complete`. The pair cannot be matched mechanically.

## Root cause

`[DISPATCH]` emission is an obligation on each individual dispatch site rather than a property of the dispatch mechanism, so any site that forgets it produces a dispatch with no evidence. Likewise `[STEP]` emission is per-step rather than emitted by the step runner.

## Solution

Emit `[DISPATCH]` and `[STEP]` from the **shared** dispatch/step-execution path rather than from each call site, so the evidence is structural and cannot be omitted by an individual site. Where that is not feasible, add a finalize-exit assertion that every `phase_steps` entry marked `done` has at least one matching work-log line, failing loudly on a gap.

The completion line should carry the same identifier as its dispatch line so pairing is mechanical.

## Generalisation

**A per-call-site logging obligation will be missed at some call site.** The plan-retrospective dispatch audit exists precisely to catch spawns that bypass the canonical envelope — but it works by reading `[DISPATCH]` lines, so a dispatch that omits its line is *invisible to the very check designed to police it*. A detector that consumes voluntarily-emitted evidence can only ever report a lower bound.

## Impact

`phase-6-finalize` step runner and every finalize step's dispatch site. The dispatch-audit aspect of `plan-retrospective` under-reports by construction until emission is centralised.
