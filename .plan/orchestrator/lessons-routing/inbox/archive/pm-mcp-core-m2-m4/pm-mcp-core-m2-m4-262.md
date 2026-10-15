envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:32Z

# Candidate lesson: Carry project-local skills such as traced-implementation into every task

**Component (suggested):** plan-marshall:phase-4-plan
**Category (suggested):** improvement

## Context

The pm-mcp-core CLAUDE.md says every concrete implementation follows the project skill
`traced-implementation`. In plan-17-project-units-and-invariants, 4-plan could not put it in any task's
`skills[]`, because it is a project-local skill and not a `{bundle}:{skill}` notation. Only TASK-1's
description told the executor to follow it; the 4-plan leaf reported that "the other tasks lack that
instruction". The executors of TASK-2 to TASK-21 therefore depended on the leaf's own judgement to apply it
(the TASK-12 executor did, when it fixed the PlanUnitMerger header mismatch).

## Root cause

Task skill resolution accepts only bundle skill notations, and there is no channel for project-local skills
that the project's instructions make mandatory.

## Proposed action

Let task skill resolution carry project-local skills (for example from `.claude/skills/` or a project
setting in marshal.json) into `skills[]`, or stamp a standing instruction into every task description when
the project declares such a skill mandatory.

## Evidence

- aspect: chat_history_analysis: 4-plan report, "traced-implementation is not a bundle:skill notation, so it is not in any task's skills[]. TASK-1's description tells the executor to follow it. The other tasks lack that instruction."
- aspect: artifact_consistency: TASK-001 skills[] holds 9 bundle skills and no traced-implementation; its description carries the instruction

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-011.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
