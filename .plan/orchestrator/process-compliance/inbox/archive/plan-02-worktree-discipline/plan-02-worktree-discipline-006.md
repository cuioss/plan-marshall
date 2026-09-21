envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:02:05Z

# Place router-scoped --plan-id before the ci verb

## Context

During plan-02-worktree-discipline finalize, a `plan-marshall:tools-integration-ci:ci pr` call passed `--plan-id` after the verb and was rejected with exit 2. The same plan merged cleanly (PR #1547 via queue) after the retry with the flag before the verb.

## Root cause

On the ci surface `--plan-id` is a top-level router flag consumed before the subcommand verb; placed after the verb it reads as an unrecognized argument to the subparser.

## Proposed action

Keep the router-position rule in the canonical-forms guard and cite it in the ci retry path: `--plan-id` before the verb on read verbs, after the verb only where the subparser declares it.

## Evidence

- aspect: script_failure_analysis — invented_flag in tools-integration-ci:ci pr, exit 2, 2026-09-20T00:28:35Z
- aspect: request_result_alignment — review-versus-gate delta: pre-push-quality-gate done, pre-submission-self-review done
