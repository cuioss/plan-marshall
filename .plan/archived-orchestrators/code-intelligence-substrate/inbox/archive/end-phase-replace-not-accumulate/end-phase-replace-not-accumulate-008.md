envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:23:02Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-07-29

# lessons-capture ran in an envelope but emitted no [DISPATCH] line, so the inverse-coverage check concludes the opposite of the truth

`default:lessons-capture` is on the dispatched roster in `dispatch-inline-split.md` (→ `phase-6-finalize --role post-run-review`). In this plan it reached `outcome=done` and its envelope demonstrably ran:

- `work.log:272` — `[STATUS] (plan-marshall:execution-context.lessons-capture) Complete`
- `execution.toon` `execution_log` — `lessons-capture,6-finalize,executed,115423,24,166674`
- it produced 4 real inbox messages (002 landing + 003/004/005 candidate-lessons), verified on disk

No `[DISPATCH]` line was ever emitted for it. There are 17 `[DISPATCH]` lines in this plan's `work.log` and none carries `role=post-run-review` before the retrospective's own at 17:06:19.

## Why this matters more than a missing log line

The `execution-context-dispatch-audit` aspect's `dispatch_coverage_violation` check keys **solely** on `[DISPATCH]` presence, and its canonical message asserts a specific conclusion:

> `"Step {step} classified DISPATCHED reached a terminal outcome ({outcome}) at phase_steps with no matching [DISPATCH] emission in work.log"` — read as "the step ran inline where dispatch was required"

For `lessons-capture` that conclusion is **false**. The step was dispatched; only the instrumentation is missing. So the detector converts an instrumentation gap into a fabricated discipline violation, and a reader auditing dispatch topology from the report would record a breach that did not happen.

The same run also produced the mirror-image false positive at `default:architecture-refresh`: rostered dispatched, genuinely ran inline, but correctly so — decisions `d0b69f` (Tier 0 clean) and `531318` (`Tier 1 skipped - change_type = bug_fix`) show only the non-dispatching tier ever fired, and the roster itself says "the dispatching tier governs the classification". So in one plan the check fires twice and is wrong about the nature of the violation both times, in opposite directions.

## Root cause

`[DISPATCH]` emission is fused to the dispatch branch in `phase-6-finalize/SKILL.md` Step 3, but the fusion is by convention in prose, not by construction — the dispatch can complete without the log line and nothing detects it. The roster's own "resolver-lookup completeness invariant" paragraph explicitly disclaims responsibility for missed emissions, so no invariant owns this.

## Impact

`[DISPATCH]` is the primary evidence surface for the whole dispatch-topology audit, including the corpus-level check in `audit-archived-plan-retrospectives`. An evidence channel with silent holes yields a detector whose findings must each be hand-verified against a second source before they can be believed — which defeats the point of a deterministic structural guard.

## Suggested corrective action

1. Make emission unskippable: emit the `[DISPATCH]` line from the dispatcher code path that performs the dispatch, not from a documented step the workflow author must remember. If the dispatch happens, the line exists.
2. Add a second, independent evidence source to the inverse-coverage check before it concludes "ran inline": the `[STATUS] (plan-marshall:execution-context.{name}) Complete` line and/or a non-zero token record for the step. A step with envelope evidence but no `[DISPATCH]` line should be reported as `missing_dispatch_emission` (an instrumentation finding against the dispatcher), NOT as `dispatch_coverage_violation` (a discipline finding against the step).
3. Give the roster a way to express a hybrid step whose dispatching tier did not activate, so `architecture-refresh` stops producing a violation when it correctly runs Tier-0-only. This is the actionable half of the classification problem that epic message 004 raised from the doc-consistency side.
