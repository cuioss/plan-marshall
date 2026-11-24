envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:18Z

component=plan-marshall:execute-task
category=improvement
title=execute-task: the test-identifier diff helper reads only pytest output, extend it to Surefire
source_lesson=2026-11-19-06-008
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# execute-task: the test-identifier diff helper reads only pytest output, extend it to Surefire

# Candidate lesson: the test-identifier diff helper of execute-task reads only pytest output

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-017), plan-retrospective (chat-history), confidence medium.

## What happened

execute-task compares the test identifiers of a build before and after a test task to confirm the new tests ran. On this Maven plan the agent skipped it ("the identifier-diff helper only reads pytest output") and inferred new-test presence from total counts (522 -> 529 -> 534 -> 537).

## Root cause

For Maven/JUnit projects the check silently degrades to a count comparison, which cannot tell a new test from a renamed or removed one.

## Candidate rule

Teach the helper to read Surefire results (`target/surefire-reports/TEST-*.xml` testcase names, or the build log), or have execute-task state explicitly that the check is pytest-only and record the skip as a coverage gap rather than leave it to the agent.
