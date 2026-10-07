envelope_version=1
sender_type=plan
sender_id=plan-02-worktree-discipline
epic=process-compliance
kind=candidate-lesson
created=2026-09-20T13:09:17Z

component=plan-marshall:plan-retrospective
category=anti-pattern
bundle=plan-marshall
created=2026-09-20

# Retrospective and logging probes need exact verbs: check-artifact-consistency run, manage-logging read

Two argparse rejections in the same late-session observability probe
(plan-02-worktree-discipline, 2026-09-20T12:56:55Z and 2026-09-20T12:59:26Z):
`plan-marshall:plan-retrospective:check-artifact-consistency run` and
`plan-marshall:manage-logging:manage-logging read` each exited 2
(argparse_other). Probing the retrospective/logging surface with a
half-remembered flag set fails at the parser, so the observation the probe
was built to collect never happens.

## Solution

Resolve probe verbs through `--help` (or the executor accept-set) before
running them, especially for retrospective helpers whose verbs differ per
check script (`run` plus required `--mode`/`--plan-id`). Keep one verified
probe spelling per check instead of re-deriving it per session.

## Impact

Retrospective evidence collection (script-failure analysis, log reads) in any
plan running post-hoc verification probes.
