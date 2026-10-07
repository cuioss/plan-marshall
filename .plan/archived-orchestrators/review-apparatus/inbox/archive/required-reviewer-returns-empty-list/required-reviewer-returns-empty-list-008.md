envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:42:10Z

component=plan-marshall:tools-script-executor
category=anti-pattern
created=2026-09-05
bundle=plan-marshall

# Argparse rejection is a population, not incidents: 5 notations in one finalize

## Context

The dispatcher reported `signal_script_failure_clusters_count: 8` for this plan. Reading
the work log directly, **six** distinct failing notations are observable in the
`6-finalize` window alone (2026-09-04T16:09Z through 2026-09-05T16:39Z), and **five of the
six are the same failure kind**: `argparse_rejection`, exit 2, a call site disagreeing
with the script's declared flag surface.

| # | Notation | Rejection |
|---|---|---|
| 1 | `plan-marshall:phase-6-finalize:ci_verify` | `Add the required flag(s) to ... run: ['provider', 'wait-outcome', 'worktree-path']` |
| 2 | `plan-marshall:workflow-integration-github:github_pr` | `unrecognized arguments: --plan-id required-reviewer-returns-empty-list` |
| 3 | `plan-marshall:tools-integration-ci:ci` | `Use a declared flag for ... ci pr comments: ['pr-number', 'unresolved-only']` |
| 4 | `plan-marshall:automatic-review:review_completeness` | 3 x exit 2 (undeclared / mis-shaped flags) |
| 5 | `plan-marshall:manage-status:manage-status` | `argument --value: expected one argument` |
| 6 | `plan-marshall:manage-files:manage-files` | `Use --dir for ... list — declared: ['dir', 'plan-id']` |

Only #4 carries a second, different failure kind (`script_internal_failure`, exit 1 — filed
as its own candidate).

## Root cause

This is not five unrelated slips. Rows 2 and 3 are **precisely the two canonical
recurrence signatures already documented** in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script
subcommands — recurrence signatures": the verb-scoped `--plan-id` on a script that does
not declare it (row 2), and the router-scoped flag placed on the wrong side of the verb
(row 3). Row 6 is the verb-paraphrase / flag-paraphrase signature from the same list.

So the documented guard exists, names these exact shapes, and they recurred anyway inside
one phase of one plan. A prose rule that an agent must recall at every call site does not
survive contact with a long finalize.

What makes this worth filing rather than shrugging at: **the tool layer already knows the
answer.** Rows 1, 3 and 6 are not raw argparse output — they are the executor's own
enriched rejections, which enumerate the declared flag set (`declared: ['dir', 'plan-id']`)
or name the missing required flags. The information needed to make the call correctly is
computed and printed *after* the call fails. Nothing consumes it *before*.

Two of the rejections are also more than an inconvenience:

- Row 5 (`manage-status metadata --value ""`): argparse rejects an empty `--value`, so
  **clearing a metadata field is not expressible through the documented surface**. The
  caller was clearing `worktree_path` while repairing the known stale-worktree defect
  (`bd825d`) that `worktree-remove` leaves behind. The very repair path for a known defect
  is blocked by a flag contract that cannot represent the empty string.
- Row 1 (`ci_verify`): the step still recorded `outcome=done` eighteen seconds after its
  own rejection. A gate whose invocation was refused should not be able to land on `done`
  without the retry being visible.

## Proposed action

1. **Close the loop the executor already half-closes.** The rejection payload proves the
   declared surface is machine-readable at rejection time; make it readable at *compose*
   time too — a pre-flight validation of `{notation} {verb} {flags}` against the live
   argparse surface, so the enriched "declared: [...]" list is what the caller sees
   instead of what the caller gets told afterwards.
2. Fix row 5 at the contract: give `manage-status metadata` an explicit way to set a field
   to empty (`--value ""` accepted, or a `--clear` flag). While it has neither, the
   documented repair for `bd825d` is not performable as documented.
3. Fix row 1 at the gate: an `argparse_rejection` on a step's own primary script call must
   not be silently absorbed into that step's `done` outcome.
4. Treat the count itself as the finding. Individually each rejection cost a retry;
   collectively five in one phase says the guard's placement (prose, recalled per call) is
   wrong, not that five callers were careless.

## Coverage note

Six notations are enumerated above; the dispatcher's forwarded count is 8. The remaining
two lie in the pre-`6-finalize` portion of the 396-entry work log that this reading did
not page back to. The population above is therefore a **floor, not the complete set** —
stated rather than presented as exhaustive.

## Evidence

- work log `2b2714`, `b444c9`, `eeebaf`, `3d6e10` (x2), `ea325d`, `524ff2`, `cede3e` — all `failure_kind=argparse_rejection`, exit 2
- `agent-behavior-rules.md` § "Never invent script subcommands — recurrence signatures" — already documents signatures matching rows 2, 3 and 6
- work log `10f78b` — "Repaired stale worktree metadata after branch-cleanup (known defect bd825d)", the operation row 5 blocked
- work log `2b2714` at 17:09:26Z followed by `cdb431` "Completed step: ci-verify (outcome=done)" at 17:09:33Z
