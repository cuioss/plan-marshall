envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:30:28Z

# Candidate lesson: `[DISPATCH]` emits once per ROLE, not once per FIRING — the multiply-fired under-count this plan closed in `mark-step-done` is still open in the sibling trail, and the audit guarding it cannot see the gap

**Source**: PLAN-TRUTH-055 post-landing retrospective, full manual enumeration of `logs/work.log` (629 lines)
**Defect class**: last-write-wins / history-erasing record — the SAME defect this plan's D4 fixed, at a different granularity
**Theme fit**: confident-signal-hides-a-caveat, twice over

## The measurement

| Instrument | Count |
|------------|-------|
| `[DISPATCH]` lines emitted in `logs/work.log` | **15** |
| Distinct `(execution-context.X) Complete` envelope completions | **32** |
| Emission coverage | **47%** |

The 15 emitted lines cross-check exactly against `analyze-logs`' independent tag counter
(`DISPATCH,15`), so the numerator is not a reading artifact.

**The mechanism is clean**: all 15 emitted lines are the *first* dispatch of a role. All 17 gaps are
re-firings or nested sub-envelopes. Examples: `phase-2-refine`'s re-dispatch (22:13:29Z), the
Q-Gate re-entry of `phase-3-outline` (07:49:13Z), firings 2/3/4 of `pre-submission-self-review`, the
nested `self-review-fix` / `self-review-fix-2` / `vacuous-guard-fix` envelopes, every post-loop-back
finalize-step re-firing, and firings 2/3/4 of `automatic-review`.

**This is not the generic-subagent defect.** Zero `envelope_violation`, zero
`generic_subagent_violation` — every line that *was* emitted carries
`target=execution-context-level-3` or `level-5`. The discipline held; the instrumentation did not.

## The pairing that makes it a lesson

This plan's **D4** fixed `mark-step-done` so a multiply-fired step retains `firing_count` and
`prior_firings`. It worked, and this plan's own `status.json` proves it:

```text
pre-submission-self-review:
  outcome: done
  display_detail: "self-review clean: 228 candidates examined, no check matched"
  prior_firings[3]{outcome}: failed / failed / done
  firing_count: 4
```

The `[DISPATCH]` trail records **that same gate once**.

One store learned to count firings; its sibling still counts roles. The originating spec's own words
for the D4 defect apply verbatim to the trail: *"an eventful gate and a first-pass-clean one must be
distinguishable in structured state."*

## The second half: the check that cannot see it

The `execution-context-dispatch-audit` aspect owns a `dispatch_coverage_violation` check that asks
whether each **step** classified DISPATCHED and marked terminal carries *at least one* `[DISPATCH]`
line. Under that predicate **this run passes for every finalize step**, because each step's first
firing emitted. All 17 gaps are invisible to it.

> A check whose population is STEPS is structurally unable to detect an under-count whose unit is
> FIRINGS. The predicate is correctly implemented, correctly passes, and answers a narrower question
> than the reader takes it to answer.

That is the epic's archetype in its purest form, inside the epic's own enforcement instrument.

## The one case where the record cannot even say what happened

The 18:19:20Z loop-back re-entry of `5-execute` emitted **neither** a `[DISPATCH]` line **nor** an
`execution-context.phase-5-execute Complete` marker, while its first two envelopes emitted both. The
log therefore cannot distinguish *dispatched-but-unlogged* from *ran inline* — two outcomes with
different enforcement consequences, and it substantiates neither.

## Candidate rule

> Move the `[DISPATCH]` emission from the dispatch-DECISION site to the dispatch-INVOCATION site, so a
> re-firing emits, and add a firing ordinal to the line.

> Any coverage check over a repeatable event must state its unit. A per-step presence assertion and a
> per-firing count assertion are different checks; publishing the first while naming it "dispatch
> coverage" invites the second to be read off it. Compare emission count against envelope-completion
> count directly — both are countable from one file.

## Cross-reference

Third instrument in this plan disagreeing about the same population: the dispatch-boundary ledger holds
**13** rows, the `[DISPATCH]` trail **15** lines, and the envelope-completion count is **32**. All three
purport to count this plan's dispatches; the ledger is the smallest. None of the three states its own
coverage.
