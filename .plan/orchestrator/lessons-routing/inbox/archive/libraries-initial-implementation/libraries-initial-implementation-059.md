envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:38Z

component=plan-marshall:manage-execution-manifest
category=improvement
title=scope the per-task quality gate to the task's module instead of whole-tree verify on every task
source_lesson=2026-11-23-12-005
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# scope the per-task quality gate to the task's module instead of whole-tree verify on every task

# Candidate lesson: the per-task gate stamp appends the whole-tree verify to every task

- Source signal: plan-retrospective of plan-23-forms-hardening (inbox plan-23-forms-hardening-013; plan_efficiency, log_analysis, manifest_decisions and llm_to_script_opportunities aspects).

## What happened

At 4-plan the compose logged `per_task_gate_appended — appended the resolved gate command to 18 task verification lists`. Each task then ran the whole-tree `verify -Ppre-commit` (1,402 to 1,461 tests); the plan made 44 maven calls that own 79.7 % of all script time (5,578 s, about 93 min), and leaves repeatedly skipped the per-deliverable focused build with a logged judgement that the green whole-tree gate on the identical tree already covered it (4 logged skips).

## Candidate rule

Stamp a module-scoped gate (for example `verify -Ppre-commit -pl {module} -am`) on each task and keep the whole-tree gate for the end-of-execute sweep, or let the build wrapper report a tree-hash cache hit so a redundant build is skipped by fact. Owning component: `plan-marshall:manage-execution-manifest`. Related to the module-tests tier lesson `2026-11-18-18-003` and the loop-back re-fire lesson `2026-11-18-07-007`.
