envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:19:11Z

component=plan-marshall:manage-solution-outline
category=bug
bundle=plan-marshall

# get-module-context demands worktree resolution it does not need, and the failure is mislabelled

## Observation

Two defects, stacked, at `2026-07-29T06:18:58Z` in phase-3-outline.

**Defect A — the precondition is wrong.** `manage-solution-outline get-module-context` exited 2 with:

> `Plan 'self-ingested-reply-non-terminating-barrier-loop' reports use_worktree=true but worktree_path is empty.`

The worktree is not created until phase-5-execute Step 2.5, so this verb **cannot succeed at phase 3** for any worktree-using plan. The consequence was recorded by the phase agent itself at 06:19:14Z:

> `get-module-context returned worktree_resolution_failed at phase-3 (worktree not created until phase-5). Optional Architecture Hints section omitted. Tool-layer defect: the verb reads architecture hints and does not need worktree resolution`

The agent diagnosed it correctly and worked around it. The outline shipped without its Architecture Hints section.

**Defect B — the failure kind is wrong.** `execute-script` recorded this as `failure_kind=argparse_rejection`. It is not an argparse rejection — argparse accepted every argument; the script's own body rejected a domain precondition. The retrospective's `script-failure-analysis` then classifies it `subtype: argparse_other` with an **empty** `stderr_excerpt`, so the actual message ("worktree_path is empty") never reaches the report. A reader of the retrospective sees a nameless argparse problem in `manage-solution-outline` and has no path to the real cause.

## Why it matters

Defect A silently degrades every deep-lane outline: the Architecture Hints section is "optional", so its absence looks like a choice rather than a tool failure. Defect B is the epic theme in miniature — a classifier confidently assigning a category (`argparse_rejection`) that is precisely wrong, which then propagates into the retrospective's own findings table.

Note that exit code 2 is doing double duty here: argparse's rejection code and the script body's precondition-failure code are the same integer, so the classifier has nothing to discriminate on except stderr shape — and this failure's stderr does not match any argparse signature, which is why it lands in the `argparse_other` catch-all with no excerpt.

## Corrective rule

- **A**: remove the worktree-resolution precondition from `get-module-context` — the verb reads architecture hints and has no worktree dependency. If some sibling verb genuinely needs it, scope the precondition to that verb.
- **B**: give script-body precondition failures a distinct exit code (or a structured TOON error the wrapper reads), so `execute-script` stops labelling them `argparse_rejection` and `script-failure-analysis` can bucket them as what they are. A `stderr_excerpt` should never be empty for a recorded failure.

## Evidence

- `work.log:31` (06:18:58Z script_failure) and `work.log:32` (06:19:14Z agent diagnosis).
- This plan's `script-failure-analysis` fragment, finding 1: `anti-pattern, argparse_other, plan-marshall:manage-solution-outline:manage-solution-outline, get-module-context, exit 2, stderr_excerpt: ""`.
- `decision.log` 05:59:23Z — worktree materialization deferred to phase-5-execute Step 2.5.
