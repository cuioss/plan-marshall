---
name: arch-gate-js
description: "Use when running or interpreting the JavaScript arch-gate — the dependency-cruiser-based architectural-fitness-function check that runs as a per-deliverable read-only structural-boundary gate and emits arch-constraint findings. A thin pointer to the central arch-gate model in plan-marshall:manage-architecture; carries only the JavaScript/dependency-cruiser binding."
user-invocable: false
mode: knowledge
---

# JavaScript arch-gate (dependency-cruiser)

**REFERENCE MODE**: This skill provides reference material for the JavaScript domain's `arch-gate` binding. It is a **thin pointer** — the structural concept, the read-only contract, the execution model, and the findings → triage → lesson feedback loop are owned by the central standard and MUST NOT be duplicated here.

The single authoritative model for `arch-gate` lives in [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) in `plan-marshall:manage-architecture`. Read that document for what an architectural fitness function is, the read-only structural-boundary-gate contract, the single per-deliverable execution model, resolution/execution path, and the lesson lifecycle. This skill carries only the JavaScript-specific binding.

## Enforcement

**Execution mode**: Reference library; load for context when running or interpreting the JavaScript arch-gate. Never execute this document's content as a workflow.

**Prohibited actions:**
- Do not duplicate the central `arch-gate-fitness-functions.md` model here — this skill is a thin pointer
- Do not mutate source from the arch-gate run — it is read-only with respect to both source and the lessons corpus
- Do not conflate module-boundary rules with per-file ESLint style — dependency-cruiser asserts a property of the module graph

**Constraints:**
- The JavaScript arch-gate tool is dependency-cruiser; the descriptor the extension declares is `{'tool': 'dependency-cruiser'}`
- arch-gate runs as a per-deliverable read-only verify-step resolved through `architecture resolve --command arch-gate`
- A structural-boundary violation is typed as an `arch-constraint` finding, never a generic `lint-issue`

## JavaScript binding

| Aspect | JavaScript value |
|--------|------------------|
| Native tool | dependency-cruiser |
| Rule surface | Module-boundary / forbidden-dependency rules (ESLint-boundaries class), a `.dependency-cruiser.js` rule set, distinct from per-file ESLint |
| Extension descriptor | `provides_arch_gate()` returns `{'tool': 'dependency-cruiser'}` |
| Verify-step | `default:verify:arch-gate`, appended to `phase-5-execute.verification_steps` by `skill-domains configure` when the javascript domain is configured |
| Finding type | `arch-constraint` (one finding per structural-boundary violation, carrying the violated rule's identity) |

Running dependency-cruiser as its own dedicated invocation — rather than folding its checks into per-file ESLint — is what lets a module-boundary / forbidden-dependency violation surface as an `arch-constraint` finding instead of a generic lint issue. dependency-cruiser violations route to [`pm-dev-frontend:ext-triage-js`](../ext-triage-js/SKILL.md) for the per-finding disposition (FIX / SUPPRESS / ACCEPT); a violation that recurs across runs feeds the `arch-constraint` lesson type (rule-identity dedup, retire-on-quiet / reinforce-on-recurrence).

## Related

- [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) — the central, authoritative arch-gate model (single source of truth)
- [`extension-contract.md` § provides_arch_gate](../../../plan-marshall/skills/extension-api/standards/extension-contract.md) — the hook contract the JavaScript extension implements
- [`pm-dev-frontend:ext-triage-js`](../ext-triage-js/SKILL.md) — JavaScript triage, including `arch-constraint` finding disposition
