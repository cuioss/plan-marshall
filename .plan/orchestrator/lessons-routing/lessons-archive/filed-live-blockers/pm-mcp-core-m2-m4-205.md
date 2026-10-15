envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:48Z

# derive_gate_bundles returns zero bundles on a non-marketplace (Maven) project, leaving the per-bundle quality-gate arm empty

## What happened

In plan `diagram-generator` (pm-mcp-core, a Maven multi-module project with no `marketplace/bundles/` tree), `derive_gate_bundles` reported every changed path as unresolved and returned zero bundles. The per-bundle quality-gate arm therefore ran over nothing, and its green result says nothing about the change.

## Why it matters

A gate that finds an empty population and reports success is a silent zero: the operator cannot tell "gate ran and passed" from "gate had nothing to look at". On every non-marketplace project this arm is structurally empty.

## Fix direction

Either derive the gate population from the project's own module inventory (`architecture which-module`) when no marketplace bundles exist, or report the arm as not applicable (with the reason, e.g. `all paths unresolved: no marketplace bundles`) rather than as a passed gate over zero bundles.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-003.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
