envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:30Z

component=plan-marshall:phase-6-finalize
category=improvement
title=phase-6-finalize: escalate fix tasks that edit a module the outline declared read-only
source_lesson=2026-11-21-12-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-21

# phase-6-finalize: escalate fix tasks that edit a module the outline declared read-only

# Candidate lesson: fix tasks from the finalize loop-backs edit a module the outline declared read-only, with no scope prompt

- Source signal: plan-retrospective (request-result alignment, manifest decisions, artifact consistency), plan plan-08-store-drafts-save (inbox plan-08-store-drafts-save-024), PR #48. Component `plan-marshall:phase-6-finalize`, confidence high.

## What happened

The outline Summary said "with no git-core edit" and the module mapping marked `git-core` read-only. The review-fix tasks of the finalize loop-backs then changed the `git-core` public API: TASK-14 added `FetchInput.prune`, and TASK-20 made `JGitRepositoryOperations.MIRROR_FETCH_REF_SPECS` public. They also changed `RepositoryOperations.java`, two `git-core` tests and `doc/specification/git-core.adoc`. The leaves reported this as "decisions you may want to check", but no operator question was raised and `references.json` was not updated. The retrospective found 7 realized paths no deliverable declared (rule M6 `declared_vs_realized_set` failed); the landing message carries it only as residue.

## Why it matters

A public API change in a lower module is the kind of scope change an owner decides, and in an orchestrated epic the declared surface is what the disjointness gate reads for the next pairing. The crossing was visible only after the merge.

## Candidate rule

When the finalize triage creates a fix task, or an execute leaf is about to edit a file in a module the module mapping marks read-only, raise a prompt-required envelope (at least log a decision and add the paths to `references.json`). This matters most for a public API change in a lower module. Owning components: `plan-marshall:phase-6-finalize` (fix-task creation) and the execute leaf's target-file check.


## Recurrence in the next plan (plan-09-store-release-index-listeners, inbox plan-09-store-release-index-listeners-010 and -020)

- Source signal: orchestrator observation. TASK-010, a fix task for review finding b186a7 (file modes lost in a release tree), extended `TreeEdit` and `InCoreWriter` in `git-core`, wrote `InCoreWriterTest` and `doc/specification/git-core.adoc`, although the plan spec said `git-core` stays read-only. No step refused it: not the fix-task creation, not execute-task, not the per-deliverable commit. The orchestrator noticed it from the leaf report and asked the owner after the fact (the owner chose "keep, report it").
- Second plan in a row with the same crossing, although this plan's spec carried the read-only line as a Standing Constraint. Added rule: `execute-task` compares the changed paths with the read-only modules of the plan spec or outline before the commit and returns a prompt-required envelope on a hit; when a review finding can only be fixed inside a read-only module, the triage returns that decision to the operator instead of opening a fix task that crosses the boundary. Owning components: `plan-marshall:execute-task` and `plan-marshall:phase-6-finalize`.
