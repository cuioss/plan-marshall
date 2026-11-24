envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:37Z

component=plan-marshall:build-maven
category=bug
title=give the learned maven build timeout headroom above the observed run time
source_lesson=2026-11-23-12-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# give the learned maven build timeout headroom above the observed run time

# Candidate lesson: the learned maven build timeout sits at the observed run time with no headroom

- Source signal: plan-retrospective of plan-23-forms-hardening (inbox plan-23-forms-hardening-012; log_analysis and chat_history_analysis aspects).

## What happened

The wrapper's learned build timeouts were 305 to 315 s while the whole-tree `verify -Ppre-commit` runs took up to 316 s (slowest logged calls 316,360 ms, 306,620 ms, 277,500 ms; 39 calls at or over the 30 s ceiling). The deliverable-6 gate passed all 1,450 tests and was then stopped by the wrapper's 315 s limit during the javadoc jar step; the leaf had to re-run with `-DskipTests` to cover lint and javadoc.

## Candidate rule

Apply a multiplicative headroom (for example 1.5x, floored at the 600 s Bash ceiling) to the learned build timeout, and never learn a limit below the longest successful run seen for the same command. Owning component: `plan-marshall:build-maven`.
