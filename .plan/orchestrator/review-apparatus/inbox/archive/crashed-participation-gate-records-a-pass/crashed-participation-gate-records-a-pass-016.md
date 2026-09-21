envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:36:52Z

# extract-chat-signal retains no operator decision turns

component: plan-marshall:plan-retrospective
category: improvement
confidence: medium
source: plan-retrospective (aspect: chat-history-analysis)
suggested_epic: truthful-signals

## Context

`extract-chat-signal` reduced this run's transcript from **1163 turns to 2** (685 bytes), reporting `no_signal: false` and `over_budget: false` — i.e. Tier 1, a clean successful extraction. The two retained turns are:

1. the `/plan-marshall:plan-marshall` invocation line, and
2. a background task-notification ("Wait for PR 1070 to leave OPEN state" completed, exit 0).

Neither is an operator decision. Meanwhile the run recorded three distinct operator interventions, all of which survive ONLY outside the transcript aspect:

- **12:40:33** — user review recorded a change request against solution_outline.md (fold the fetch_findings sites + github_pr.py flag declarations into D1). This forced an outline re-entry.
- **18:57:22** — the operator chose merge-now on a KNOWN-PARTIAL review (coderabbit rate-limited, pr-agent had not seen the final HEAD).
- **13:03:14** — operator-answered bot lists (`bot_lists_provenance: answered`).

## Root cause

The extractor's signal grammar does not treat `AskUserQuestion` answers / gate dispositions as signal. Its output is therefore structurally unable to contribute the one input the chat aspect is uniquely positioned to supply, and `finalize-step-preference-emitter` — which exists to learn recurring operator gate-dispositions — has to work from the findings ledger instead.

The reporting shape compounds it: `no_signal: false` on a 1163 -> 2 reduction reads as "signal was found", when what was found is an invocation echo and a job notification. There is no field distinguishing "retained substantive turns" from "retained boilerplate", so the aspect cannot self-report its own emptiness.

## Proposed action

1. Add operator gate-dispositions to the extractor's retained grammar: `AskUserQuestion` prompt/answer pairs, review-gate change requests, and merge/no-merge decisions.
2. Emit a `retained_substantive_turn_count` alongside `reduced_turn_count` so a reduction that keeps only boilerplate is visible as such rather than reported as a successful extraction.
3. Calibration caveat: this is ONE observation. Whether the grammar drops operator turns generally, or whether this session's operator input simply arrived through channels the transcript does not carry, is UNMEASURED. Confirm against the archived-plan corpus before treating it as a general defect — that is why this is filed at medium confidence.

## Evidence

- `extract-chat-signal run` output — `raw_turn_count: 1163`, `reduced_turn_count: 2`, `dropped_turn_count: 1161`, `reduced_bytes: 685`, `no_signal: false`
- `logs/decision.log:22` (D1 widening change request), `logs/decision.log:79` (merge-now on known-partial review)
- `execution.toon` phase_6 step_params.automatic-review — `bot_lists_provenance: answered`
- `status.metadata.phase_steps["6-finalize"]["finalize-step-preference-emitter"]` — "0 patterns promoted, 2 skipped"
