# Architectural Fitness Functions (arch-gate)

The authoritative model for `arch-gate` — the canonical build command that runs a domain's native architectural-constraint tool as a deterministic, read-only structural-boundary gate. This document is the single home for the structural concept; the per-domain arch-gate skills (`arch-gate-java`, `arch-gate-python`, `arch-gate-js`) are thin pointers here and MUST NOT duplicate this content.

## What an architectural fitness function is

An architectural fitness function is an executable, objective check that a structural property of the codebase still holds — a layering rule, a directional import contract, a module-boundary constraint. Unlike a unit test (which asserts behaviour of one unit) or a linter (which flags per-file style/quality), a fitness function asserts a property of the dependency graph as a whole: "the `service` layer must not depend on `web`", "package A must not import package B", "the UI module may not reach into the persistence module directly".

`arch-gate` is the plan-marshall canonical command that runs these checks. Each domain binds it to the native tool that already expresses such rules in that ecosystem:

| Domain | Native tool | Rule surface |
|--------|-------------|--------------|
| Java | ArchUnit | `@ArchTest` rules run as a dedicated ArchUnit-only invocation (a tagged Surefire/JUnit execution of only the `@ArchTest` rules, distinct from module-tests) |
| Python | import-linter | Whole-graph directional / layered import contracts (distinct from per-file ruff) |
| JavaScript | dependency-cruiser | Module-boundary / forbidden-dependency rules (ESLint-boundaries class) |

## Read-only structural-boundary-gate contract

`arch-gate` is a **gate**, not a transformation. Its contract is strictly read-only with respect to both source and the lessons corpus:

- It **emits findings** — one `arch-constraint`-typed finding per structural-boundary violation (see [`../../manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) § `arch-constraint`).
- It **never mutates source** — it does not rewrite imports, move files, or apply fixes. Remediation is a downstream triage decision, never an arch-gate side effect.
- It **never mutates lessons** — the arch-gate run does not create, reinforce, or retire lessons. The lesson lifecycle (below) is driven by the existing lessons-housekeeping machinery from the findings the gate emitted, not by the gate itself.

## Single per-deliverable read-only execution model

There is exactly ONE arch-gate execution model: a per-deliverable read-only verify-step. arch-gate is always run as a dedicated structural-boundary check at the per-deliverable verification point — it is NEVER piggybacked onto `module-tests` and has NO execution-mode variants. A domain declares arch-gate availability by overriding the optional `provides_arch_gate()` hook to return a single-field descriptor `{'tool': <name>}` (no `execution_mode` key); see [`../../extension-api/standards/extension-contract.md`](../../extension-api/standards/extension-contract.md) § provides_arch_gate.

Running arch-gate as its own dedicated invocation — rather than masking violations inside the test suite — is what lets a structural-boundary violation be typed as an `arch-constraint` finding instead of a generic `test-failure`. The Java case is illustrative: the `@ArchTest` rules run as a dedicated ArchUnit-only Surefire/JUnit execution, separate from `module-tests`, so an ArchUnit violation surfaces as `arch-constraint`, not as a failed test.

## Resolution and execution path

arch-gate resolves through the standard build abstraction — the same `architecture resolve` path every canonical command uses (see [`resolve-command.md`](resolve-command.md)):

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command arch-gate --module {module}
```

`arch-gate` is an **extension-specific** canonical (not a required command), so a module receives an `arch-gate` command only when its domain populates one. On a module whose domain declares no arch-gate tool, the resolve no-ops and the verify-step is a silent skip. The verify-step itself is appended to `phase-5-execute.verification_steps` by `skill-domains configure` for every project whose configured domains include one with a non-None `provides_arch_gate()`; it is a **domain-appended** verify-step resolved through the same parameterized `canonical_verify.md` doc as the built-in canonicals — see [`../../extension-api/standards/ext-point-build-verify-step.md`](../../extension-api/standards/ext-point-build-verify-step.md) § Domain-Appended Verify Steps.

## Findings → triage → lesson feedback loop

arch-gate participates in the existing producer → store → triage pipeline; it introduces no new pipeline stage:

```text
arch-gate verify-step
  → emits arch-constraint finding (manage-findings)
  → ext-triage-{domain} disposition (FIX / SUPPRESS / ACCEPT)
  → recurring violation of the same rule
  → arch-constraint lesson (rule-identity dedup; retire-on-quiet / reinforce-on-recurrence)
  → architecture-hints pipe (existing surfacing mechanism)
```

1. **Emit** — the gate writes one `arch-constraint` finding per violation, carrying the violated rule's identity in the `rule` field.
2. **Triage** — the finding routes to the domain's `ext-triage-{domain}` skill, which decides the per-finding disposition (FIX / SUPPRESS / ACCEPT) exactly as it does for `lint-issue` / `sonar-issue` findings.
3. **Lesson** — a violation that recurs across runs feeds the `arch-constraint` lesson type, whose dedup key is **rule identity**: a recurring violation of the same rule REINFORCES the one lesson (recurrence count + a `## Recurrence` note) rather than allocating one lesson per instance. The lifecycle is **retire-on-quiet / reinforce-on-recurrence** — a rule that has been quiet for the configured window retires the lesson — and is deliberately NOT the promote-to-skill path. See [`../../manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) for the lesson category, the `rule` metadata field, and the recurrence semantics.
4. **Surface** — these lessons reach planning through the existing architecture-hints pipe; no new surfacing mechanism is introduced.

## Related

- [`../../extension-api/standards/extension-contract.md`](../../extension-api/standards/extension-contract.md) — the `provides_arch_gate()` hook contract
- [`../../extension-api/standards/ext-point-build-verify-step.md`](../../extension-api/standards/ext-point-build-verify-step.md) — the domain-appended verify-step discovery and resolution
- [`../../manage-findings/standards/jsonl-format.md`](../../manage-findings/standards/jsonl-format.md) — the `arch-constraint` finding type
- [`../../manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) — the `arch-constraint` lesson type and lifecycle
- [`resolve-command.md`](resolve-command.md) — canonical-command resolution via the build abstraction
