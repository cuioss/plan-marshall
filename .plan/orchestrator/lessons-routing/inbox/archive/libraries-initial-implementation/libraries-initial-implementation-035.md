envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:23Z

component=plan-marshall:workflow-integration-git
category=bug
title=git-workflow commit: an empty index is reported as FETCH_FAILURE instead of nothing_staged
source_lesson=2026-11-19-19-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# git-workflow commit: an empty index is reported as FETCH_FAILURE instead of nothing_staged

# Candidate lesson: `git-workflow commit` with nothing staged reports FETCH_FAILURE instead of naming the empty index

- Source signal: plan plan-05-git-core-merge-read-notes (inbox plan-05-git-core-merge-read-notes-012), retrospective chat-history (envelope 2 hand-back) and LLM-to-script opportunities, component `plan-marshall:workflow-integration-git` (`git-workflow commit`).

## What happened

In 5-execute envelope 2 the deliverable-5 commit first failed with "nothing staged", but the verb returned the error code `FETCH_FAILURE`. The leaf staged the six task files with `git add` by hand and the retry succeeded (commit `a621adf`). This is separate from the finalize commit-guard refusal (`no_sanction`, lesson `2026-11-18-13-002`).

## Root cause

The commit verb maps an empty-index outcome onto an unrelated error code, and it does not stage the task's declared changed paths itself, so every caller has to know to run `git add` first.

## Candidate rule

Return a dedicated outcome such as `nothing_staged` that names the unstaged paths, and optionally accept the task's changed-path list and stage exactly those paths before committing, so the leaf does not have to stage files by hand.
