envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:33:05Z

component=plan-marshall:marshall-orchestrator
category=anti-pattern
title=A hand-written count that drifted is a SAMPLE of narrative-outranks-derivable, never the population

# A hand-written count that drifted is a SAMPLE of narrative-outranks-derivable, never the population

PLAN-203 was requested to fix ONE drifted hand-written count (the resume anchor's inbox count) and
carried the explicit hypothesis, prior set to *refuted*, that it was the only one. The D4 gate
enumerated the population and **refuted the hypothesis**.

## Evidence

Population swept — 7 files: `scripts/orchestrator.py`, `templates/epic.md`, `workflow/orchestrate.md`,
`workflow/analyze.md`, `workflow/resume.md`, `workflow/close.md`,
`persona-marshall-orchestrator/standards/orchestration-model.md`.

Split — **13 assertion classes DERIVABLE**: Ordered Queue order / plan id / workstream / status, the
staged-launched-shipped-parked tallies, `parallelization_scope`, `launched_count`, PR number, PR+CI
state, the `phase==closed` terminal anchor, `epic.md` Decisions vs `logs/`, and the inbox
queued/archived counts. **8 genuinely NARRATIVE**: Vision, Surface (expected), per-row Notes, Open
Defect statements, Watch statements with their re-check triggers, the closing rationale, the
next-action judgement clause of the anchor, and the operator-confirmed `running` state.

At least **three DERIVABLE surfaces beyond the fixed inbox count remain unprotected**, and one — the
`epic.md` Ordered Queue table, four derivable columns with no BEGIN/END GENERATED guard — is
**strictly larger** than the count the plan was asked to fix.

## Rule

When a request names one drifted hand-written value, treat it as a **sample of an archetype**, and
enumerate the population before scoping the fix. The corrective is structural, not disciplinary:
**render the value from its machine source at read time**. "Remember to update the prose after the
drain" is precisely the discipline that already failed — a remedy that re-asks for it has not fixed
anything.

## Impact

This is the epic's own theme (`truthful-signals`) landing in the epic's own tooling. Every
orchestrator surface that asserts a value a reader could instead derive is a live drift candidate,
and a stale assertion drifts in the **confident** direction — PLAN-109's anchor asserted 18 queued
messages and named a specific one as unarchived when the derived reader said 0 and both were already
drained.

Claim label: OBSERVED (first-party enumeration, D4 gate, mutates nothing).
