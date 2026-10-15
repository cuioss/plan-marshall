envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:11Z

# Re-check docs-only footprint before re-running the full build on loop-back

## Context

Plan 39 changed 62 files, all of them documentation (manifest-decisions: documentation 62, production 0, test 0). The pre-push quality gate fired 8 times, once per finalize pass. Most passes followed review-triage loop-backs for one-sentence ADR rewordings. Every firing ran the full `verify -Ppre-commit` (315-445s) plus a short follow-up build. That is 16 Maven runs and 2947s, about 49 minutes of build time for a diff with no code in it.

## Root cause

Manifest compose kept pre-push-quality-gate "on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed". At outline time no worktree existed, so the footprint could not be classified. The decision was never re-evaluated once the realized footprint resolved to documentation only.

## Proposed action

At each pre-push-quality-gate firing (or at least on a loop-back re-entry), re-classify the realized footprint. When it is documentation-only and the module build cannot be affected, run the cheap check (asciidoc/link validation) or skip with a logged reason instead of the full verify. Another option is to re-run the compose-time prune predicate once the worktree footprint exists.

## Evidence

- plan-efficiency: 7.4M tokens; 6-finalize took 64% of them; 8 pre-push-quality-gate firings
- log-analysis: plan-marshall:build-maven:maven 16 calls, 2947s cumulative (21% of all script time)
- manifest-decisions: decision.log 4ffcc8 "kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable"; realized footprint 62 documentation files

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-008.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
