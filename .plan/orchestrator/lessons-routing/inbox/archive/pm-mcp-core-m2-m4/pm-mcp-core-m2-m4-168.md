envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:56Z

# Candidate lesson: retrospective footprint misses sibling-repository deliverables

- Component: plan-marshall:plan-retrospective (shared footprint resolver; check-artifact-consistency, check-manifest-consistency, check-outline-vs-shipped)
- Suggested category: bug
- Signal: plan-retrospective (artifact-consistency, manifest-decisions, outline-vs-shipped)

## Context

Deliverables 2 and 9 changed files in the sibling checkout `../plan-marshall-documentation`, merged as docs
PR #49 (aa6c377). The footprint resolver only knows the pm-mcp-core PR #45 landing, so every declared
`../plan-marshall-documentation/...` path is reported as declared-but-unrealised. Rule M6
(`declared_vs_realized_set`) graded the plan `fail`, and outline-vs-shipped listed 15 of its 21
`include_unrealised` paths from that repository as a possible silent descope, although all of them shipped.

## Root cause

The footprint is resolved from one repository's PR or merge commit. A plan that declares paths outside the
repository root (a `../` prefix) has no tier that can see them, and the aspects do not separate "outside the
resolvable repository" from "not changed".

## Proposed action

Partition declared paths that resolve outside the repository root into their own population, reported as
`unmeasured (outside repository)` rather than unrealised, and exclude them from M6 and the recall
denominator. Optionally, resolve them from a second landing reference when the plan records one (for
example the docs PR number).

## Evidence

- artifact-consistency: recall 78% (39/50); all 10 missing paths, and all 11 `outline_only` paths, start
  with `../plan-marshall-documentation/`.
- manifest-decisions: footprint tier `pr_landing` base 45; M6 `declared_vs_realized_set` fail with
  11 declared-but-unrealised paths, all in the sibling repository.
- outline-vs-shipped: include_unrealised 21 of 60, of which 15 are `../plan-marshall-documentation/` paths.
- work.log 16:34:33: "Deliverable 2 committed in plan-marshall-documentation on branch feature/workflow-engine
  (e38e160)"; decision.log 06:28:31: operator approved merge of both PRs (#45 and docs #49).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-018.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
