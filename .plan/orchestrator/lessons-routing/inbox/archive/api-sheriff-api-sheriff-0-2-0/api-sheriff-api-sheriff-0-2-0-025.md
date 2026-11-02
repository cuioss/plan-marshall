envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T13:55:59Z

# Candidate lesson: Finalize sync-baseline rebase throws away every execute-phase build verdict (plan-marshall:phase-6-finalize sync-baseline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 008.


**Source**: finalize work log plus orchestrator observation. Low priority: the behaviour is correct, but it is expensive.
**Probable owner**: plan-marshall:phase-6-finalize (finalize-step-sync-baseline / worktree freshness ledger).

## What happened

Execute exit recorded a passing verify against the worktree sha: 5932 tests, 304 s, ledger-verified freshness. Finalize `sync-baseline` then rebased onto origin/main, which had moved by 10 upstream commits. That step's timestamps run from 10:16:36 to 11:59:43. The rebase changed the tree sha, so every execute-phase build verdict was invalidated, and the pre-push quality gate had to rebuild from scratch.

## Corrective rule (candidate)

When the upstream commits brought in by the rebase do not intersect the plan's build-relevant footprint or its dependency closure, the freshness ledger could carry the execute-exit verdict across the rebase. For example: no change to `pom.xml` and no change under a module the plan touches. A rebuild should be owed only when they do intersect. Separately, the cause of the roughly 1h43m wall time inside sync-baseline should be checked. It may be operator wait rather than tooling time.
