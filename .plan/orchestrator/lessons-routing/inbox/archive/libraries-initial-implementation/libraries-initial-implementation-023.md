envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:15Z

component=plan-marshall:automatic-review
category=anti-pattern
title=review_completeness: --finished-review-bots takes bare bot_kind tokens, pair-shaped tokens belong on the pair flags
source_lesson=2026-11-19-06-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# review_completeness: --finished-review-bots takes bare bot_kind tokens, pair-shaped tokens belong on the pair flags

# Candidate lesson: a pair-shaped token is passed to the bare-form flag `review_completeness --finished-review-bots`

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-007), script_failure cluster `plan-marshall:automatic-review:review_completeness` (automatic-review step, first pass on PR #31).

## What happened

```
exit_code=1 failure_kind=script_internal_failure detail=status: error / error: malformed_bot_flag /
"--finished-review-bots expects bare bot_kind tokens but received the pair-shaped token 'coderabbit:review_body'."
```

The agent passed a `bot_kind:value` pair to the bare-form flag. The script's guard caught it and the step still completed `done`, but only after a retry.

## Candidate rule

Where the automatic-review workflow assembles the `review_completeness` call, state next to the call which flags take bare `bot_kind` tokens and which take `bot_kind:value` pairs, with one example of each, so the agent does not have to infer the form from the observed bot evidence.
