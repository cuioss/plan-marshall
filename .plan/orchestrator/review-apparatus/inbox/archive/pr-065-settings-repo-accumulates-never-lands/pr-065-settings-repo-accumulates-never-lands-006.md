envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:36Z

component=plan-marshall:persona-plan-marshall-agent
category=bug
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 62dc45 (2026-09-13T21:05:17Z)

# The documented recurrence signature for `architecture --plan-id` points the wrong way

`plan-marshall:manage-architecture:architecture` rejected a call with
`unrecognized arguments: --plan-id pr-065-...`, and the executor's own note read:
*"--plan-id is a top-level flag"*. The usage line it printed confirms this:

```text
architecture.py [-h] [--project-dir PROJECT_DIR] [--plan-id PLAN_ID]
                {discover,init,derived,...,enrich} ...
```

So on this surface `--plan-id` is declared on the ROUTER, ahead of the verb.

## The divergence

`persona-plan-marshall-agent/standards/agent-behavior-rules.md`
§ "Never invent script subcommands — recurrence signatures", signature 2, states
the opposite for this exact script:

> **Top-level `--plan-id` / `--project-dir` where the flag is verb-scoped** —
> placing `--plan-id` or `--project-dir` immediately after the notation on
> `manage-architecture` / `manage-config`, where those flags are declared on the
> subcommand (or named `--audit-plan-id`).

An agent obeying signature 2 moves `--plan-id` from the router position (where the
live parser declares it) to a post-verb position (where the live parser rejects
it). That is the failure observed here. The `--audit-plan-id` parenthetical is
accurate for `resolve` specifically, but the general instruction that the flag is
verb-scoped on `manage-architecture` is not what the parser declares.

## Candidate rule

This is a doc-vs-parser divergence in a document whose whole purpose is to stop
argparse rejections, so the failure it causes is one it is credited with
preventing. Re-derive signature 2 against the live `architecture.py` and
`manage-config.py` parsers and state the router-vs-subcommand split per script
(and per verb where they differ), rather than per script family. A test asserting
documented-position equals declared-position would keep it from drifting again.
