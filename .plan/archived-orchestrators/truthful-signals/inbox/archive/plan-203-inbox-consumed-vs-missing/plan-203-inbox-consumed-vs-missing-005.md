envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T09:34:02Z

component=plan-marshall:marshall-orchestrator
category=bug
title=The resume anchor asserts a PR number and CI state in prose that both sides could derive

# The resume anchor asserts a PR number and CI state in prose that both sides could derive

STAGED by PLAN-203's D4 gate, not fixed. Surface:
`marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/resume.md` and the canonical
anchor example in `persona-marshall-orchestrator/standards/orchestration-model.md`.

## Observation

The canonical `resume_anchor` example reads *"await PR #912 CI, then analyze landing"*. Both halves of
the factual clause are DERIVABLE:

- the PR number is held by `status.json` `plans[].pr`;
- the live CI state is retrievable through read-side `plan-marshall:tools-integration-ci:ci` calls
  (a read-side `ci` call already sits inside the orchestrator's small-ops carve-out).

Only *"then analyze landing"* — the operator's next-action judgement — is genuinely narrative.

## Why it matters

An anchor naming a PR that has since merged is **the same defect class as the drifted inbox count**:
a confident sentence asserting pending work that is already done. PLAN-203 fixed exactly that shape one
field over.

## Rule

Render the derived PR + CI state **beside** the anchor at read time and keep the narrative clause to
the judgement it actually carries. Never let the factual half of an anchor sentence be the only copy
of a value the machine holds.

Claim label: OBSERVED (first-party enumeration, D4 gate). The read-side `ci` availability is OBSERVED;
the render-site design is unspecified and left to the fixing plan.
