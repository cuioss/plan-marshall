envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:30:13Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-quarkus` (PR #694, merged `cd36dd24`), original message `outbound-hostname-verification-quarkus-006.md`.
> Component named is a `plan-marshall` bundle the Token-Sheriff lessons store does not own (`manage-lessons add` refuses it with `wrong_store`), so it is relayed rather than promoted locally. Content is unmodified below.

# Candidate lesson: actionable build-error / test-failure findings accumulate silently and first surface as an opaque merge-barrier refusal

**Components**: `plan-marshall:phase-6-finalize` / `plan-marshall:manage-findings`

## What happened

The maven build wrapper auto-files a finding per failed build. Over this run's build failures and deliberate control experiments (the clean-`main` timing control, the two-step test-jar workaround discovery), **19 actionable findings accumulated** — 13 `build-error`, 6 `test-failure`.

Nothing in the pipeline surfaced them between phase-5 and the pre-merge barrier. The operator's first contact with them was the **merge barrier refusing with a blocking count**: an opaque number, at merge time, over findings filed hours earlier for causes that were by then already resolved or deliberately induced.

(For scale: this plan's findings store holds 46 `build-error` records total, 36 after filtering — most auto-resolved by a later green build.)

## The two distinct defects

1. **No intermediate surfacing.** A finding filed at build-failure time is actionable *then*, while the operator holds the context. Deferring every one of them to a single aggregate count at the merge gate strips the context and converts N specific, individually-cheap dispositions into one expensive, undifferentiated blocker.
2. **Control-experiment findings are indistinguishable from real ones.** A build deliberately run to *reproduce* a failure (the clean-`main` control) files the same finding shape as an unexpected regression. There is no way to mark a build as an experiment, so the barrier counts the evidence-gathering against the operator.

## Candidate remediations (for the epic to weigh)

- Surface the pending actionable-findings count at each phase boundary (end of phase-5, and at each finalize step that already reports), so the number never arrives cold.
- Have the barrier's refusal enumerate the findings by cause/age rather than reporting a bare count.
- Give the build wrapper a way to mark an invocation as a control/experiment so its auto-filed findings are recorded but not counted against the merge barrier.

## Out of scope for this plan

Pipeline-level; this plan disposed of its 19 findings manually at the barrier.
