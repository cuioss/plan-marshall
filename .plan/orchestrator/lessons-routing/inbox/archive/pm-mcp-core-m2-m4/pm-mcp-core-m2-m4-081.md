envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:15Z

# Resolve dispatch workflow notations to the installed bundle path

**Signal source**: plan-retrospective (chat-history-analysis, llm-to-script-opportunities), finalize step of workflow-dsl-parser-and-ast.

**Component (suggested)**: `plan-marshall:execution-context` (Step 4 workflow-notation resolution)

**Category (suggested)**: bug

## Context

execution-context Step 4 resolves `{bundle}:{skill}/workflow/{file}.md` to `marketplace/bundles/{bundle}/skills/{skill}/workflow/{file}.md`. pm-mcp-core is a consumer project with no `marketplace/bundles` tree, so in this plan at least the create-pr, sonar-roundtrip and verification-feedback/triage leaves found no file at that path. Each one fell back by hand to `/Users/oliver/git/plan-marshall/target/claude/plan-marshall/skills/...` and noted it in its return. Per Step 4 the contract outcome is `workflow_not_found`, so the leaves were improvising around their own contract.

## Root cause

The notation table assumes the plan-marshall source checkout layout. In a consumer project the bundles are installed elsewhere (the plugin cache / target directory that the skill loader already uses), and the dispatcher has no resolver for it.

## Proposed action

Resolve the workflow notation through the same lookup the skill loader uses (installed plugin root, then `marketplace/bundles` for the source checkout), ideally as a script verb the orchestrator calls before dispatch so the prompt carries an absolute, verified path. Update the Step 4 table to state the consumer-project resolution.

## Evidence

- aspect: chat_history_analysis — create-pr leaf: "The workflow doc was not under the worktree's marketplace/bundles/..., so I read it from .../target/claude/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md"; sonar-roundtrip and triage leaves report the same
- aspect: llm_to_script_opportunities — candidate "locate the workflow doc when the dispatch notation does not resolve", repetition 4, complexity low
- Distinct from lessons-capture 004 (consumer-project gaps in pre-push-quality-gate and the drift probe)

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-018.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
