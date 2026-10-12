envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:32Z

# Candidate lesson: fix-round builds logged under NO_PLAN, so the push freshness gate saw an unbuilt tree

Component: plan-marshall:build-maven / plan-marshall:phase-6-finalize (push freshness gate)
Category (proposed): bug
Source: plan code-analysis-base, phase-5 fix rounds and finalize push

## Observation

The builds run during the phase-5 review-fix rounds were recorded under `.plan/local/plans/NO_PLAN` instead of under the plan. The build wrapper call did not carry the plan context (no `--plan-id` resolved for those calls), so the build record landed in the plan-less sentinel. The push freshness gate reads the plan's build records, found none for the current tree, judged it unbuilt, and the full gate had to be re-run.

## Proposed correction

- Fix-round build dispatches (and any build in an active plan's worktree) must resolve and pass the plan id; the wrapper should derive it from the cwd-pinned worktree when the flag is absent instead of falling back to NO_PLAN.
- Alternatively the freshness gate should match build records by tree SHA regardless of the plan bucket, so a fresh build is never discarded on bookkeeping.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-004.md` from plan code-analysis-base (PLAN-36, #31)
