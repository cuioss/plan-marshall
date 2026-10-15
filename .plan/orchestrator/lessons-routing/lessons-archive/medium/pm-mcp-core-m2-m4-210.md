envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:53Z

# Build review_completeness --participated-bots from producer facts, not bare bot names

## Context

In plan diagram-generator, at the pre-merge stage (09:57:29Z, branch-cleanup), the orchestrator called `plan-marshall:automatic-review:review_completeness check` with `--participated-bots coderabbit`. The script rejected it with `malformed_bot_flag`: the flag expects `bot_kind:evidence_kind` pairs (for example `coderabbit:inline`), and a bare bot_kind is refused rather than resolved to absent. The merge went ahead after a corrected call, but the barrier had failed once on a caller error.

## Root cause

The calling workflow prose leaves the orchestrator to hand-build the pair list, even though the automatic-review producer already reports each bot's participation evidence (`participated (inline)`, `participated_but_empty (issue_comment)`).

## Proposed action

Show the pair format in a worked example at the barrier's call site in the finalize and branch-cleanup docs. Better still, let the barrier read the participation evidence the step already persisted (or offer a `--from-step-facts` mode), so the LLM never builds the list.

## Evidence

- script-failure-analysis: bug/script_internal_error in plan-marshall:automatic-review:review_completeness check, exit 1
- log-analysis: work.log ERROR at 09:57:29Z with detail "--participated-bots expects bot_kind:evidence_kind pairs but received the token 'coderabbit'"

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-009.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
