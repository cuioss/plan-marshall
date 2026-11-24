envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:00Z

component=plan-marshall:manage-findings
category=improvement
title=manage-findings: the Q-Gate read path invites an invented verb (qgate query) - point to qgate list or add an alias
source_lesson=2026-11-18-07-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# manage-findings: the Q-Gate read path invites an invented verb (qgate query) - point to qgate list or add an alias

# Candidate lesson: invented verb `manage-findings qgate query` (argparse rejection, twice)

- Source signal: script-failure cluster, notation plan-marshall:manage-findings:manage-findings (by_class: script_failure 2, failed 0, no_progress_reclassification 0)
- Work-log entries: hash c3533b at 2026-11-17T19:43:02Z and 2026-11-17T19:45:39Z, both during 3-outline re-entry after Q-Gate finding 9fe2d8
- Detail: exit_code=2, failure_kind=argparse_rejection. "`query` is not a registered verb for `plan-marshall:manage-findings:manage-findings qgate`: ['add', 'clear', 'list', 'resolve', 'resolve-by-rule', 'resolve-evidenced']"

## What happened

Within one plan, an agent called `manage-findings qgate query` two times, about 2.5 minutes apart. That verb does not exist. The correct read verb is `qgate list --plan-id P --phase PH [--resolution R]`. The first rejection did not stop the second attempt.

## Candidate rule

This is the "verb paraphrase" form of the invented-subcommand error, on the Q-Gate read path of phase-3-outline / q-gate re-entry. Possible fixes are a canonical-invocation reference to `qgate list` at the point where phase-3-outline reads pending Q-Gate findings, or a `query` alias. The run also had 3 verification_handback rows, which are not lesson-bearing and are left out here.



## Recurrence in a later plan (git-worktrees-hardening, inbox plan-19-git-worktrees-hardening-005)

- Source signal: script_failure cluster `plan-marshall:manage-findings:manage-findings` (phase 3-outline re-dispatch, exit 2, argparse rejection): `query` is not a registered verb for `qgate`; registered: `add, clear, list, resolve, resolve-by-rule, resolve-evidenced`.
- The outline agent called `qgate query` instead of `qgate list`: the same invented verb as above, on a different plan.

Same root cause and same corrective rule: quote the canonical `qgate list --plan-id ... --phase ...` invocation next to the read in the phase-3-outline / q-gate prose, or add the alias.


## Recurrence in a third plan (git-core-incore-write-cas, inbox git-core-incore-write-cas-010)

- Source signal: script_failure cluster `plan-marshall:manage-findings:manage-findings` (work-log line c3533b, 2026-11-18T15:03:00Z, in the orchestrator context after the 3-outline q-gate-validation dispatch returned, exit 2, argparse rejection): `query` is not a registered verb for `qgate`; registered: `add, clear, list, resolve, resolve-by-rule, resolve-evidenced`.
- The orchestrator-side reader of the Q-Gate findings called `qgate query` instead of `qgate list`: the same invented verb as above, now in the orchestrator step rather than in the outline agent, and on a third plan.

Same root cause and same corrective rule: quote `qgate list --plan-id ... --phase ...` verbatim from the manage-findings canonical invocations at every point that reads Q-Gate findings (the orchestrator step after q-gate-validation included), or add the alias.


## Recurrence in a fourth plan (implement-plan-06-build-guards, inbox implement-plan-06-build-guards-011)

- Source signal: script-failure cluster `plan-marshall:manage-findings:manage-findings` (one counted row, 2026-11-19T21:22:13Z, phase 3-outline re-entry): `qgate list` rejected with exit 2, `argparse_rejection`, missing required `--phase` (the scan's known recurrence signature 5, missing `--phase` on phase-scoped finding verbs).

The corrected verb is now called, but without its required scope flag: the Q-Gate read path keeps producing wrong invocations (`qgate query`, then `qgate list` without `--phase`). Same corrective rule: quote the full `qgate list --plan-id ... --phase ...` form from the canonical invocations at every point that reads Q-Gate findings.


## Recurrence in a fifth plan (plan-08-store-drafts-save, inbox plan-08-store-drafts-save-001)

- Source signal: script-failure cluster `plan-marshall:manage-findings:manage-findings` (3 `script_failure` rows, `argparse_rejection`, two from the phase-3-outline leaf at 2026-11-20T18:40:30Z and 18:53:48Z): `query` is not a registered verb of `manage-findings qgate`; the registered verbs are add, clear, list, resolve, resolve-by-rule, resolve-evidenced.

The leaf reached for `qgate query` on two separate dispatches and recovered both times, so the invented verb comes from something the leaf reads, not from a slip. Same corrective rule: quote the full `qgate list --plan-id ... --phase ...` form from the canonical invocations at every point that reads Q-Gate findings, or register `query` as a read alias.


## Recurrence in a sixth plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-003)

- Source signal: script-failure cluster `plan-marshall:manage-findings:manage-findings` (2 `script_failure` rows, `argparse_rejection`): 2026-11-21T13:43:12Z `qgate query` again (`query` is not a registered verb; the registered ones are add, clear, list, resolve, resolve-by-rule, resolve-evidenced), and 2026-11-21T16:31:28Z a `manage-findings list` call during the verification-feedback dispatch whose rejected flag is not recorded.
- Secondary observation: the `[ERROR] script_failure` marker cuts the argparse usage text off before the rejected flag, so the second failure is undiagnosable afterwards. The marker should record the `rejected:` flag name before the usage text.

Same corrective rule: quote the full `qgate list --plan-id ... --phase ...` form from the canonical invocations at every point that reads Q-Gate findings.


## Recurrence in a later plan (plan-20-leftover-fixes-2, inbox plan-20-leftover-fixes-2-008)

The invented `manage-findings qgate query` was called twice within one minute (2026-11-23T16:50:34Z and 16:51:28Z, around the outline Q-Gate re-entry); the first rejection did not correct the caller. Correct form: `manage-findings qgate list --plan-id P --phase PHASE [--resolution R]`. Registered verbs: add, clear, list, resolve, resolve-by-rule, resolve-evidenced.
