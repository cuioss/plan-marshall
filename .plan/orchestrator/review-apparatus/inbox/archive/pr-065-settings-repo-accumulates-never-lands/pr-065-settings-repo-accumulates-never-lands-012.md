envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:10Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR d18749 (2026-09-14T17:37:04Z)

# The documented signature-4 rejection recurred verbatim inside finalize

`plan-marshall:tools-integration-ci:ci` was called with `--plan-id` AFTER the
verb and rejected:

```text
ci.py: error: unrecognized arguments: --plan-id pr-065-...
note: --plan-id is a top-level flag and belongs BEFORE the subcommand (verb),
not after it. ... e.g. `... ci --plan-id pr-065-... pr view`.
```

This is exactly recurrence signature 4 in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md`, which documents
this script, this flag, this direction, and even this `pr view` example. The
guard fired and the failure happened anyway.

## Why it matters to this epic

The rejection message is excellent — it prints the caller's own invocation with
the flag moved. The documentation is also correct. What is missing is anything
that reaches the agent *before* the call: signature 4 is prose in a standards
document that a finalize-step envelope may never have loaded, while the CI
surface's own workflow bodies place `--plan-id` in both positions depending on
the verb (router-consumed before the verb for the read verbs; required after the
verb for `prepare-body` / `prepare-comment`). An agent holding both facts and no
per-verb table guesses.

## Candidate rule

The per-verb position split on the `ci` surface is the real hazard — the same
flag name is legal in two positions on one script depending on the verb. A table
in `tools-integration-ci` mapping verb to required `--plan-id` position would
turn the guess into a lookup, and it belongs next to the verbs rather than in a
persona standard.
