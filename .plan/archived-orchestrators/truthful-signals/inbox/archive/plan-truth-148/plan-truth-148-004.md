envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:46:02Z

component=plan-marshall:phase-3-outline
category=improvement
confidence=high
source_plan=plan-truth-148
source_aspects=request_result_alignment,artifact_consistency,outline_vs_shipped

# Declare a gate-dependent file as verdict-dependent, not write-replace

## Context

Deliverables 3 and 7 of plan-truth-148 each declared `intent: write-replace` on a file the landed
commit never touched:

- D7 declared `phase-6-finalize/standards/push.md`. Its goal was to settle the claim about
  `lessons-capture` and record the verdict. The verdict was already present at push.md line 75 —
  "`default:lessons-capture` is NOT a member and never was: it declares `mutates_source: false`" —
  written by PR #1454, before this plan started.
- D3 declared `test/plan-marshall/phase-6-finalize/test_step_prompt_fields_contract.py`. That file
  already derives the four dispatcher-owned fields (`caller_phase`, `iteration`, `producer`,
  `session_id`) from `find_implementors` rather than from a hardcoded list, which is exactly what D3's
  own success criterion required of it.

Both outcomes are correct. D1 — the re-grounding gate this plan's whole shape is built around —
returned `confirmed` for both claims, and no edit was owed. The cost is paid by the metrics: D3 scored
50% declared-mutation coverage, D7 scored 0%, and artifact-consistency recall landed at 90.9% with
both files listed under `outline_only`.

## Root cause

A deliverable that depends on a gate deliverable cannot honestly declare its mutation intent at
outline time, because the gate's verdict is what decides whether the file changes. The declaration
vocabulary offers only `write-replace` and `read`, so the outline author must guess — and guessing
`write-replace` is the safe choice for planning while being the wrong one for measurement. The
coverage metric then penalises precisely the plan shape the gate exists to enable.

## Proposed action

Add a third declared intent for a file whose mutation is contingent on an upstream gate verdict, and
exclude it from the coverage denominator the way `read` already is — while keeping it in the
scope-creep comparison, so a contingent file that IS touched is still not a surprise. The mechanism
already exists for `read`; this is one more member, not a new machine.

Failing that, the narrower fix: when a deliverable declares `depends` on a gate deliverable and the
gate recorded `confirmed` for the claim that names a file, treat that file as satisfied rather than
missed.

## Evidence

- aspect: request_result_alignment — D3 `partial` at 1/2, D7 `partial` at 0/1; `declared_intent_overstatement.count: 2`
- aspect: artifact_consistency — `recall_pct: 90.9`, `outline_only[2]` naming exactly these two files
- aspect: outline_vs_shipped — `touched_but_unassessed: 27 of 27`, `include_unrealised: 0 of 0`
- corroboration — push.md's last commit is f24b19a51 (PR #1454), predating this plan
