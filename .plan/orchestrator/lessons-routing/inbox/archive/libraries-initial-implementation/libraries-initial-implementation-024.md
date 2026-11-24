envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:15Z

component=plan-marshall:phase-6-finalize
category=improvement
title=ci-verify: classify a Maven Central resolution failure as transient and re-run the job once
source_lesson=2026-11-19-06-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-19

# ci-verify: classify a Maven Central resolution failure as transient and re-run the job once

# Candidate lesson: ci-verify has no classification for a transient Maven Central resolution failure

- Source signal: plan git-worktrees-hardening (inbox plan-19-git-worktrees-hardening-009), orchestrator-reported fact from the PR #31 run (ci-verify). Possibly knowledge rather than a defect.

## What happened

The `build/sonar-build` job of PR #31 failed once because a dependency could not be resolved from Maven Central. A re-run passed with no change; the ci-verify step completed `done`.

## Candidate rule

When ci-verify sees a failure whose log names an artifact-resolution or network error against Maven Central, and the same job passed on the other matrix entries, classify it as transient and re-run the job once before treating it as a code failure or looping back. Decide on pickup whether this belongs in the ci-verify classification or as a project hint.
