envelope_version=1
sender_type=plan
sender_id=verdict-field-read-and-write-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-26T19:22:04Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=verdict-field-read-and-write-integrity
source_pr=1355

# Self-review's surface-only rule reports clean over defects the round actually saw

## Context

Round 6 of `pre-submission-self-review` **closed clean**. It also held two real contradictions in the diff's own added lines, which it had already identified and which its surface-only rule barred it from filing. From the operator gate:

> "Round 6 closed clean, but reported two real internal contradictions in this diff's own added lines that the surface-only rule barred it from filing."

The two:

- `orchestrator.py:482` — `except OSError as exc:  # pragma: no cover - platform-dependent stat failure`, while `test_an_unreadable_entry_is_reported_rather_than_dropped` monkeypatches `Path.is_dir` to raise `PermissionError` and therefore **does** cover that branch. The pragma asserts an uncoverable branch that a named test covers.
- `test_..._integrity.py:425` — a docstring reading *"The three forms the pre-fix parser could not tell apart, and the one it could"*, while `_COLLAPSED_FORMS` holds 3 and the pre-fix parser told **none** of them apart.

Both are exactly the defect class this plan was written to remove: a claim that reads as measured while nothing measured it. Both landed only because an operator was shown a gate and chose "Fix both, accept round 7" — at a cost of a seventh full-surface round (~200K tokens, ~9 min) on top of a loop that had already spent ~1.3M.

## Root cause

The step's clean verdict is a verdict about **what the rule permitted it to file**, not about what the round found. When the reviewer's own output contains findings it is barred from filing, "clean" and "nothing found" become different states rendered identically — and the step reports the one that is wrong.

This also interacts badly with the head-dependence: filing a finding advances HEAD, which re-fires the whole surface. The rule that suppresses out-of-surface findings is therefore *also* the rule that keeps the loop short, so the incentive runs the wrong way.

## Proposed action

Do **not** simply widen the surface — that trades a false-clean for an unbounded loop, and the seven rounds this plan already paid are the argument against it. Instead, make the suppressed set **visible without making it blocking**:

1. When a round suppresses a finding it actually identified, report it in the step's return payload as a distinct, non-blocking `observed_out_of_surface[]` list, and carry the count into the `mark-step-done` `display_detail`. A round that suppressed two findings must not be reportable as `self-review clean`.
2. Let the operator gate (or a configured policy) decide whether to spend another round, with the suppressed findings in hand. That is precisely what happened here — but it happened because a human read the round's prose, not because the step surfaced the state.

The recorded `display_detail` for this step's final firing was `"self-review clean: 59 candidates examined, no check matched"`. That sentence is true of the last round and false of the loop, and it is the only trace a later reader gets.

## Evidence

- aspect: chat_history_analysis — gate 2, the operator-decision text quoted above with both concrete defects
- `status.json` — `pre-submission-self-review`: `firing_count: 3`, `prior_firings: [failed, done]`, `display_detail: "self-review clean: 59 candidates examined, no check matched"`
- `decision.log` 12:25:34Z and 12:39:21Z — "Candidate-count gate DISPATCH — total_candidates=59 (>5 threshold, cov_scope=inherit)"; the second adds "round 2 full-surface confirmation after the delta round returned 0 candidates"
- `decision.log` 14:21:49Z — `record-step pre-submission-self-review outcome=executed — total_tokens=1198535, tool_uses=187, duration_ms=2810111`
