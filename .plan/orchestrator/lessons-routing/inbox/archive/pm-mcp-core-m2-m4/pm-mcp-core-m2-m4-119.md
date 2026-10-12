envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:31:59Z

# Pre-push quality gate selection is marketplace-shaped; this Maven repo needed the whole-tree gate resolved via architecture

Source: decision log 4ffcc8 (both manifest compose passes), plus an orchestrator observation for the finalize pre-push-quality-gate step (recorded `executed`, 19:36:51Z).

## What happened

Manifest compose logged:

> pre_push_quality_gate_inactive — kept pre-push-quality-gate on an unknown build verdict: plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed

The step was kept only because the verdict was unknown, not because the plan's footprint was evaluated. In finalize, the step derives its gate per bundle, which is the marketplace layout (`marketplace/bundles/{bundle}`). pm-mcp-core is a Maven multi-module repo with no bundles. The gate that actually applies, `verify -Ppre-commit` over the whole tree, had to be resolved through `architecture resolve` instead.

## Candidate rule / fix

- In the pre-push quality gate, take the bundle-scoped derivation only when the project is a marketplace. Otherwise resolve the canonical `quality-gate` command through the architecture API for the whole tree, or for the touched modules.
- Compose should evaluate the footprint after worktree materialization, or say that the verdict is deferred. Today an unresolvable footprint is the only reason the step stays active.

Owner: plan-marshall `phase-6-finalize` pre-push-quality-gate / `manage-execution-manifest` compose.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-006.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
