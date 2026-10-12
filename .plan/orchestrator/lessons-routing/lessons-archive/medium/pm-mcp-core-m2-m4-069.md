envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T16:59:10Z

# Candidate lesson: automatic-review workflow doc and the review_completeness / github_pr script surfaces disagree

**Signal source**: automatic-review step (signal_automated_review_count=1) plus a script-failure record (argparse rejection) in its third iteration.

**Component (suggested)**: `plan-marshall:automatic-review`, `plan-marshall:workflow-integration-github`

## Evidence

- Work log 2026-10-11T14:48:39Z: `[ERROR] script_failure notation=plan-marshall:automatic-review:review_completeness exit_code=2 failure_kind=argparse_rejection detail=--required-bots is not declared for review_completeness trigger-bot: ['newest-kind', 'plan-id', 'stale-bots'] — flag --required-bots is declared on sibling verb(s): review_completeness check --required-bots, review_completeness deficit --required-bots`.
- The automatic-review leaf reported that the `github_pr bot_completion` argparse surface also differs from what the workflow doc shows. This half is the orchestrator's report and does not appear in the plan logs. Check it against live `--help` before acting on it.

## Why it matters

The leaf followed the workflow doc and got an argparse rejection, then had to recover by reading `--help`. Every automatic-review run that reaches the trigger-bot path repeats this.

## Suggested direction (for orchestrator classification)

Align `automatic-review` workflow docs with the live argparse surfaces of `review_completeness trigger-bot` (it takes `--stale-bots`, not `--required-bots`) and of `github_pr bot_completion`. Make the docs cite each script's canonical-invocations block instead of restating the command.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-dsl-parser-and-ast-005.md` from plan workflow-dsl-parser-and-ast (PLAN-07, #27)
