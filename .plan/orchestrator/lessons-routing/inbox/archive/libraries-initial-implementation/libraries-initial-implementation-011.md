envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:06Z

component=plan-marshall:manage-findings
category=improvement
title=manage-findings list rejects --limit; add a limit or count-only mode or fix the docs
source_lesson=2026-11-18-13-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# manage-findings list rejects --limit; add a limit or count-only mode or fix the docs

# Candidate lesson: `manage-findings list --limit` is rejected by argparse in automatic-review and verification-feedback

- Source signal: script-failure cluster `plan-marshall:manage-findings:manage-findings` (exit 2, argparse_rejection), plan git-core-import, twice (inbox git-core-import-003).

## What happened

Two dispatches running different workflows called `manage-findings list ... --limit N`. `list` declares no `--limit` (it accepts any-checkout, author, bot-kind, component, file-pattern, include-qgate, kind, plan-id, preference-admissible, promoted, resolution, type). The call failed before the script body ran and the leaf retried without the flag. With 73 findings the unlimited payload was 235 KB of TOON.

## Candidate rule

- Check `automatic-review/SKILL.md`, `plan-marshall/workflow/verification-feedback.md` and the triage docs they load for a `list` example carrying `--limit`, and correct it; the flag was probably carried over from `manage-logging read`.
- Or give `manage-findings list` a real `--limit` / count-only mode, since a full-store payload is large enough to spill to disk in a leaf. Related: lesson 2026-11-18-07-002 (invented verb on the same script).


## Recurrence in a later plan (plan-05-git-core-merge-read-notes, inbox plan-05-git-core-merge-read-notes-008)

- Source signal: script failure cluster `plan-marshall:manage-findings:manage-findings` (3 `script_failure` rows, one hash 6ef3b9): `--limit` is not declared for `manage-findings list`; its flags are `any-checkout, author, bot-kind, component, file-pattern, include-qgate, kind, plan-id, preference-admissible, promoted, resolution, type`.
- The same rejection was logged three times in 6-finalize, by the same caller each time (2026-11-19T18:06:57Z after sonar-roundtrip, 18:51:27Z during automatic-review iteration 2, 19:26:52Z before the lessons-capture dispatch, most likely the dispatcher's Signal Gate query for remediated pr-comments). All three callers recovered by retrying without the flag.

Same root cause and same corrective rule: the repeated hash points at one shared prompt or doc template that carries `list ... --limit N` for a count-only query. Either add a declared `--limit` (or a count-only verb; `filtered_count` is all these callers need) or remove it from the workflow text.


## Recurrence in a third plan (plan-07-store-module-registry-spi, inbox plan-07-store-module-registry-spi-005)

- Source signal: script_failure marker (work log, 2026-11-20T11:44:57Z, automatic-review round 2): the automatic-review leaf called `manage-findings list ... --limit N`; the declared flags are the same twelve as above.
- New figure: the full `list` output for this plan's 15 findings is 82 KB, because the `raw_input` and `body` columns are included. That is the likely reason a limit was reached for.

Same root cause and same corrective rule. Add to the options: a projection (for example a column selection) on `list`, which serves the same callers as `--limit` and also keeps a leaf's context small.


## Related rejections on the same script in a fourth plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-005)

- Source signal: script-failure cluster `plan-marshall:manage-findings:manage-findings`, two argparse rejections (exit 2). (1) 3-outline re-entry (2026-11-20T15:31:29Z, hash c3533b): `manage-findings qgate query`, a verb that is not registered (the registered `qgate` verbs are add, clear, list, resolve, resolve-by-rule and resolve-evidenced), the verb-paraphrase signature: a likely-sounding verb taken from the prose, not from the script's surface. (2) 6-finalize lessons-capture (17:45:06Z, hash 771256): `qgate list --plan-id ...` without `--phase`, which `qgate list` requires; it retried with `--phase 3-outline`.

Same class as above (a call the declared surface rejects), on a different verb. Corrective rule: take the verb and flag set from the script's canonical-invocation block or its `--help`, never from workflow prose. For the owning component: let `qgate list` omit `--phase` to list every phase, because lessons-capture reads Q-Gate findings across 2-refine through 6-finalize and today needs five calls for it.
