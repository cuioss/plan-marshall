envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-14T13:31:53Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan static-verifier-residuals (PLAN-56, pm-mcp-core #66, merged 7981d17), drained 2026-10-14.
> Source inbox message(s): static-verifier-residuals-003.md static-verifier-residuals-008.md 
> RECURRENCE of lessons-routing inbox messages already routed by this epic: pm-mcp-core-m2-m4-203, -213, -240 (queued); -009, -055, -096 (archived). Fold into those; this is new evidence from another plan, not a new lesson.

# Candidate lesson: cross-repository deliverables vanish from the task plan

Plan: static-verifier-residuals (PR plan-marshall/pm-mcp-core#66).
Signal source: Q-Gate finding 292092 (phase 3-outline) plus an orchestrator observation at
phase 4/finalize.

## What happened

Deliverable 8 (documentation updates in plan-marshall-documentation: implementation-watch
workflow-dsl.adoc and roadmap.adoc) first listed `../plan-marshall-documentation/...` paths as
affected files. The Q-Gate correctly flagged that `../` resolves to nothing inside the plan
worktree and would pollute references.affected_files. The fix removed those paths and described
the external change in prose only. Consequence: phase-4-plan produced NO task for the
documentation work — deliverable 8 became verification-only — and the orchestrator had to open
the issue and the documentation PR by hand. Per project CLAUDE.md, a plan that changes what a
specification states must update the documentation repository as part of its own work, so this
deliverable was mandatory, not optional.

## Candidate rule

A deliverable whose work lies in a sibling repository needs a first-class representation that
phase-4 turns into an executable task (e.g. a cross-repo task profile with a repository-qualified
target and its own PR step), not prose that the task planner cannot see. Until such a profile
exists, the outline should mark the deliverable explicitly as an orchestrator-owned manual step
so it is tracked rather than silently dropped.

## Suggested owner

plan-marshall phase-3-outline / phase-4-plan (cross-repository deliverable handling).
Classification deferred to the orchestrator.

component=plan-marshall:phase-3-outline
category=improvement
title=Model cross-repository deliverables as executable steps instead of read-only tasks

# Model cross-repository deliverables as executable steps instead of read-only tasks

## Context

Deliverable 8 of static-verifier-residuals changes two files in the sibling repository plan-marshall-documentation (watch-item retirement, roadmap) in its own PR. The outline could only declare a read-only local file for it, so phase-4-plan's verification-only guard turned it into a verification-profile task that runs `verify -Ppre-commit` locally and does none of the work. After 4-plan the operator had to decide who does the work ("I do it after execute"), and the orchestrator later ran an ad-hoc inline-instruction dispatch for it; the functional review then graded D8 met_with_residuals until the operator merged PR #72.

## Root cause

The outline and task model have no shape for an external-repository deliverable: affected files must resolve inside the worktree, and a deliverable without write-intent paths degrades to a verification task.

## Proposed action

Give the outline a declared external-repository deliverable kind (repo path, files, PR expectation) that phase-4-plan turns into an operator-attended or dispatched step with its own completion evidence (PR URL, merge state), instead of a local verification task.

## Evidence

- aspect: chat-history-analysis — pivot after 3-outline: "None of the 13 tasks covers that repository; task 13 only runs a formatting check here"
- aspect: request-result-alignment — D8 has read-intent declarations only and is judged on task status; the real work happened outside the task model
- phase-4-plan report: "If you want that work done by an agent, give D8 a write-intent path or add a manual or operator step before landing"
