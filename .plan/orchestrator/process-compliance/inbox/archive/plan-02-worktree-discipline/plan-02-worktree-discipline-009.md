envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:08:43Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
bundle=plan-marshall
created=2026-09-20

# ci router-scoped --plan-id belongs BEFORE the verb, never after pr

Argparse rejection in plan-02-worktree-discipline (2026-09-20T00:28:35Z):
`plan-marshall:tools-integration-ci:ci pr ... --plan-id plan-02-worktree-discipline`
exits 2 with `unrecognized arguments: --plan-id ...; note: --plan-id is a
top-level flag and belongs BEFORE the subcommand`.

The `ci` router consumes `--plan-id` only ahead of the first verb token for
its read verbs (`checks`, `pr view`, `pr list`, `pr wait-for-comments`), which
declare no `--plan-id` of their own. Placing it after `pr` is an argparse
rejection, the mirror of the verb-scoped case. Body-consumer and
prepare-body/prepare-comment verbs declare their own required `--plan-id`
AFTER their verb instead.

## Solution

Read the script canonical-invocation block per verb: pre-verb `--plan-id`
only for the router-consumed read verbs, post-verb where the subparser
declares it, nothing where it is undeclared. Never append `--plan-id` by rote.

## Impact

Every `ci` call site; wrong placement bypasses the script body with exit 2.
