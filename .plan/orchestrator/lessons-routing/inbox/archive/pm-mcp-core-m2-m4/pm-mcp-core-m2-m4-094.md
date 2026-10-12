envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:36Z

# Resolve execution-context workflow notations against the installed bundle, not marketplace/bundles

Component: plan-marshall:execution-context (Step 4 notation resolution)
Category (proposed): bug
Confidence: high
Source: plan code-analysis-base, post-run-review retrospective (aspect chat-history-analysis)

## Context

Two finalize leaves (create-pr and the round-2 sonar-roundtrip) reported that their workflow doc "was not at the repo-relative marketplace path". Each then located it on its own under `/Users/oliver/git/plan-marshall/target/claude/plan-marshall/skills/phase-6-finalize/workflow/`. Each leaf spent tool calls on the search, and an unlucky search could have read a stale copy or failed the dispatch with `workflow_not_found`.

## Root cause

execution-context Step 4 maps `{bundle}:{skill}/...` to `marketplace/bundles/{bundle}/skills/{skill}/...`. That tree exists only inside the plan-marshall repository. In a consumer repository such as pm-mcp-core, the bundles are installed elsewhere (the plugin base directory), so the documented mapping always misses.

## Proposed action

Resolve the notation through the same resolver the executor uses for skills (the installed plugin base directory, for example via an `execute-script` or platform-runtime path-resolution verb), and keep `marketplace/bundles/...` only as the in-repo development fallback. Document the resolution order in Step 4.

## Evidence

- aspect: chat-history-analysis: create-pr hand-back, "The workflow doc was not at the repo-relative marketplace path, so I read it from .../target/claude/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md"
- aspect: chat-history-analysis: sonar-roundtrip round-2 hand-back, "the workflow doc is not under the worktree's marketplace path"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-013.md` from plan code-analysis-base (PLAN-36, #31)
