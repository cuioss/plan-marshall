envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:22:43Z

# Script surface drift: documented verbs and flags the scripts do not declare

Severity: high. Bundle: **plan-marshall** (`tools-script-executor`, and every workflow doc that quotes a command). Filed under RULING 2026-10-09 (a).

Recurrence of `lessons-routing-023` (Q-Gate hash primitive) and of the argparse class filed across `-023`, `-033`.

## Sources

- corpus `2026-10-22-12-001` (the flag-declaration lesson; itself sourced from live-blockers `lb-49-opencode-measurement-002`)
- inbox `pm-mcp-core-m2-m4-298`, `-299`, `-303`, `-304`, `-305`, `-315`, `-316`, `-318`, `-319`, `-320`, `-343`, `-357`, `-360`, `-361`, `-362`, `-363`, `-379`, `-381`, `-382`, `-394`, `-402`

## Consolidated statement

Across the `pm-mcp-core` plans of 2026-10-17..2026-10-22, argparse rejections (exit 2, before the script body ran) are the dominant script-failure class: 41 `ERROR` rows in one plan's `script-execution.log`, 16 failures across 8 distinct notations in another, and 5 in a single finalize run. The recurring shape is a caller — human or leaf — writing a flag set from workflow prose or from a neighbouring verb instead of from the script's own declaration.

Named occurrences, by script:

- `manage-change-ledger`: `query --plan-id` (7x) and `append --plan-id` — neither verb declares `--plan-id`; the store is cwd-resolved. An invented `read` verb was also called.
- `manage-findings qgate`: invented `query` (the read verb is `list`); `add --type warning` where `warning` is a severity, not a finding type (5 findings never recorded).
- `manage-solution-outline`: invented `deliverable-hashes` (rejected in one dispatch, accepted minutes later — verb-guard/skew discrepancy); `--number` instead of `--deliverable-number`.
- `manage-tasks`: `finalize-step --verification-owed` (flag not declared; two dispatches 14 h apart); `get --field`; `read --task-id`.
- `manage-architecture`: invented `search --path`; `--plan-id` placed before the verb; `search … --literal false` (store_true given a value); `resolve … --plan-id` where the verb does not take it.
- `build-maven`: invented `resolve-test-scope`; `build_server` called as a maven verb (it is `plan-marshall:build-server-client:build_server`).
- `manage-config`: `resolve-outline-skill --audit-plan-id` — the documented Step 9a invocation cannot run; the verb declares only repeatable `--domain`.
- `manage-logging read`, `run_config commit-trailer`, `manage-references list`, `manage-adr scan`: the same rote `--plan-id`.
- `phase-6-finalize ci_complete_precondition`: required `--worktree-path` omitted, although cwd-pinning makes callers stop passing it.
- `review_support validate --findings-file` where the flag is `--verdict-file`.
- `ci checks`: `ci checks 131`, `--job-id`, missing `run-id`.

Cost is paid per occurrence and never accumulates into one visible failure: every rejection costs a round trip, and in at least three cases the calling step fell back to a **weaker evidence path** rather than retrying correctly. The "never append `--plan-id` by rote" instruction already exists in `agents/execution-context.md` and did not prevent it.

## What is asked

1. Give `execute-script.py` a validation mode that builds the target script's real argparse parser and parses the requested argv without executing it, returning the accept-set on rejection (the executor already reports `accepted:`).
2. Sweep the workflow docs for `--plan-id` (and for the other named flags) on the scripts whose parsers do not declare them, and delete the flag from those call sites.
3. Make the argparse error name the accepted sub-verbs and flags, so a retry needs no guesswork; keep the argparse stderr line in `script-execution.log` (four of eight clusters had an empty `stderr_excerpt`).
4. Fix `phase-3-outline` Step 9a to the bare `resolve-outline-skill --domain …` form, or cite the canonical block instead of restating the command; add a plugin-doctor rule for a `{placeholder}`-free canonical mismatch.
5. Add a contract test that every verb a workflow document invokes exists in the registered argparse surface of its notation.

## Evidence

As recorded by the senders in the sources above. Not re-verified against HEAD in this run.
