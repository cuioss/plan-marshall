---
name: pm-dev-python-arch-gate-python
description: "Use when running or interpreting the Python arch-gate — the import-linter-based architectural-fitness-function check that runs as a per-deliverable read-only structural-boundary gate and emits arch-constraint findings. A thin pointer to the central arch-gate model in plan-marshall:manage-architecture; carries only the Python/import-linter binding."
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Python arch-gate (import-linter)

**REFERENCE MODE**: This skill provides reference material for the Python domain's `arch-gate` binding. It is a **thin pointer** — the structural concept, the read-only contract, the execution model, and the findings → triage → lesson feedback loop are owned by the central standard and MUST NOT be duplicated here.

The single authoritative model for `arch-gate` lives in [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) in `plan-marshall:manage-architecture`. Read that document for what an architectural fitness function is, the read-only structural-boundary-gate contract, the single per-deliverable execution model, resolution/execution path, and the lesson lifecycle. This skill carries only the Python-specific binding.

## Enforcement

**Execution mode**: Reference library; load for context when running or interpreting the Python arch-gate. Never execute this document's content as a workflow.

**Prohibited actions:**
- Do not duplicate the central `arch-gate-fitness-functions.md` model here — this skill is a thin pointer
- Do not mutate source from the arch-gate run — it is read-only with respect to both source and the lessons corpus
- Do not conflate the whole-graph import contract with per-file ruff — import-linter asserts a property of the import graph, not per-file style

**Constraints:**
- The Python arch-gate tool is import-linter; the descriptor the extension declares is `{'tool': 'import-linter'}`
- arch-gate runs as a per-deliverable read-only verify-step resolved through `architecture resolve --command arch-gate`
- A structural-boundary violation is typed as an `arch-constraint` finding, never a generic `lint-issue`

## Python binding

| Aspect | Python value |
|--------|--------------|
| Native tool | import-linter |
| Rule surface | Whole-graph directional / layered import contracts (a `.importlinter` contract set), distinct from per-file ruff |
| Extension descriptor | `provides_arch_gate()` returns `{'tool': 'import-linter'}` |
| Verify-step | `default:verify:arch-gate`, appended to `phase-5-execute.verification_steps` by `skill-domains configure` when the python domain is configured |
| Finding type | `arch-constraint` (one finding per structural-boundary violation, carrying the violated contract's identity) |

Running import-linter as its own dedicated invocation — rather than folding its checks into per-file ruff — is what lets a directional/layered import violation surface as an `arch-constraint` finding instead of a generic lint issue. import-linter violations route to [`pm-dev-python:ext-triage-python`](../ext-triage-python/SKILL.md) for the per-finding disposition (FIX / SUPPRESS / ACCEPT); a violation that recurs across runs feeds the `arch-constraint` lesson type (rule-identity dedup, retire-on-quiet / reinforce-on-recurrence).

## Related

- [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) — the central, authoritative arch-gate model (single source of truth)
- [`extension-contract.md` § provides_arch_gate](../../../plan-marshall/skills/extension-api/standards/extension-contract.md) — the hook contract the Python extension implements
- [`pm-dev-python:ext-triage-python`](../ext-triage-python/SKILL.md) — Python triage, including `arch-constraint` finding disposition
