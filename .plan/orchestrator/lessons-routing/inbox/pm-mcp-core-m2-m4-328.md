envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:34Z

component=plan-marshall:manage-execution-manifest
category=bug
confidence=high
source=plan-retrospective (execution-context-dispatch-audit, chat-history-analysis)

# Do not compose verify:module-tests when the root has no module-tests canonical

## Context

The execution manifest of plan-74-credential-store-choice lists `phase_5.verification_steps = [verify:quality-gate, verify:module-tests]`. In pm-mcp-core the whole-tree `module-tests` canonical does not resolve at the root module ("Command not found"; available: clean, quality-gate, verify, install, compile, package). Execute envelopes repeatedly explained the gap, one handed `verify:module-tests` back as owed, and the final sweep had to argue it away because the whole-tree verify covers it. The dispatch audit shows 5 unpaired `verify:*` execution rows in 5-execute.

## Root cause

Compose selects verification steps from the default rule without checking that each step's canonical command resolves for the plan's scope, so the manifest promises a step the architecture cannot run.

## Proposed action

At compose time, resolve each candidate verification step against the architecture; drop (or replace by the covering canonical, e.g. `verify`) a step that does not resolve, and log the substitution as a decision.

## Evidence

- aspect: execution-context-dispatch-audit — 5-execute unpaired_execution: verify:module-tests x4, verify:quality-gate x1
- execute hand-backs: "The whole-tree module-tests canonical does not resolve at the repository root"
