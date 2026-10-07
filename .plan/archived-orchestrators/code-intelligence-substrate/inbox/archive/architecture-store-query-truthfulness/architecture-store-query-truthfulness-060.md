envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:58:56Z

component=plan-marshall:manage-files
category=bug

# `manage-files list` was called with an undeclared flag where `--dir` is the only one

Source: script-failure cluster, notation plan-marshall:manage-files:manage-files
(exit_code=2, failure_kind=argparse_rejection). 1 occurrence, 5-execute.

Rejection: "Use `--dir` for `plan-marshall:manage-files:manage-files list` — declared:
['dir', 'plan-id']."

## Solution

A two-flag verb still drew a paraphrased flag name. This is the cheapest possible case
for the standing rule — quote the flag verbatim from `--help` or from the skill's
canonical-invocations block rather than inferring it from the surrounding narrative —
and it still fired, which suggests the cost of a `--help` round-trip is being weighed
against the cost of a guess even when the declared set is tiny.

Worth considering for the epic: the executor already knows the declared set at rejection
time (it prints it). The same knowledge could be surfaced BEFORE the call rather than
after it.

## Impact

One wasted round-trip; representative of a broader pattern rather than costly in itself.
