envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:30:09Z

# Two deferrals that arrive nowhere: a set mismatch handed to an aspect with no rule, and 25 of 29 failures classified from stderr that was never captured

component: plan-marshall:plan-retrospective
category: bug
severity: warning
source_plan: detector-and-auditor-integrity
source_pr: 1370

## Finding A — the declared-vs-realized mismatch is deferred to an aspect that cannot receive it

`check-artifact-consistency` found a real footprint disagreement in both
directions on this plan — 2 paths declared in the outline and absent from
references, 17 paths in references never declared — and reported it at **info**
severity with the message:

> "Set mismatch — deferred to manifest aspect (see check-manifest-consistency)"

`check-manifest-consistency` ran on the same plan and its entire rule set is:
`manifest_version_recognized`, `docs_only_diff` (M1), `early_terminate_diff`
(M2), `tests_only_diff` (M3), `branch_cleanup_changes` (M4). **None of them
compares outline declarations against references.** There is no receiving check.

The signal is therefore raised, downgraded to info on the strength of a deferral,
and dropped. Neither aspect reports a failure; the plan's own
`affected_files_exact_match` shows `status: warn` and the report shows nothing
actionable.

Adjacent, same aspect, same run: `affected_files_recall` **failed** because
deliverable 9 — "Prove every guard bites, and confirm no proposal was
implemented" — has a declaration heading with no parseable bullet. The one
deliverable whose subject is proving coverage is the one the coverage check could
not read.

## Finding B — the script-failure classifier cannot read the stderr it classifies on

`script-failure-analysis` reported 29 failures across 9 unique signatures. **25
of the 29 carry `subtype: argparse_other` with an EMPTY `stderr_excerpt`.** The
three documented signatures (`invalid choice:` → invented_subcommand; `the
following arguments are required:` → missing_required_flag; `unrecognized
arguments:` → invented_flag) matched only 4.

The classifier is not wrong — `argparse_other` is the honest residual bucket. But
it is classifying on an input that was not captured, so 86% of the plan's script
failures produce a seed lesson reading "Argparse rejection in {component} call"
with no cause and no remedy. The largest single cluster (11 rejections of
`manage-solution-outline get-deliverable`) is unactionable as recorded.

## The generalizable rule

A deferral is a claim that something else will do the work; it is only honest if
the target has a rule that fires. Before downgrading a finding to info on a
hand-off, name the specific check that receives it — and if none exists, keep the
severity. Likewise a classifier whose discriminating input is routinely absent
should report the input as missing (`stderr_unavailable`) rather than routing to
a residual bucket that reads like a classification.
