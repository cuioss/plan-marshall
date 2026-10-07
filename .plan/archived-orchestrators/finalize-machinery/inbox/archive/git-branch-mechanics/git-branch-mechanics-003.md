envelope_version=1
sender_type=plan
sender_id=git-branch-mechanics
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T20:08:41Z

# Document review_completeness check flags and boolean coercion

## Context

During plan git-branch-mechanics, three argparse rejections plus one script-internal error hit the `review_completeness check` verb within about a minute (19:18:42Z-19:19:03Z), including an `unrecognized arguments: true` failure that suggests callers guess how to pass booleans to the check flags.

## Root cause

The accepted flag shape of the check subcommand is not discoverable enough at the call site, so callers probe invented spellings instead of reading `--help` first.

## Proposed action

Document the check subcommand's accepted flags in the automatic-review skill reference and normalize boolean flag coercion so a bare `true` token is rejected with a hint naming the real flag.

## Evidence

- aspect: script-failure-analysis — 3 argparse-class failures + 1 script_internal_error on plan-marshall:automatic-review:review_completeness check, 2026-09-17T19:18:42Z-19:19:03Z
- component: plan-marshall:automatic-review
- category: anti-pattern
- confidence: medium
- plan_id: git-branch-mechanics
