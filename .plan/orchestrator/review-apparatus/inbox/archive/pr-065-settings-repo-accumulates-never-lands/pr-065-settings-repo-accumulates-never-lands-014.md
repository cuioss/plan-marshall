envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:21Z

component=plan-marshall:tools-script-executor
category=bug
source_signal=qgate_finding
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=qgate finding cfbbb0 (5-execute, taken_into_account); work-log ERROR 19dc7e, f2a569

# The generated executor rejected a flag the dispatched script declares, and two full regenerations did not clear it

`ci pr list --state open --limit 200` was refused PRE-SPAWN by the generated
`.plan/execute-script.py`:

```text
error=invalid_invocation reason=unknown_flag rejected=--limit
accepted=head,state exit_code=2
```

The dispatched `ci.py` declares `--limit` (confirmed by `--help` in the same
run). The executor embeds a `SCRIPT_SURFACES` accept-set derived at
generation time, consults it with no runtime digest check, and never spawns the
subprocess. Two from-scratch executor regenerations did NOT clear the stale
accept-set, which is what moves this from "regenerate and move on" to a
derivation defect in `argparse_surface`.

## Blast radius observed in this run

TASK-3 and TASK-4 both ran the refused command; the deliverable-2 gate and the
whole downstream task chain were blocked on it. The run recovered only by
dropping `--limit` and relying on the script's own default of 100 — safe here
solely because the population happened to be 48 and `truncated: false` proved it.
A population above the default would have produced a page read as a population,
which is the exact defect the plan existed to remove.

## Candidate rule

A pre-spawn validator that can be stale against the script it guards must be able
to tell "this flag does not exist" from "my surface may be out of date". A
derivation that survives two regenerations is not self-healing, so the accept-set
needs either a runtime digest check or a fail-open path on an unconfident
surface. Note the structural twin in this same run: the `manage-invocation-invalid`
plugin-doctor rule consumes an UNCONFIDENT parser surface as confident. Same
substrate, same failure shape, two consumers.
