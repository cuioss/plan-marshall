envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:05:03Z

# Derive the post-loop-back re-fire set from the fix commit's paths

component: plan-marshall:phase-6-finalize
category: improvement

## Context

Loop-back 4 of ledger-decomposition-and-row-vocabulary turned 6 CodeRabbit findings on PR #1609 into TASK-14..17. Those tasks changed `_orchestrator_ledger.py`, `orchestrator.py`, `_orchestrator_inbox.py`, two tests and a concept doc. On resume the operator chose "gates + push only", so only pre-push-quality-gate, ci-verify and automatic-review re-fired. lessons-housekeeping, simplify, plugin-doctor and pre-submission-self-review did not re-fire over the code fixes. The skip left no per-step record: status.json still shows those steps as `done` at head 3a8bed617, which predates the fixes.

## Root cause

Re-fire after a loop-back is decided per run, either by `verdict_currency` or by an operator shortcut. No step declares which paths it reads, so a skip cannot be told apart from "not needed", and the step record's `head_at_completion` quietly goes stale.

## Proposed action

Derive the re-fire set from the fix commit's changed paths against each step's declared inputs. Present that set at the resume prompt. When the operator skips a step whose inputs changed, record it as `skipped_by_operator` with the stale head, not as a still-current `done`.

## Evidence

- aspect: chat_history_analysis — operator "gates + push only" after the PR-review fix round
- aspect: llm_to_script_opportunities — 4 loop-back iterations each re-fired 3-4 steps
- work.log 07:43:01 — "re-firing ci-verify and automatic-review (re-review) per operator 'gates + push only'"
