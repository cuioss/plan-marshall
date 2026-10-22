envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-21T12:58:18Z

# Finding: `tools-integration-ci:ci` works only for a repository with its own CI configuration; a sibling repository cannot be read or merged through it

Source: epic `pm-mcp-core-m2-m4`, 2026-10-21, while merging the documentation pull request #95 (`plan-marshall-documentation`) on the operator's word.

## Observed

- `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr view --pr-number 95` run with the working directory in `/home/oliver/git/plan-marshall-documentation`: `can't open file '.plan/execute-script.py'` (that checkout has only `.plan/local`, no executor).
- The same call through the executor of `pm-mcp-core` with the documentation checkout as the working directory: `status: error, operation: router, error: CI provider not configured. Run /marshall-steward first.` The provider is read from the checkout's own `marshal.json`; the CLI has no `--repo` selector (`pr view`, `pr merge` and `checks status` take `--pr-number` or `--head` only).
- The orchestrator's rule is to reach pull requests through `ci` only, so it could not apply it to a repository that a plan of this epic depends on. The pull request was read and merged with `gh` directly in that checkout, an exception recorded in the ledger.

## Suggestion

A `--repo` selector (or a repository argument resolved from the sibling checkout's remote) on the read and merge verbs, so the orchestrator can handle a cross-repository pull request without leaving the abstraction.
