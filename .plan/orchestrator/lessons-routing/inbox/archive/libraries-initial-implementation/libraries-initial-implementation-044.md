envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:28Z

component=plan-marshall:phase-6-finalize
category=improvement
title=phase-6-finalize: set the merge-queue squash message instead of letting the PR body, with the review bot's release-notes block, become the commit message
source_lesson=2026-11-20-18-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-6-finalize: set the merge-queue squash message instead of letting the PR body, with the review bot's release-notes block, become the commit message

# Candidate lesson: the merge-queue squash message carries the whole PR body, including the review bot's release-notes block

- Source signal: plan plan-21-merge-worktrees-into-core (landing message plan-21-merge-worktrees-into-core-008, residue), corroborated by the orchestrator in `git log` of the merge commits `9e3cfb0` (PR #46) and `9bdc5ba` (PR #41): each commit message contains the full PR body, which ends with the CodeRabbit auto-generated release-notes block (four hits for "coderabbit" in the message of each commit).

## What happened

The run does not set the squash message, so the merge queue uses the pull request description. The description holds the plan's Summary, Intent, Changes and Test Plan sections, an unticked Test Plan checklist, a session link and the bot's `<!-- coderabbit-ai-generated -->` release-notes block with its HTML comment markers. All of it becomes the commit message on `main`, where it is permanent history.

## Why it matters

The history of `main` carries bot boilerplate and an unticked checklist as if they were the commit's own statement, and the commit subject is the only part written for history. The landing message of the plan names it as unset, so the gap is known but unowned.

## Candidate rule

When the finalize step creates or merges the pull request through a merge queue, it sets the squash commit message explicitly: the conventional-commit subject plus the Summary and Intent, without the Test Plan checklist and without the review bot's generated block (strip the block between its HTML comment markers). Owning component: `plan-marshall:phase-6-finalize` (create-pr and the merge step).
