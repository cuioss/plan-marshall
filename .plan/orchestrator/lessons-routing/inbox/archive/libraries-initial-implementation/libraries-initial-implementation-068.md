envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:43Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: a deliverable that says "every file of kind X" runs the content sweep while outlining and lists the result with exclusions
source_lesson=2026-11-24-07-006
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-24

# phase-3-outline: a deliverable that says "every file of kind X" runs the content sweep while outlining and lists the result with exclusions

Source: Q-Gate finding 5f8635, phase 3-outline, scope_criterion_validator, under_coverage, severity warning, resolution taken_into_account.

Observation: D5 said "every other git-core test with a negative absence assertion over a generated letters-only value is migrated in the same change", but its affected files named only four tests. A content sweep found six more candidates (RemotePolicyTest, RefusingFSTest, JGitCacheRepositoryTest, GitNotesTest, InCoreWriterTest, worktrees/JGitWorktreeOperationsTest). An unenumerated "every X" fails the declared-set closure at plan time.

Resolution in run: D5 states the derivation rule and enumerates the six candidates as write-replace, with GitIdentityTest and WorktreeOperationsRecordsTest excluded with reasons.

Candidate rule: a deliverable that says "every file of kind X" runs the content sweep while outlining and lists the result (plus exclusions with reasons); the quantifier alone is not a file set.

Context: plan plan-20-leftover-fixes-2, PR 69 (merged f7eda4e).


Source: inbox plan-20-leftover-fixes-2-004 (Q-Gate finding 5f8635).
