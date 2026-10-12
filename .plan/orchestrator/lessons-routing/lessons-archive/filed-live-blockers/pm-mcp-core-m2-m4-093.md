envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:36Z

# Give leaves a sanctioned content search when Grep is denied, so they stop using git grep

Component: plan-marshall:execution-context (leaf tool contract) / plan-marshall:persona-plan-marshall-agent
Category (proposed): anti-pattern
Confidence: high
Source: plan code-analysis-base, post-run-review retrospective (aspects permission-prompt-analysis, chat-history-analysis)

## Context

The harness denied Grep and Glob to several dispatched leaves in this plan. Two of them fell back to git's grep subcommand through Bash, which the file-operation hard rule forbids. The first was execute envelope 3 (the PM-WATCH-MOD-8 and item-count search in the sibling documentation worktree). The second was the round-2 finalize triage (a usage lookup). A third leaf (round-1 triage) used `architecture search --content` correctly.

## Root cause

`architecture search --content` covers only this repository's module inventory. A cross-repo plan has to search a sibling checkout such as plan-marshall-documentation, and the leaf had no sanctioned tool for that, so it improvised. The contract's other option, "return the coverage gap to the orchestrator", is costly in a long envelope and was skipped.

## Proposed action

Either add a sanctioned content-search verb that accepts an explicit root outside the inventory (a read-only, path-bounded search of a declared sibling checkout), or have phase-3/phase-4 record the content-search criteria of cross-repo deliverables as orchestrator-run checks. In both cases, state in the execution-context leaf contract that `git grep` is not an allowed fallback, even against another repository.

## Evidence

- aspect: chat-history-analysis: execute envelope 3 hand-back, "the Grep tool was not available, so the search ... used git's grep through Bash, against the documentation repository only"
- aspect: chat-history-analysis: round-2 triage hand-back, "Grep and Glob were denied to this subagent. I used architecture search --content and git grep"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-012.md` from plan code-analysis-base (PLAN-36, #31)
