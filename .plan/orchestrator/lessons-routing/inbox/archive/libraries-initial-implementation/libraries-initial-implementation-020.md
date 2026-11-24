envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:13Z

component=plan-marshall:manage-architecture
category=improvement
title=Bootstrap unmeasured build tiers so leaves can run per-deliverable builds
source_lesson=2026-11-18-18-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Bootstrap unmeasured build tiers so leaves can run per-deliverable builds

# Candidate lesson: a command that was never measured is pinned to the orchestrator tier, so a new module's focused build is never measured from a leaf

- Source signal: plan-retrospective of plan git-worktrees-import (inbox plan-03-git-worktrees-import-017), component `plan-marshall:manage-architecture`, confidence high.

## What happened

In phase 5 the focused per-deliverable builds for the new module (`compile` and `module-tests`, that is `test -pl git-worktrees -am`) resolved as `execution_tier: orchestrator` with the reason "Unmeasured; orchestrator-tier until first measurement". The execute leaves skipped them for deliverables 1, 2 and 3 and relied on the whole-tree `verify -Ppre-commit`. Envelope 2 ended with a `verification_handback` for `verify:module-tests` that the orchestrator then ran itself.

## Root cause

A command with no measurement is pinned to the orchestrator tier, and a leaf may not run an orchestrator-tier command, so the first measurement of a new module's focused build can never come from inside a leaf.

## Candidate rule

Give an unmeasured command a bounded per-task default (for example the resolved Bash ceiling) on its first run, or record the measurement from the orchestrator's hand-back run so the next leaf resolves it per task.

## Evidence

- log_analysis: the 5-execute dispatch boundaries include 1 verification_handback.
- execution_context_dispatch_audit: unpaired execution rows `verify:module-tests` x2.
- chat_history_analysis: both envelope-1 and envelope-2 leaves report the focused builds skipped as orchestrator-tier.


## Recurrence for the next new module (plan-07-store-module-registry-spi, inbox plan-07-store-module-registry-spi-010)

- Source signal: plan-retrospective, component `plan-marshall:manage-architecture`. PLAN-07 created the reactor module `git-store`; every module-scoped build for it (`compile`, module-tests, `verify` and `verify -Ppre-commit` with `-pl git-store -am`) resolved to `execution_tier: orchestrator` ("Unmeasured; orchestrator-tier until first measurement") for the plan's whole life. Two of the six execute dispatches ended in `verification_handback` (TASK-8 and TASK-15) and execute was re-entered three times, while the whole-tree `verify -Ppre-commit` ran inline and green in the same leaves (847 and 883 tests).
- Cost: 4,695,078 tokens (a floor) against the 2.5M error anchor for a multi_module feature plan; 5-execute 1,782,190 dominant; `maven` calls were 31, 39.7 percent of script time.

Same root cause, second module created in this epic (`git-worktrees` was the first). New point: the tier is keyed on a per-module measurement that only a module-scoped run records, and an inline whole-tree run that already covers the module never seeds one. Corrective rule as above, with one addition: record the module-scoped duration from the first successful whole-tree run that builds the module, or let the resolver treat a whole-tree inline run that already passed on the same tree as satisfying the owed module-scoped step.


## Recurrence in a third module (plan-08-store-drafts-save, inbox plan-08-store-drafts-save-023)

- Source signal: plan-retrospective (chat-history, logging-gap and dispatch-audit aspects), component `plan-marshall:phase-5-execute`. The end-of-phase step `verify:module-tests` for `git-store` (`verify -pl git-store -am`) resolved to the orchestrator tier twice because it had never been measured. Envelopes 3 and 4 both returned `verification_handback` although whole-reactor `verify -Ppre-commit` (and in envelope 3 a full `verify`) had already passed on the exact same tree: two hand-backs, two extra orchestrator builds and two extra re-entry dispatches (the 5-execute ledger shows 2 `verification_handback` rows and 4 closes). Afterwards the freshness check still reported `scope_cross_check: undetermined` (`required_coverage_unknown`).

Same root cause (`git-store` is the second module of this epic to hit it after `git-worktrees`, and the same module hit it in PLAN-07). Corrective rule as above, with one further point: when a whole-reactor build of the same goal, or a superset, passed on the current tree hash, record the module-tests step as satisfied instead of handing it back, and record the covered modules on the ledger row so the freshness scope check can decide.
