---
name: q-gate-validation
description: Shared Q-Gate verification workflow — checks solution outline deliverables against request intent and assessments for false positives, missing coverage, and scope drift. Dispatched from phase-3 outline-time Q-Gate (Complex Track Step 11) and phase-4 plan-time Q-Gate (Step 9b) via the cross.q-gate-validation role key.
user-invocable: false
---

# Q-Gate Validation

Single home for the cross-phase Q-Gate verification workflow. The substance lives in [`standards/workflow.md`](standards/workflow.md); this SKILL.md is the addressable handle for the dispatcher's `Read` of the workflow notation.

## Usage

Dispatched as `cross.q-gate-validation` (role key) under `plan-marshall:execution-context-{level}`:

```toon
name:        q-gate-validation
plan_id:     {plan_id}
skills[6]:
- plan-marshall:manage-solution-outline
- plan-marshall:manage-findings
- plan-marshall:manage-plan-documents
- plan-marshall:manage-status
- plan-marshall:manage-architecture
- plan-marshall:manage-logging
workflow:    plan-marshall:q-gate-validation/standards/workflow.md
WORKTREE:    {repo-relative-path}
```

The level is resolved from `manage-config models read --role cross.q-gate-validation`.

## Workflow

See [`standards/workflow.md`](standards/workflow.md) for the full step list, deliverable verification criteria, missing-coverage check, findings recording, and return-TOON contract.

## Call sites

- `phase-3-outline` Complex Track Step 11 — outline-time Q-Gate validating the freshly-authored solution outline against the request and per-file assessments.
- `phase-4-plan` Step 9b — plan-time Q-Gate validating that planned tasks cover the outline's deliverables before phase-5 execution begins.

Each call site passes a different `activation_context` / `validators` runtime parameter to scope which subsections of the workflow apply.
