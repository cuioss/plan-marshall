envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:21:14Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# channel_completeness divides all-phase dispatch lines by finalize-only completions

## Context

`check-dispatch-audit.py`'s D3 block (`channel_completeness`) is the audit's own self-trust grade — it publishes a dispatch/completion `ratio` and downgrades `confidence` when the channel looks sparse. On this plan it reported:

```
dispatch_line_count: 22
completion_count: 22
ratio: 1.0
confidence: nominal
```

Both figures are correct in isolation and they are **not** measured over the same population:

- `dispatch_line_count = len(dispatch_lines)` counts every `[DISPATCH]` spawn line in the work log across **phases 2 through 6** (22 on this plan; only **12** carry the finalize dispatcher caller).
- `completion_count` counts `[STEP] ... Completed step:` lines, which `mark-step-done` emits only for **finalize** steps (22 on this plan).

The `1.0` is the arithmetic coincidence of two unrelated populations. The finalize-scoped ratio is `12/22 = 0.545` — barely above the `_SPARSE_RATIO = 0.5` floor below which `confidence` would degrade to `low`.

The consequence on this very plan: the audit graded the channel `nominal` over a four-envelope, ~893K-token hole in that same channel (see the sibling candidate-lesson on re-dispatch emission).

## Root cause

`cmd_run` computes `finalize_dispatch_line_count` — the correctly-scoped figure — and passes it to D2 (`evaluate_dispatch_coverage`), then passes the **unscoped** `len(dispatch_lines)` to D3 (`evaluate_channel_completeness`) alongside D2's finalize-scoped `coverage['dispatched']`. Two checks in one function disagree about their own scope, and the mismatch is invisible because both published counts look plausible.

`check-dispatch-audit.py`:

```python
channel = evaluate_channel_completeness(
    len(dispatch_lines), completion_count, coverage['dispatched']
)
```

## Proposed action

Pass `finalize_dispatch_line_count` to `evaluate_channel_completeness` so the numerator and the denominator name the same phase, exactly as D2 already does. Two guards worth adding with it:

1. The ratio's two inputs should be **labelled with the population each was taken over** in the emitted fact block, so a future scope divergence is visible in the fragment rather than only in the source.
2. A regression test in which the all-phase count and the finalize-scoped count differ, asserting the graded `confidence` follows the finalize-scoped figure. A test built on a single-phase fixture cannot distinguish the two and would pass over this defect.

Note the irony worth carrying into the fix: this is a detector whose job is to make a zero legible, reporting a confident `nominal` over the gap it exists to expose. It is the same class as the plan that produced this observation.

## Evidence

- aspect: logging_gap_analysis — `channel_completeness_cross_population_ratio`
- aspect: execution_context_dispatch_audit — emitted `ratio: 1.0`, `confidence: nominal`, `dispatch_line_count: 22`, `completion_count: 22`
- Source: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py` — `cmd_run` (the `evaluate_channel_completeness` call site), `FINALIZE_DISPATCH_CALLER`, `_SPARSE_RATIO`
- Counted from `work.log`: 22 `[DISPATCH]` lines total, 12 with caller `plan-marshall:phase-6-finalize`, 22 `[STEP] Completed step:` lines
