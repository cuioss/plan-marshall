envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:05Z

component=plan-marshall:workflow-integration-git
category=bug
title=Finalize commit gate refuses inline fixes with no_sanction; --step needs the bare manifest id
source_lesson=2026-11-18-13-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Finalize commit gate refuses inline fixes with no_sanction; --step needs the bare manifest id

# Candidate lesson: the finalize commit gate refuses inline fixes with no_sanction, and --step needs the bare manifest id

- Source signal: script-failure cluster `plan-marshall:workflow-integration-git:git-workflow` (reason `no_sanction`), plans git-core-import (inbox git-core-import-002) and plan-18-leftover-fixes (inbox plan-18-leftover-fixes-001). Two plans, same refusal.

## What happened

In 6-finalize, source edits made inline while remediating review-bot findings were committed through `git-workflow commit`. The source-tree gate refused them: no `--step` from the composed manifest, no open loop-back fix task and no review-rubric inline-correction record. Passing `--step "plan-marshall:automatic-review"` was refused again, because the gate compares against manifest step ids stored bare (`automatic-review`), without the bundle prefix that the work log and the step's frontmatter show. The bare form succeeded.

## Candidate rule

- Before a finalize triage edits source inline, establish the sanction the gate will ask for (open a fix task, record the rubric entry, or pass `--step` with the BARE manifest step id, never `bundle:skill`).
- Tooling fix: normalise `bundle:step` to the bare id, or name the accepted ids in the refusal payload. The triage workflow should state the sanction requirement where inline edits are allowed.


## Recurrence in a later plan (plan-05-git-core-merge-read-notes, inbox plan-05-git-core-merge-read-notes-001)

- Source signal: script failure cluster `plan-marshall:workflow-integration-git:git-workflow` (2 refusals, `reason: no_sanction`).
- In the second review round on PR #37 the unified triage applied the coderabbit and Sonar fixes inline in the worktree (five files) and then tried to commit them. `git-workflow` refused twice (2026-11-19T19:05:39Z with `step: null`, 19:05:49Z with `step: "plan-marshall:automatic-review"`): "no step id from the composed phase-6 manifest, no open loop-back fix task and no review-rubric section-6 inline-correction record". The bundle-prefixed `plan-marshall:automatic-review` was not accepted although `automatic-review` is a composed phase-6 step (the manifest lists it without the prefix).
- The triage then opened a fix task (TASK-014) only so it could commit the edits that were already applied, which forced a full loop-back to 5-execute and a repeat of simplify, the pre-push gate, ci-verify, sonar and automatic-review. In round 1 the inline edits did commit, because fix tasks were open at the same moment.

Same root cause and same corrective rule: record the sanction first (the section-6 inline-correction record, or the unprefixed manifest step id) or open the fix task first and apply the edits inside it; and check whether `--step` should accept the bundle-prefixed notation. Second plan to pay a loop-back for it.
