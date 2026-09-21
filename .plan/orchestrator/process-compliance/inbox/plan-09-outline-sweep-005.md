envelope_version=1
sender_type=plan
sender_id=plan-09-outline-sweep
epic=process-compliance
kind=finding
created=2026-09-20T22:24:06Z

# Process-rule issue: phase_steps_complete parser reads non-step bullets plus post-archive state

plan: plan-09-outline-sweep
phase: 6-finalize post-archive verification

## Observation
`phase_handshake capture --phase 6-finalize` run AFTER `manage-status archive`
reported `phase_steps_incomplete` with two defects:

1. The `missing[]` list contains two entries that are prose from
   `required-steps.md` § Step Ownership Contract, not steps:
   `**orchestrator-owned** steps sub-dispatch ...` and
   `**leaf-dispatchable** steps are self-contained ...`. The parser keys on
   lines beginning with `- ` but does not confine itself to the `## Steps`
   section, so contract prose bullets leak into the required set.
2. The `missing[]` list names steps absent from this plan's manifest
   (`finalize-step-security-audit`, `sonar-roundtrip`, `lessons-capture`,
   `adr-propose`), although the Activation note says a step listed in the
   required file but absent from the manifest is NOT enforced. All
   manifest-scheduled required steps were marked done before archive; the
   post-archive read appears to resolve a status copy without the step
   records (or without the manifest filter).

## What was done
No action: `manage-status archive` already reported `phase_closure:
complete` and moved the plan to
`.plan/local/archived-plans/2026-09-20-plan-09-outline-sweep`. The capture
refusal is a post-terminal artifact read, not a lifecycle gap.

## Request
Confine the required-steps parser to the `## Steps` section, and make the
post-archive capture path either resolve the archived record or refuse with
a distinct `plan_archived` code instead of a misleading incomplete-steps
verdict.
