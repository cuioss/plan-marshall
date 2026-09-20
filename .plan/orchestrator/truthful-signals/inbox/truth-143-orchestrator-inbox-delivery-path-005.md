envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:27Z

# 8 of 15 token-proven dispatched finalize steps emit no [DISPATCH] work-log line

component: plan-marshall:phase-6-finalize
category: bug
confidence: high

## Context

`check-dispatch-audit` classified the 17 terminal finalize steps of this plan by their token record: 15 `dispatched`, 2 `ran_inline`, 0 `no_evidence`. Against those 15 token-proven dispatched envelopes, only 7 distinct `(role, workflow)` `[DISPATCH]` lines carry the finalize dispatcher caller — a gap of 8 missing dispatch emissions.

`channel_completeness` puts the finalize-scoped dispatch-line count at 7 against a completion count of 67, ratio `0.104`, and downgrades its own `confidence` to `low` on that basis.

The 8 is a **floor** for two independent reasons the script states: a step whose token row is unreadable lands in `no_evidence` and is never counted as dispatched at all, and a re-fire adds lines without adding steps. On this plan the first reason bites hard — 41 of 77 finalize dispatch-boundary rows record zero tokens (a separate proposal), so some steps that did dispatch cannot be proven to have dispatched and are excluded from the 15 entirely.

## Root cause

An instrumentation gap in the **dispatcher**, not a discipline violation by any step. The `[DISPATCH]` emission contract (`ref-workflow-architecture/standards/dispatch-logging.md` § "Emission contract") is satisfied by only 7 of the finalize dispatch sites. The audit is explicit that this is a finding against the emitter.

The consequence is that the audit's own headline numbers are weaker than they read. `shape_violation` reports `0/61` clean, but the audit itself warns that a clean shape violation over a populated population shows only that the emitter's two writes agree — both surfaces come from one seam. And `dispatch_coverage`'s `ran_inline: 2` is an **upper bound on inline execution, never proof of it**, because `ran_inline` means a recorded zero token attribution, which on this plan is also what a dispatched step with an uncaptured `<usage>` tag looks like.

## Proposed action

1. Emit the `[DISPATCH]` line from the single shared dispatch seam in `phase-6-finalize`, so coverage is by construction rather than per-site, and every finalize step dispatch produces exactly one line whether or not the step author remembered.
2. Publish the emission gap as a first-class gate signal rather than only as a retrospective finding: have the finalize dispatcher compare its own dispatch count against its emitted line count at phase close and record the delta.
3. While `ran_inline` remains derived from a zero token attribution, rename it or qualify it at the point of publication so a reader cannot take it as evidence of inline execution. The audit prose says this clearly; the field name does not.

## Evidence

- aspect: execution_context_dispatch_audit — `dispatch_coverage: 15 dispatched / 2 inline / 0 no-evidence of 17`, `missing_dispatch_emission: 8`, severity `error`
- aspect: execution_context_dispatch_audit — `channel_completeness: dispatch_line_count 7, completion_count 67, ratio 0.104, confidence low`
- cross-reference: 41 of 77 finalize dispatch-boundary rows carry zero token attribution, which inflates the floor character of the 8
- contract: `ref-workflow-architecture/standards/dispatch-logging.md` § "Emission contract"
