envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:18:59Z

# Candidate lesson: an orchestrator halt mid-finalize under `finalize_without_asking=true` left no `[BLOCKED]` marker, no `escalate_ask`, and no trace in the plan's own record

**Component**: `plan-marshall:phase-6-finalize` / `plan-marshall:manage-status` (the halt-recording surface)
**Source signal**: plan-retrospective report for `dual-homed-hook-install-renders-identically`
**Suggested category**: bug

## Claim

The run halted part-way through `6-finalize` while `finalize_without_asking=true` was configured — i.e. under a setting whose entire purpose is that finalize does **not** stop to ask. The halt produced:

- no `[BLOCKED]` work-log marker,
- no `escalate_ask` record,
- **nothing recoverable from the plan's own record at all**.

The only evidence the halt occurred is the session transcript, which the plan artifacts do not retain. From the plan's persisted state the run is indistinguishable from one that simply progressed more slowly.

## Why it matters

This is the failure mode the whole resumability contract exists to prevent. A halt with no marker means:

- **`resume` has nothing to re-anchor on.** The next session reads a plan mid-phase with no reason recorded and must reconstruct the stop from chat that may be gone.
- **The `finalize_without_asking` setting cannot be audited.** If finalize halts anyway, the setting's effective behaviour differs from its declared behaviour, and no artifact records the divergence — so nobody can measure how often it happens.
- **It is silent by construction.** A halt that records nothing cannot be counted, so its frequency is unknown and will stay unknown. Every other stop-class event in this system (a Q-Gate block, a merge-lock refusal, a drain's `archive_failed`) leaves a durable record specifically so the population is derivable.

## The archetype

Same family as the run's other findings, one level up: the *absence* of a signal read as the absence of an event. A phase that stopped and a phase that is still going look identical in the record, so the count of halts is structurally zero regardless of how many occurred — a zero that cannot distinguish which kind of zero it is.

## Suggested directive (for the orchestrator to judge)

1. **Every halt writes a marker, unconditionally.** Whatever path stops a phase mid-flight — operator interrupt, escalation, harness kill, budget exhaustion — must write a `[BLOCKED]`-class record naming the step it stopped in and the cause, before control leaves. A halt path with an unrecorded exit is the defect, independent of why it halted.
2. **Establish which path this actually was before designing the fix.** The retrospective observes the missing marker but not the halt's origin. A harness kill and a deliberate escalation need different remedies, and the current evidence cannot separate them — which is itself the point.
3. **Reconcile the marker against `finalize_without_asking`.** If the halt was an escalation, the setting was not honoured and that is a second, separate defect. If it was not an escalation, the setting is irrelevant and the report should not implicate it. Do not fold the two into one finding.

Derive the population rather than trusting this single observation: once a marker exists, count halts across recent plans. The current answer — zero — is an artifact of there being nothing to count with.
