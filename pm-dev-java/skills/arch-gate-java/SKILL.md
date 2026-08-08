---
name: arch-gate-java
description: "Use when running or interpreting the Java arch-gate — the ArchUnit-based architectural-fitness-function check that runs as a per-deliverable read-only structural-boundary gate and emits arch-constraint findings. A thin pointer to the central arch-gate model in plan-marshall:manage-architecture; carries only the Java/ArchUnit binding."
user-invocable: false
mode: knowledge
---

# Java arch-gate (ArchUnit)

**REFERENCE MODE**: This skill provides reference material for the Java domain's `arch-gate` binding. It is a **thin pointer** — the structural concept, the read-only contract, the execution model, and the findings → triage → lesson feedback loop are owned by the central standard and MUST NOT be duplicated here.

The single authoritative model for `arch-gate` lives in [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) in `plan-marshall:manage-architecture`. Read that document for what an architectural fitness function is, the read-only structural-boundary-gate contract, the single per-deliverable execution model, resolution/execution path, and the lesson lifecycle. This skill carries only the Java-specific binding.

## Enforcement

**Execution mode**: Reference library; load for context when running or interpreting the Java arch-gate. Never execute this document's content as a workflow.

**Prohibited actions:**
- Do not duplicate the central `arch-gate-fitness-functions.md` model here — this skill is a thin pointer
- Do not mutate source from the arch-gate run — it is read-only with respect to both source and the lessons corpus
- Do not piggyback the ArchUnit rules onto `module-tests` — the `@ArchTest` rules run as a dedicated ArchUnit-only execution

**Constraints:**
- The Java arch-gate tool is ArchUnit; the descriptor the extension declares is `{'tool': 'archunit'}`
- arch-gate runs as a per-deliverable read-only verify-step resolved through `architecture resolve --command arch-gate`
- A structural-boundary violation is typed as an `arch-constraint` finding, never a generic `test-failure`

## Java binding

| Aspect | Java value |
|--------|------------|
| Native tool | ArchUnit |
| Rule surface | `@ArchTest` rules run as a dedicated ArchUnit-only invocation — a tagged Surefire/JUnit execution of only the `@ArchTest` rules, distinct from `module-tests` |
| Extension descriptor | `provides_arch_gate()` returns `{'tool': 'archunit'}` |
| Verify-step | `default:verify:arch-gate`, appended to `phase-5-execute.verification_steps` by `skill-domains configure` when the java domain is configured |
| Finding type | `arch-constraint` (one finding per structural-boundary violation, carrying the violated rule's identity) |

Running the `@ArchTest` rules as their own dedicated ArchUnit invocation — rather than masking violations inside the test suite — is what lets a structural-boundary violation surface as an `arch-constraint` finding instead of a failed test. ArchUnit violations route to [`pm-dev-java:ext-triage-java`](../ext-triage-java/SKILL.md) for the per-finding disposition (FIX / SUPPRESS / ACCEPT); a violation that recurs across runs feeds the `arch-constraint` lesson type (rule-identity dedup, retire-on-quiet / reinforce-on-recurrence).

## Related

- [`arch-gate-fitness-functions.md`](../../../plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md) — the central, authoritative arch-gate model (single source of truth)
- [`extension-contract.md` § provides_arch_gate](../../../plan-marshall/skills/extension-api/standards/extension-contract.md) — the hook contract the Java extension implements
- [`pm-dev-java:ext-triage-java`](../ext-triage-java/SKILL.md) — Java triage, including `arch-constraint` finding disposition
