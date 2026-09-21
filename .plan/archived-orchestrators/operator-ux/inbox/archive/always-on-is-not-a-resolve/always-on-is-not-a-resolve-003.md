envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:22:08Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
bundle=plan-marshall
confidence=high

# Make ci pr prepare-body reject a router-position --plan-id by name

## Context

Plan `always-on-is-not-a-resolve` recorded two argparse rejections against
`plan-marshall:tools-integration-ci:ci pr prepare-body`, both at
2026-09-03T17:38:29Z, with the stderr:

```text
usage: ci.py pr prepare-body [-h] --plan-id PLAN_ID [--for {create,edit}] [--slot SLOT]
ci.py pr prepare-body: error: the following arguments are required: --plan-id
```

The caller supplied `--plan-id`. It was consumed by the `ci` router, which reads
that flag before the provider subparser is built, so `prepare-body` — which
declares its own required `--plan-id` after the verb — never saw it and reported
it as missing.

## Root cause

`ci` declares `--plan-id` at two levels with opposite position requirements: the
router consumes it ahead of the first verb for the read verbs, while
`prepare-body` / `prepare-comment` declare a required `--plan-id` after their own
verb. Which position is correct depends on the verb, and the error message names
neither. This is documented by name in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` as recurrence
signatures 2 and 4, and it recurred anyway — documentation alone has not held.

## Proposed action

Make the failure self-correcting at the point it fires, the way the router's
mirror case already does: when a `prepare-body` / `prepare-comment` invocation is
missing its subcommand `--plan-id` **and** the router consumed one, reject with a
message that prints the caller's own invocation with the flag moved after the
verb. The router already holds the swallowed value, so the corrected form is
constructible without guessing.

A structural alternative worth weighing: stop the router from consuming
`--plan-id` when the resolved verb declares its own.

## Evidence

- aspect: script_failure_analysis — `anti-pattern / missing_required_flag`, component `plan-marshall:tools-integration-ci:ci`, exit 2, occurrence_count 2
- aspect: log_analysis — `errors_script: 8` across 4 unique argparse signatures in one plan
