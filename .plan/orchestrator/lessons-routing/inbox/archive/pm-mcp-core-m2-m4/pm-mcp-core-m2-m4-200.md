envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:55Z

# Default compose envelope_count from the packed tasks

Component: `plan-marshall:manage-execution-manifest` · Category: improvement · Source: plan-retrospective of `static-verifier-rule-gaps-completion`

## Context

phase-4-plan ran twice in this plan, because a plan-time Q-Gate forced a re-plan. Each time, the leaf composed the execution manifest without `--envelope-count`. It got `envelope_count: 1`, although the packer had written `envelope_id` 1 to 3 onto the tasks, and then composed again with `--envelope-count 3`. decision.log has four compose blocks for two plan passes.

## Root cause

`compose` defaults `envelope_count` to 1 when the flag is absent, even though the packed tasks already hold the answer. Callers that forget the flag record a wrong manifest until they notice.

## Proposed action

When `--envelope-count` is absent, derive it from `max(envelope_id)` over the plan's tasks, and log the value derived. Keep the flag as an explicit override, and reject a flag value that contradicts the packed tasks.

## Evidence

- aspect: manifest-decisions — 32 compose decision-log entries, 4 full compose blocks across 2 plan passes
- phase-4-plan hand-backs (both passes): "The first compose, run without the flag, recorded envelope_count: 1. I recomposed with --envelope-count 3"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-011.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
