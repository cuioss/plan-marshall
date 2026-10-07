envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:27:11Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
created=2026-09-03

# `ci pr prepare-body` / `ci pr edit` invoked without their verb-scoped `--plan-id`

At 2026-09-03T17:38Z and 17:39Z (plan `always-on-is-not-a-resolve`), two
`plan-marshall:tools-integration-ci:ci` calls were rejected by argparse
(`exit_code=2`, `failure_kind=argparse_rejection`):

```text
ci.py pr prepare-body: error: the following arguments are required: --plan-id
ci.py pr edit: error: the following arguments are required: --plan-id
```

This is the exact split the `ci` surface is documented to have, hit from the
wrong side. On `ci`, `--plan-id` is *router*-scoped for the read verbs (the
`checks` read verbs, `pr view`, `pr list`, `pr wait-for-comments`) and must
appear BEFORE the first positional. But the body-consumer verbs —
`pr prepare-body`, `pr prepare-comment`, `pr edit` — declare a **required**
`--plan-id` of their own AFTER the verb. A pre-verb flag is swallowed by the
router, and the subparser then rejects the call for a missing required
argument, which is precisely the message observed.

## Solution

Position `--plan-id` per verb, not per script:

```bash
# read verbs: BEFORE the first positional
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id PLAN_ID pr view --pr-number N

# body-consumer verbs: AFTER the verb
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr prepare-body --plan-id PLAN_ID --for edit
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  pr edit --pr-number N --plan-id PLAN_ID --slot SLOT
```

## Impact

Recurrence signature 4 in `persona-plan-marshall-agent` § "Never invent script
subcommands" already names this surface, and the `execution-context` envelope
restates it — yet the rejection still fired twice in one run. That suggests the
knowledge is present but not reachable at call time. Worth considering whether
the finalize workflow doc that issues these two calls shows them with the flag
in the correct post-verb position, since the documented form is what a caller
copies.
