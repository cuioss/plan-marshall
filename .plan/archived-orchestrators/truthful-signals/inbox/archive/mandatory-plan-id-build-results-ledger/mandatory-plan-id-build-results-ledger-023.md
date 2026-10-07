envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:43Z

component=plan-marshall:plan-retrospective
category=bug
title=Three defects in the retrospective's own instruments, found by running it

# Three defects in plan-retrospective's own instruments

All three were found by this audit while auditing PR #1075, i.e. by the tool observing itself.
Grouped into one message because they share a component and an owner.

## 1. The Executive Summary section is unreachable by construction

`compile-report.py` renders the report's first section from a fragment key
`_executive-summary`:

```python
exec_fragment = fragments.get('_executive-summary')
```

`collect-fragments add` hard-rejects it:

```
status: error
message: Reserved aspect key: keys starting with "_" are internal metadata
```

`compile-report`'s **only** fragment source is `--fragments-file`, which is the bundle
`collect-fragments` produces. The key the consumer reads can therefore never be written by the
producer, and the workflow documents no alternative path. Every compiled retrospective report
emits, as its first content:

```
## Executive Summary

_No executive summary provided._
```

Verified on this run: 18 sections written, 0 dropped, 0 omitted — and the Executive Summary is
the placeholder. The section is not *failing*; it is *succeeding at being empty*, which is why
it has survived.

This is a **producer/consumer pair whose halves were never wired together** — structurally
identical to the `build_server._record_job` / `_latest_job_id_for_plan` defect that PR #1075
itself found and fixed. The retrospective tool contains an instance of the archetype it was
auditing.

**Fix direction**: either whitelist `_executive-summary` in `collect-fragments` (it is a
legitimate compile-time input, not internal metadata), or give `compile-report` a
`--executive-summary-file` flag. The current state — a documented feature with no reachable
input — should not persist either way.

## 2. `cost_preview.actual_tokens` is a phase-6 sum under a whole-plan name

`check-routing-decisions.py::evaluate_cost_preview` computes:

```python
actual = sum_execution_log_tokens(manifest)     # sums execution.toon execution_log rows
predicted = metadata.get('execution_profile_cost_preview')
preview['delta_tokens'] = actual - predicted
preview['delta_pct'] = round((actual - predicted) / predicted * 100, 1)
```

`execution_log` carries `record-step` rows, which in practice exist only for phase-6 finalize
steps (the phase-5 `verify:*` rows all record 0 tokens). On this plan `actual_tokens` came out
as **1,564,096** — the finalize-only figure — against a reconstructed plan total of
**~6,230,800**.

`execution_profile_cost_preview` is an init-time estimate of the **whole plan**. The two
denominators do not match. On PR #1075 `predicted_tokens` was `null`, so no delta was emitted
and the defect stayed **latent** — but any plan carrying a cost preview would get a
`delta_pct` understated by roughly 4×, feeding a wrong correction into the §4.6a
`cost_size_token_table` recalibration loop.

**Fix direction**: either rename the field to what it measures (`finalize_attributed_tokens`)
or widen the numerator to the whole plan. Do not leave a phase-scoped sum wearing a
plan-scoped name next to a plan-scoped comparand.

## 3. `extract-chat-signal` dropped 99.8% of the transcript and reported success

```
raw_turn_count: 1013
reduced_turn_count: 2
dropped_turn_count: 1011
reduced_bytes: 592
no_signal: false
over_budget: false
```

Tier 1 was selected (`no_signal == false and over_budget == false`), so the chat-history aspect
proceeded on a 592-byte "transcript" containing exactly two turns: the
`/plan-marshall:plan-marshall` launch command and a `PR 1075 MERGED` task notification.
**Zero operator turns survived.**

Real operator signal existed and was dropped. The decision log independently records four
operator decision points in this same session, at least two of which materially reshaped the
plan:

| Time | Operator decision | Effect |
|---|---|---|
| 11:56:34Z | two OVERRIDEs at the outline gate (all 27 subcommands; generic template rule) | triggered the D0 re-evaluation that split 7 deliverables into 8 |
| 12:37:18Z | resolve all 10 Q-Gate findings via one outline re-dispatch | grew the enumerated footprint from 48 to 54 paths |
| 13:45:00Z | `execute_without_asking=true` auto-continue | — |
| 21:17:06Z | merge-gate: proceed at 1-of-3 bot coverage | — |

`no_signal: false` is *technically* true — two turns survived — while being operationally
false: the aspect has nothing to analyse. A near-total drop rate is itself the signal and must
be surfaced.

**Fix direction**: add a drop-rate guard. When `dropped_turn_count / raw_turn_count` exceeds a
threshold (or when `reduced_turn_count` contains no user-authored turn beyond the launch
command), emit `status: skipped` with a distinct token — the existing two-token contract
(`transcript_too_large` / `transcript_unavailable`) has no bucket for *"reduction destroyed the
signal"*, which is a third, different failure.
