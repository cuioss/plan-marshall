envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:49Z

# Candidate lesson: a deliverable whose write targets live in a sibling repository was mapped to a module of this repository

- Source: Q-Gate finding a4937a (phase 3-outline, severity warning, resolution taken_into_account)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Candidate component: plan-marshall:phase-3-outline

## Observation

Deliverable 2 was mapped to module `documentation` of pm-mcp-core, but both of its write targets (`../plan-marshall-documentation/doc/roadmap/migration-inventory.csv`, `../plan-marshall-documentation/doc/roadmap.adoc`) lie in the sibling repository plan-marshall-documentation. `architecture which-module` resolved the path to `module: null` (3 attributors ran). The deliverable's commit, push and pull request happen in another repository. The chain-tail commit, the per-deliverable module build and the declared footprint of this plan all work on the pm-mcp-core worktree. The Risks section named the classifier risk but left the execution shape open ("or D2 becomes a manual step").

## Resolution in this run

D2 became an explicit mixed step with module `none` and no affected files in this repository's footprint (the survey/mutate pair both declare none here). Each of its eight steps states the repository it runs in (plan-marshall-documentation, plan-marshall read-only, this plan's decision log, operator merge). The pin, counts and PR link reach D6 through one D2 decision-log entry, and the operator merges the documentation PR.

## Possible rule (for orchestrator judgement)

When `which-module` returns `module: null` for an affected file because it lies outside the repository, the outline should not take a module of this repository. It should declare the cross-repository deliverable as an operator or mixed step with module none, state the repository each step runs in, and carry its outputs to later deliverables through the decision log. The outline workflow could check for this mismatch.
