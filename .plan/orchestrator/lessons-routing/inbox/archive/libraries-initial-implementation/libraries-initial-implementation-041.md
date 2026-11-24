envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:27Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: draw each deliverable's verification command from the project's canonical build list, not from a convenient goal
source_lesson=2026-11-20-14-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-3-outline: draw each deliverable's verification command from the project's canonical build list, not from a convenient goal

# Candidate lesson: the outline's per-deliverable verification used a build goal outside the project's canonical list

- Source signal: plan plan-07-store-module-registry-spi (inbox plan-07-store-module-registry-spi-001), Q-Gate finding ba5c90 (phase 3-outline, severity warning, resolution `taken_into_account`).

## What happened

The first outline draft had deliverables 1 to 5 verify with `maven run --command-args "test"`. The project's CLAUDE.md (Build Commands) names exactly four canonical builds, `compile`, `verify -Ppre-commit`, `verify` and `verify -Pcoverage`, and says never to hard-code other invocations. The Q-Gate caught it and the operator chose `verify` for every deliverable.

## Candidate rule

When the outline writes per-deliverable verification commands, draw them only from the project's canonical build command list (CLAUDE.md, or the architecture-resolved commands), never from a convenient goal such as `test`. A check at the outline's own self-check step (before the Q-Gate) would catch the class: every verification command is a member of the canonical list.


## Recurrence in a later plan (plan-11-store-anchoring-signed, inbox plan-11-store-anchoring-signed-005)

Q-Gate finding f5596f (phase 3-outline): deliverables 1, 2 and 3 named `maven run --command-args 'test -pl git-store -am'` as their verification command, which is not one of the canonical commands CLAUDE.md allows (compile, verify -Ppre-commit, verify, verify -Pcoverage). It was accepted without a change because the PR was gated by `build / conclusion`. If a module-scoped run is wanted for speed, the outline states why it is an acceptable variant; otherwise the Q-Gate flags it on every plan.
