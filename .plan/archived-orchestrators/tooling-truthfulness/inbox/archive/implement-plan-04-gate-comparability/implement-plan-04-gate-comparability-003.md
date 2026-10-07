envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:49:24Z

# Q-Gate outline gap: deliverable 2 promised describe-side schema updates not in Affected files

## Context

During 3-outline Q-Gate validation for implement-plan-04-gate-comparability, deliverable 2 Change per file promised describe-side schema updates (plan-orchestrator SKILL.md cross-check paragraph and persona-plan-orchestrator orchestration-model.md) while Affected files listed only orchestrator.py and test_orchestrator_corpus.py.

## Root cause

Same outline authoring gap as deliverable 1: Change per file promises and Affected files list drifted, so sync-affected-files footprint misses the docs and phase-4 closure flags declared-set drift.

## Proposed action

Apply the same sync-affected-files check to every deliverable: add both promised doc paths to Affected files with explicit Change per file text, or remove the promise.

## Evidence

- aspect: qgate — phase 3-outline pending finding 46d315
- component: plan-marshall:phase-3-outline
- category: improvement
- plan: implement-plan-04-gate-comparability
- file: marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md
