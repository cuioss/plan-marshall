envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:18Z

component=plan-marshall:execute-task
category=improvement
title=execute-task: add a scripted fails-at-base check instead of a manual diff restore
source_lesson=2026-11-19-06-007
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# execute-task: add a scripted fails-at-base check instead of a manual diff restore

# Candidate lesson: execute-task asks for a fails-at-base proof but offers no tool, so the agent rewrites and restores the worktree by hand

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-016), plan-retrospective (llm-to-script-opportunities, chat-history), confidence medium.

## What happened

To prove that each new test fails without its fix, the executing agent saved the production diff to `.plan/temp/`, restored the task's production files from HEAD, ran the test class and re-applied the diff, five times in one plan (the work log carries the `fails-at-base confirmed` lines for TASK-2, 4, 6, 8 and 11). Scratch files (three patch files, a commit message, extracted JGit sources) were left behind.

## Root cause

No deterministic tool for the check: the manual restore is repetitive, risky (a failed re-apply would lose the fix) and leaves scratch state.

## Candidate rule

Add an execute-task helper verb that runs a test selector against the base version of named production files in a scratch copy (a temporary stash or worktree), reports which tests went red and always restores the tree. The agent then only names the test and the files.
