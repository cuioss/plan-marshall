envelope_version=1
sender_type=plan
sender_id=compliant-paths
epic=process-compliance
kind=finding
created=2026-09-19T14:57:01Z

# Process-rule issue: phase-1-init doc invents --request-text for domain-detect (argparse_rejection)

Epic: process-compliance
Plan: compliant-paths
Kind: finding

## Observation

`phase-1-init/SKILL.md` workflow prose implies `manage-config domain-detect` consumes `--request-text "{request_narrative}"` alongside recipe-match/aspect-classify.

Live `--help` walk rejects it:

`--request-text is not declared for domain-detect: ['affected-files', 'domain-override', 'field', 'plan-id']`

Correct invocation is plan-scoped:

`manage-config domain-detect --plan-id {plan_id}`

## Impact

Caller following skill prose verbatim hits `exit_code: 2` argparse_rejection, bypassing the script body. This is the verb-paraphrase/flag-invention recurrence signature owned by `pm-plugin-development:recipe-fix-argparse-rejection`.

## Request

Correct the phase-1-init doc to route domain detection through `--plan-id` (with `--affected-files` file signal), or extend the verb to accept `--request-text`. Add a plugin-doctor rule or canonical-block check so the doc cannot drift from argparse again.
