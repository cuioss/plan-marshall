envelope_version=1
sender_type=plan
sender_id=implement-plan-04-gate-comparability
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-12T10:49:17Z

# Q-Gate outline gap: deliverable 1 promised describe-side surface not in Affected files

## Context

During 3-outline Q-Gate validation for implement-plan-04-gate-comparability, deliverable 1 Change per file promised the describe-side surface update (plan-orchestrator SKILL.md cross-check paragraph stating exact normalized file-path overlap) while Affected files listed only orchestrator.py, epic_spec_parser.py (read), and test_orchestrator_corpus.py.

## Root cause

Outline Change per file text and Affected files list were authored as separate acts without a sync check, so a promised doc edit missed the declared footprint and phase-4 closure would flag declared-set drift.

## Proposed action

Enforce the sync-affected-files footprint check at outline authoring time: either add the promised doc path to Affected files with explicit Change per file text, or remove the promise before Q-Gate.

## Evidence

- aspect: qgate — phase 3-outline pending finding f01634
- component: plan-marshall:phase-3-outline
- category: improvement
- plan: implement-plan-04-gate-comparability
- file: marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md
