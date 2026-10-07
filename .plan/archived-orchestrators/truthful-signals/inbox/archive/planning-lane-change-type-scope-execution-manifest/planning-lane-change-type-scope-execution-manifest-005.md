envelope_version=1
sender_type=plan
sender_id=planning-lane-change-type-scope-execution-manifest
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T16:00:59Z

# Finalize consumed 81% of a 13.9M-token plan against execute's 507K

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high
source_plan: planning-lane-change-type-scope-execution-manifest
source_pr: 1399

## Context

`(scope_estimate: multi_module, change_type: bug_fix)` is an anchored row: warning at 1.2M tokens / 90 min, error at 2.0M / 150 min. This plan recorded:

| Metric | Value | Anchor |
|---|---|---|
| `totals.tokens` | 13,916,554 | error at 2.0M — crossed by ~7x |
| `totals.worked_seconds` | 30,624 (8h30m) | error at 150 min — crossed by ~3.4x |
| `max_phase_token_share` | 0.81 | fallback threshold 0.50 |
| `total_tokens_per_deliverable` | 1,070,504 | fallback threshold 500,000 |
| `tokens_per_file_modified` | 397,616 | fallback threshold 50,000 |

The distribution, not the total, is the finding:

| Phase | Tokens | Tool uses |
|---|---:|---:|
| 5-execute | 507,388 | 194 |
| 6-finalize | 11,273,742 *(boundary floor)* | 2,245 |

The implementation of 25 tasks across 13 deliverables cost 507K. The gate that shipped it cost 11.27M — and that figure is a **floor**, because `6-finalize` never closed, so the total above is a floor too.

## Root cause

The finalize loop ran 19 `pre-submission-self-review` firings (15 returning `loop_back`), 19 `plugin-doctor` firings, 18 `pre-push-quality-gate` firings, 17 `lessons-housekeeping` firings, 10 `automatic-review` firings and 8 `ci-verify` firings — a `firing_count` of 121 step completions against 23 configured steps. The dispatch ledger shows 61 finalize dispatches averaging ~185K tokens each.

Two structural contributors are visible in the record and are addressed by sibling candidate lessons:

1. **Self-seeding review rounds** — 14 of the 51 Q-Gate findings were authored by an earlier round's own fix, so a measurable share of the 19 rounds was spent repairing the previous round's repair.
2. **Head-dependent re-firing** — `pre-push-quality-gate` (18), `plugin-doctor` (19) and `lessons-housekeeping` (17) each re-fire whenever HEAD advances, and every self-review round advances HEAD. The gate cost is therefore multiplicative in the round count, not additive.

## Proposed action

Not a proposal to weaken the gate. Two bounded measurements first:

- Publish the finalize cost distribution the run already records — `refire-report` has `firings` per step and the dispatch ledger has `total_tokens` per row, so a per-step cost roll-up is a join over two existing artifacts, not new instrumentation.
- With that roll-up, decide which head-dependent steps genuinely need to re-run on every HEAD advance. A self-review round that touches three doc files advances HEAD and currently re-triggers a whole-tree `verify` (1560s+) and a whole-tree `plugin-doctor`; whether that is the right coupling is answerable once the cost is visible, and is guesswork until then.

Sizing the lever before staging it is the epic's own standing rule; this item is the sizing step.

## Evidence

- aspect: plan_efficiency — all four ratios computed against the anchored `multi_module + bug_fix` row; `totals.tokens` crosses the error column by ~7x
- aspect: logging_gap_analysis — 61 finalize dispatch-boundary rows, 42 `step_complete`, 17 `returned_with_findings`
- `status.metadata.phase_steps["6-finalize"]` — `firing_count` per step: self-review 19, plugin-doctor 19, quality-gate 18, lessons-housekeeping 17, automatic-review 10, ci-verify 8, push 8
