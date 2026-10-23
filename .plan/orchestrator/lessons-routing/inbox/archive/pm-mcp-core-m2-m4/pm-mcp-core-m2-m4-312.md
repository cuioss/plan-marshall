envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:42Z

# Candidate lesson: Resolve verify:module-tests for Maven instead of inventing per-module step ids

Source: plan-retrospective (logging-gap-analysis + execution-context-dispatch-audit + chat-history-analysis), plan-69-unit-frontmatter-and-types
Component (suggested): plan-marshall:phase-5-execute (foreign bundle - route to plan-marshall lessons inbox)
Category (suggested): bug

## Context

The manifest declared phase-5 verification steps `verify:quality-gate` and `verify:module-tests`. At execute exit the leaf found that `module-tests` does not resolve for this Maven project ("only verify exists"), ran `verify -pl pm-core -am` and recorded it under a step id it made up, `verify:module-tests:pm-core`; pm-workflow resolved to the orchestrator tier (never timed) and was handed back. The execution log for 5-execute ends with that single invented row and no row for either manifest step, and four of nine execute dispatches ended `voluntary_checkpoint` on verify hand-backs. The orchestrator then had to judge by hand whether its earlier whole-tree runs on the same head covered the owed steps.

## Root cause

The manifest composer emits a canonical step (`module-tests`) the build-maven extension does not resolve, and execute has no defined fallback or record shape for it, so the leaf improvises an id and the steps the manifest names are never recorded.

## Proposed action

Either map `module-tests` to `verify -pl {module} -am` for Maven (or have the composer omit it when it does not resolve), and define the per-module record key the manifest expects; additionally let execute consult the build-freshness ledger to auto-record a pending verify step already covered by an orchestrator run on the same tree before handing it back.

## Evidence

- execute-exit return: "module-tests does not resolve in this project; only verify exists ... Recorded under step id verify:module-tests:pm-core. I made that id up"
- dispatch audit firing_comparison 5-execute: execution_rows 1, unpaired_execution `verify:module-tests:pm-core`
- dispatch boundaries 5-execute: 5 budget_yield, 4 voluntary_checkpoint (all verify hand-backs)
