envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule gap: invented a script flag instead of quoting the declared surface

## Observed

- Ran `manage-logging read --plan-id test-fidelity-rules-follow-up --lines 50`.
- The verb rejected it: `unknown_flag`, rejected `--lines`, accepted `limit, phase, plan-id, store, type`.
- Re-read the verb `--help` and re-issued with the declared flags (`--type work --limit 50`), which succeeded.

## Conflict

- Hard rule: quote script subcommands and flags verbatim from the executor mapping or `--help`; never extrapolate plausible names.
- The `--lines` form read naturally but does not exist on this verb. The rejection bypassed the script body.

## What was done on this run

- No state was written by the rejected call (exit before the body).
- Corrected to the canonical `--type {script,work,decision} --limit N` shape; the follow-up `read --type work --limit 50` returned 13 entries.
- Recorded here rather than left silent.

## Request

- No product change requested; filing as a self-caught recurrence data point for the verb-paraphrase/flag-invention class.
