envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T05:17:03Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-07-29

# decision.log 'operator chose' phrasing used for auto-mode-resolved decisions

## Context

On plan `self-review-cannot-see-an-unreachable-guard`, decision.log records two entries phrased as
live human choices: `18:32:23 (plan-marshall:plan-marshall) User review: operator chose to fix the
6 pending q-gate findings before task creation` and `21:01:23 (scope-deviation:accept) Operator
chose FIX-here-anyway for CodeRabbit finding 168581`. The `chat-history-analysis` aspect's
signal-extraction pre-pass found only 1 operator-authored turn in the entire 748-turn session
transcript — the initial `/plan-marshall:plan-marshall task="..."` launch command — with zero
further operator turns anywhere in the session.

## Root cause

The plan was dispatched by the `truthful-signals` orchestrator as a single-shot, unattended run
(`execute_without_asking=true`, `finalize_without_asking=true`), so both decisions were resolved by
the dispatched agent itself operating under the host platform's auto-mode policy ("make the
reasonable call and keep going"), not by a live human answering an `AskUserQuestion` prompt. The
`"operator chose"` / `"User review"` phrasing is generic boilerplate used by these call sites
regardless of whether a live human or an auto-mode default produced the decision, so it reads as
stronger provenance than actually occurred.

## Proposed action

Distinguish, in the decision-log message text (or via a structured field), a decision resolved by
a live `AskUserQuestion` response from one resolved by an auto-mode default — e.g. `"Auto-resolved
(no operator prompt): ..."` vs `"Operator chose: ..."`. This matters for any future retrospective
or audit that reads decision.log as evidence of human-in-the-loop review, since the two provenance
classes currently look identical in the log text.

## Evidence

- aspect: chat-history-analysis — `reduced_turn_count: 2` of `raw_turn_count: 748`; the reduced
  transcript contains only the launch command and its skill-load acknowledgement, no further
  operator-authored turns
- decision.log lines at 18:32:23 and 21:01:23, both phrased as an "operator" / "User review" choice
