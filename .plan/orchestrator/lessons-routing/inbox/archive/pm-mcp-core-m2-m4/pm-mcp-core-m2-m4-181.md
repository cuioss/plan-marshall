envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:16Z

# Candidate lesson: treat sibling-repo deliverable paths as outside the footprint in rule M6

Source: plan-retrospective of plan verify-not-resolve (PR #43). Proposed component: `plan-marshall:plan-retrospective`. Category: bug. Confidence: high.

## Context

Deliverable 8 changed four files in the sibling repository `plan-marshall-documentation`, using absolute paths, and was delivered as that repository's PR #46. The retrospective's realized footprint only sees `pm-mcp-core`. So `check-artifact-consistency` reports recall 88% with these four files missing, and `check-manifest-consistency` rule M6 (`declared_vs_realized_set`) fails with 4 declared-but-unrealized paths. Request-result alignment cannot grade the deliverable's coverage either.

## Root cause

The footprint resolver and the declared-set comparison assume every declared path is inside the plan's own repository. A path outside the repository can never show up in the realized footprint, so the check fails by construction.

## Proposed action

Split declared paths that resolve outside the project root into their own `out_of_repo` set. Keep them out of the recall denominator and the M6 `outline_only` set, and publish the set with its size, so a cross-repo deliverable reads as "not measurable here" and not as unrealized.

## Evidence

- aspect: artifact-consistency — recall 88.2%, missing = the 4 `/Users/oliver/git/plan-marshall-documentation/...` paths
- aspect: manifest-decisions — M6 fail, 4 outline_only plus 1 references_only
- aspect: request-result-alignment — D8 fulfilled via documentation PR #46, footprint coverage 0/4 by construction

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-016.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
