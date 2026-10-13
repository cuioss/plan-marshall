envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T08:39:56Z

# Flag contract-tightening plans as blocking their verified consumers

Component: `plan-marshall:plan-orchestrator` · Category: improvement · Source: plan-retrospective of `static-verifier-rule-gaps-completion`

## Context

The PLAN-54 spec listed PLAN-13 (`workflow-engine`) as "Adjacent to: ... runs verified units and does not wait". The init overlap check compared only shared files (`doc/plans/README.adoc`, the spec file) and found nothing to worry about. #45 landed while PLAN-54 ran. After the finalize rebase, the stricter verifier refused 39 of the engine's test units (Rule 6 `stepped_out` targets, the `change` kind removed from the production defaults), and `WorkflowEngine` stopped compiling against the new `VerificationResult` constructor. Fixing PLAN-13's test fixtures became a loop-back fix task inside PLAN-54 and needed two more operator decisions.

## Root cause

Overlap is judged by shared files only. A plan that tightens a contract (a verifier, a schema, a registry default) breaks every consumer that passes its own fixtures through that contract, even when no file is shared. "Runs verified units" was named in the spec and still read as "adjacent".

## Proposed action

In spec authoring and in the init overlap check, treat "consumes the output or the checks of the contract this plan tightens" as a sequencing dependency, not adjacency. Either order the consumer after the tightening plan, or put the consumer's fixture conformance into the tightening plan's declared scope from the start. This complements inbox 008, which records the breakage itself.

## Evidence

- aspect: chat-history-analysis — operator decision at the pre-push loop-back ("Fix the fixtures"), then TASK-12 BLOCKED on shouldFaultOnUndeclaredOutcome
- aspect: request-result-alignment — 6 workflow.engine files outside the declared surface
- aspect: invariant-summary — main_sha drift 4-plan to 5-execute; 3 upstream commits absorbed at sync-baseline

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-rule-gaps-completion-013.md` from plan static-verifier-rule-gaps-completion (PLAN-54, #48; Claude Code)
