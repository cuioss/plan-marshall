envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T14:23:30Z

# phase-1-init file-pointer rebind cannot be honoured under the Bash hard rules

## Observed

phase-1-init Step 4 (file-pointer branch) rebinds `{request_narrative}` to the INGESTED spec content
and requires Step 5c-recipe-match / Step 5c-aspect-classify to receive it via
`--request-text "{request_narrative}"`. Both verbs accept ONLY `--request-text` (confirmed via
`--help`): no `--request-file`, no `--plan-id` to read the persisted request.md.

A multi-line spec with backticks, quotes and apostrophes cannot be passed verbatim as one shell
argument without violating "Bash: one command per call" (newlines) or needing quoting constructs;
the natural move is to paraphrase/condense — exactly what the rebind forbids ("the LLM never
retypes, paraphrases, or summarises the spec body").

In this run the orchestrator FIRST passed a condensed narrative (a deviation), then re-ran both
verbs with the full spec flattened to a single line (newlines → spaces, one `'"'"'` quote escape).
Result was unchanged (no recipe match; aspect=implementation), but the contract is only satisfiable
by a lossy transform either way.

## Suggested fix

Give `recipe-match` and `aspect-classify` a `--plan-id` (read request.md body through the request
schema) or `--request-file` input, and point the phase-1-init Step 5c calls at it on the
file-pointer branch — the same script-reads-the-file principle Step 5.1 `--body-file` already uses.
