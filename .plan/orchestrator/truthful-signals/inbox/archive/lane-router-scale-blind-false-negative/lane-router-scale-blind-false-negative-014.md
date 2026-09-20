envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T19:18:20Z

component=plan-marshall:tools-script-executor
category=anti-pattern
bundle=plan-marshall

# 13 argparse rejections in one plan — and one of them was a manifest naming an executor that does not exist

`script-failure-analysis` over this plan's `script-execution.log`: **15 non-zero-exit script
calls, 13 unique**, roughly one per hour of wall-clock. Spread across ten different
components:

| Component | Subtype |
|---|---|
| `manage-status` (`planning-lane`) | invented_flag |
| `manage-findings` (`qgate`) | invented_subcommand, argparse_other, invented_flag ×2 |
| `manage-references` (`get`) | missing_required_flag |
| `manage-lessons` (`list`) | invented_flag |
| `manage-logging` (`decision`) | invented_subcommand |
| `run_config` (`get`) | invented_subcommand |
| `tools-integration-ci` (`checks`) | invented_flag (`--plan-id` on a verb that has none) |
| `phase-6-finalize:ci_verify` (`run`) | missing_required_flag |
| `automatic-review:review_completeness` (`check`) | argparse_other ×2 |
| `workflow-integration-github:github_pr` (`bot_completion`) | missing_required_flag |
| `phase-6-finalize:finalize_step_preference_emitter` | **script_internal_error** |

These are the exact four recurrence signatures the always-loaded persona enumerates. The
guidance is loaded on every dispatch and the rate is still one per hour. Guidance is not
working as the control here.

**The last row is not a caller error.** `finalize_step_preference_emitter` failed with:

> `Invalid notation: 'plan-marshall:phase-6-finalize:finalize_step_preference_emitter' — the
> third part appears to be a subcommand, not a script name.`

The execution manifest names a finalize step whose executor notation **does not resolve at
all**. The step recorded `outcome=skipped` with the honest detail *"no aggregation
performed, not asserted clean"* — the workflow did the right thing — but the consequence is
that **no preference/disposition aggregation ran on a plan carrying 12 FIX dispositions
concentrated in `manage-config` and `manage-execution-manifest`**, which very plausibly
crossed `preference_min_recurrence=2`. A whole finalize step was a no-op and the plan found
out at execution time.

## Solution

- **Validate every manifest-named executor notation at compose time**, not at execution
  time. `manage-execution-manifest compose` already enumerates the step set; resolving each
  step's notation against the executor's `SCRIPTS` mapping there turns a silent
  execution-time skip into a loud compose-time failure.
- **Fix the `finalize-step-preference-emitter` notation** (or the manifest entry that names
  it) so the step actually runs.
- **Treat the 13-rejection rate as a tooling problem, not a discipline problem.** Two
  structural levers exist and neither is fully used: the `ARGUMENT_NAMING_*` plugin-doctor
  cluster catches drift in *docs*, but nothing catches an invented verb at *call* time. A
  `did-you-mean`-free hard failure is already what happens; what is missing is that the
  failures are invisible until a retrospective counts them. Surface a per-plan
  argparse-rejection count in the finalize summary so the rate is observed while the plan is
  running.

## Impact

The rejection rate is a standing tax on every plan (each one costs a retry round-trip). The
manifest-names-an-unresolvable-executor defect is sharper and narrower: it is a
**silently-skipped finalize step**, and the only reason it is visible at all is that this
plan's workflow chose to log the skip as "not asserted clean" rather than as done. A less
careful step would have recorded a green outcome for work it never performed.
