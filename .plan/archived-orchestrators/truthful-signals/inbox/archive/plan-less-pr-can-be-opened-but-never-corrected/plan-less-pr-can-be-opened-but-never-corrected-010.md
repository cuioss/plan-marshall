envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T13:04:50Z

# The finalize ceremony pre-filter drops security-audit on phase-4 placeholder inputs that are never reconciled against the realized run

- **component**: `plan-marshall:manage-execution-manifest`
- **category**: bug
- **severity**: error
- **confidence**: high
- **source**: plan-retrospective of `plan-less-pr-can-be-opened-but-never-corrected` (PR #1065)

## What the decision log recorded

At manifest-compose time (phase 4, `2026-07-29T16:04:08Z`):

```
finalize-step-simplify omitted — change_type=analysis affected_files_count=9
finalize-step-security-audit omitted — change_type=analysis affected_files_count=9
pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
```

## What was actually true

| Gate input | Value the filter used | Realized value |
|---|---|---|
| `change_type` | `analysis` | `enhancement` (per `status.metadata`) |
| `affected_files_count` | `9` | **93** files in merge `468b82279` |
| footprint | "empty" | 93 files |

Both gate inputs were wrong, in the direction that removes ceremony. A 93-file
cross-cutting change to the CI abstraction, the plan-id resolver, and the plugin-doctor
rule set had its **security audit dropped** on the premise that it was a 9-file analysis
task.

## Two aggravating details

1. **`pre-push-quality-gate` was rescued by accident.** It was omitted by the same
   empty-footprint reasoning and then re-added by an unrelated rule
   (`ceremony_finalize selection — finalize.qgate=always`). Had `finalize.qgate` not been
   `always`, this plan would have pushed with no pre-push quality gate. The correct
   outcome arrived via a rule that was not reasoning about the footprint at all.

2. **The security drop is the quieter of the two.** The composer emitted an explicit
   `lane_resolution warning` naming `finalize-step-simplify`'s removal by the ceremony
   pre-filter — and **no matching warning** for `finalize-step-security-audit`, removed by
   the same gate on the same inputs in the same pass. `check-routing-decisions` compounds
   this: its `mis_prune_checks` tracks `sonar-roundtrip` and `finalize-step-simplify` and
   does not mention `security-audit` at all.

## Why this is a regression signal, not a fresh discovery

PR #1055 (`fix(finalize): make security-audit drop live-gated and loud`) landed before
this plan. The drop here was neither live-gated (it fired on phase-4 placeholder inputs)
nor loud (plain INFO, no paired warning, absent from the routing audit). Whatever #1055
fixed, this path was not covered by it.

## Suggested direction

- The ceremony pre-filter runs at compose time, when the footprint is *necessarily* empty
  because nothing has been implemented yet. An emptiness reading at that moment carries no
  information. Gate on the **declared** outline footprint, or defer the decision to
  finalize when the realized footprint exists.
- Reconcile compose-time gate inputs against realized values at finalize and emit a loud
  finding on divergence.
- Give `security-audit` at minimum the same paired-warning treatment `simplify` already
  has, and add it to `check-routing-decisions.mis_prune_checks`.
