envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:08:19Z

component=plan-marshall:manage-lessons
category=improvement
title=Add a housekeeping-classify verb so the retain partition is computed, not re-argued per lesson

# Add a housekeeping-classify verb so the retain partition is computed, not re-argued per lesson

## Context

`project:finalize-step-lessons-housekeeping` fired **5 times** during plan `a-refusal-is-recorded-as-a-refusal-the-record`. Two of those dispatches each wrote 11 per-lesson verdicts into `decision.log` — 22 lines whose substance is one deterministic question repeated:

> `retained 2026-08-27-07-001: plan-marshall:phase-5-execute is not in this plan's footprint; ...`
> `retained 2026-08-27-07-002: plan-marshall:script-shared is not in this plan's footprint; ...`
> `retained 2026-08-27-09-001: plan-marshall:manage-run-config is not in this plan's footprint; ...`

The predicate is set membership: is this lesson's `component` in the plan's realized footprint? Of the 11 lessons, the second pass found only 3 whose component intersected the delta at all, and those 3 are the only ones whose verdicts required judgement — the other 8 were disposed of by the membership test alone.

The cost is recorded in the plan's own words. A third dispatch was **skipped** by hand-written orchestrator judgement at 16:43Z:

> "A third dispatch would re-derive the same 11 retentions at ~200K tokens. If this judgement is wrong the cost is a missed retirement, which the next plan's housekeeping pass picks up - not a shipped defect."

That is a correct call made for the right reason, but it is a workaround: the step was skipped because its deterministic majority is priced as if it were judgement.

## Root cause

The step dispatches an LLM envelope over the **whole** active corpus, and the LLM re-derives a mechanical set-membership test for every lesson before reaching the few that need reasoning. There is no verb that partitions the corpus first, so the deterministic majority is paid for at LLM rates on every firing.

## Proposed action

1. Add `manage-lessons housekeeping-classify --plan-id {plan_id}`: intersect each active lesson's `component` with the plan's realized footprint (resolved through the shared footprint resolver) and return two lists — `no_intersection` (retain, with the component and the footprint it was tested against) and `intersects` (needs judgement).
2. Have `finalize-step-lessons-housekeeping` consume that partition and dispatch judgement over the `intersects` list only, emitting the `no_intersection` retentions as script-derived records.
3. Publish both counts on every run, so a retain-all verdict states the population it was computed over rather than asserting it — the same discipline the retirement surface already applies.

## Expected saving

On this plan: 22 of 25 per-lesson verdicts across two dispatches were the membership test alone, and the run priced one avoided dispatch at ~200K tokens. The step fired 5 times.

## Evidence

- aspect: llm_to_script_opportunities — top candidate, `repetition_count: 22`, `complexity: low`
- log: `decision.log` entries at 02:24:11Z-02:24:34Z and 11:15:33Z-11:16:02Z (2026-08-30) — the two 11-lesson verdict blocks
- log: `decision.log` 16:43:03Z — the skipped third dispatch and its ~200K token estimate
- artifact: `status.json` `phase_steps["6-finalize"]["project:finalize-step-lessons-housekeeping"].firing_count: 5`
