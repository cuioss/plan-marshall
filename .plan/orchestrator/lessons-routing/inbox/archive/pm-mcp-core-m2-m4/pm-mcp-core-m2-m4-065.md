envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:08Z

# Candidate lesson: scope_creep_check cannot persist its own finding type and counts absorbed upstream commits as scope creep

**Signal source**: script-failure cluster (`plan-marshall:phase-5-execute:scope_creep_check`, exit 1, `failure_kind=script_internal_failure`), 4 occurrences in 5-execute (2026-10-10T20:07:22Z, 20:45:03Z, 20:49:59Z, 21:08:35Z).

**Component (suggested)**: `plan-marshall:phase-5-execute` (scope_creep_check) / `plan-marshall:manage-findings`

## What happened

1. Every run of `scope_creep_check --plan-id workflow-dsl-parser-and-ast` failed with
   `Invalid finding type: scope_creep_warning. Must be one of ('bug', 'improvement', 'anti-pattern', 'triage', 'tip', 'insight', 'best-practice', 'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'arch-constraint', 'pr-comment', 'pr-comment-overflow')`.
   The check emits a finding type that `manage-findings` does not accept, so it can never record its result (`finding_persist_failed`).
2. The residual 7 "scope creep" files it reported were upstream `main` commits (#23 workflow pins: `.github/workflows/*` x6; #24: `.plan/marshal.json`) that landed between `plan_creation_sha` c2b608b and `origin/main` 66950bb and were absorbed by the worktree baseline. They are not plan work.

## Why it matters

The check fails closed on every execute envelope, so the leaf has to hand-classify the failure each time; and the diff base (`plan_creation_sha`) does not account for upstream commits absorbed by baseline sync, so even a fixed persist path would raise false scope-creep warnings.

## Suggested direction (for orchestrator classification)

- Register `scope_creep_warning` in the manage-findings type enum, or have the check emit an accepted type.
- Diff against the merge-base with the absorbed upstream tip (or subtract the absorbed upstream commit range), not against `plan_creation_sha` alone.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-001.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
