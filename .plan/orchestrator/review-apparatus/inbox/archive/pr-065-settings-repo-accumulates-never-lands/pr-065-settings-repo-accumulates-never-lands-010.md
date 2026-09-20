envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:59Z

component=plan-marshall:manage-references
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 459284 (2026-09-14T11:49:27Z)

# `manage-references get` called without its required `--field`

During the `create-pr` finalize step,
`plan-marshall:manage-references:manage-references get` was called without
`--field`; the executor answered
`Add the required flag(s) to ... get: ['field']`.

`get` is a field-level read verb — it has no whole-document form — so a bare
`get` cannot mean anything. The failure sits inside the PR-composition path,
where the surrounding workflow prose reads as "read the references" (a
document-level intent) while the script exposes only a field-level read.

## Candidate rule

Where a workflow instructs "read the references", the instruction must name the
field it wants, because the API has no document-level read. This is the same
prose-intent-versus-declared-surface generator as the manage-solution-outline and
manage-change-ledger clusters in this run: three of the nine script-failure
clusters share it.
