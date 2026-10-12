envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T20:00:34Z

# Candidate lesson: empty-string --value is stripped by the executor, so the documented quoted-empty form fails

**Signal source**: script-failure cluster (`signal_script_failure_clusters_count`)

**Components**: `plan-marshall:manage-execution-manifest` (`step-params set`), `plan-marshall:manage-references` (`set-list`), and the shared executor `plan-marshall:tools-script-executor` (`.plan/execute-script.py`)

## Observation

Passing an empty value as `--value ""` is rejected by argparse with `expected one argument`. The executor drops empty-string arguments before the script sees them, so `--value` arrives without its operand. Only the `--value=` form (flag and empty value fused into one token) works.

The documented quoted-empty form therefore does not work as written. It was hit twice in this run:

- phase 3: clearing the domain via `manage-execution-manifest step-params set`
- phase 6: clearing `required_bots` via `manage-references set-list`

## Suggested corrective action (for orchestrator triage)

Either have the executor pass empty-string arguments through unchanged, or document `--value=` as the only supported way to send an empty value on every verb that accepts one, ideally with a dedicated `--clear` flag instead. Add a regression test that drives an empty value through `execute-script.py`, not only through the script's own parser.

Category guess: bug

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-38-review-bot-re-review-001.md` from plan plan-38-review-bot-re-review (PLAN-38, #24)
