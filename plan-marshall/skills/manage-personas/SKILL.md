---
name: manage-personas
description: Resolve a persona's composition DAG into a flat, deduped skills[] for dispatch
user-invocable: false
mode: script-executor
---

# Manage Personas Skill

Persona resolution for the persona / ref / profile identity model. The `resolve` verb computes the **transitive closure** of a persona's composition DAG and emits one flat, deduped `skills[]` that a dispatch site passes as the execution-context's explicit `skills[]`. This is deterministic *resolution* — analogous to `architecture resolve` and `manage-config resolve-recipe` — not new runtime authority and not nested skill loading.

## Enforcement

**Execution mode**: Single-verb script-executor — call `resolve` and route on the returned TOON `status`. Do not improvise additional verbs or arguments.

**Prohibited actions:**
- Do not hardcode a persona↔profile table — the persona's `profiles:` frontmatter is the binding source of truth.
- Do not hardcode a persona↔composition table — the persona's `composes:` frontmatter is the binding source of truth.
- Do not load composed personas via nested skill loading — composition is flattened by this resolver and carried in the explicit `skills[]`.

**Constraints:**
- The composition graph MUST be a DAG; the resolver detects and rejects cycles (`status: error`, `error: composition_cycle`).
- The base `persona-plan-marshall-agent` is always included, unconditionally — it is never read from `composes:`.

## What `resolve` does

Given `--persona-key {bundle:persona}` and optional `--domains a,b,c`, the resolver reads the persona's `SKILL.md` frontmatter and produces a flat, deduped `skills[]` by unioning, in deterministic order:

1. **Base** — always `plan-marshall:persona-plan-marshall-agent` (unconditional; same guarantee as the current foundational base load).
2. **Direct composition** — every `bundle:skill` notation in the persona's `composes:` frontmatter list (`ref-*` concerns and, for meta personas, other `persona-*` skills).
3. **Recursive composition** — for each composed `persona-*`, the transitive closure of *its* `composes:` and `profiles:` resolution (DAG walk; cycles rejected).
4. **Profile × domain** — for **each** profile in the persona's `profiles:` frontmatter list, the `profile × {domains}` domain skills resolved via the Extension API (`manage-config resolve-domain-skills --domain {domain} --profile {profile}`), for every domain in `--domains`. When `--domains` is omitted, no profile×domain skills are merged (the resolver emits base + composition only).

The persona's frontmatter (`profiles:` + `composes:`) is the sole binding source of truth — there is no hardcoded table anywhere in the resolver.

## Output

```toon
status: success
persona_key: plan-marshall:persona-implementer
skills[N]:
  - plan-marshall:persona-plan-marshall-agent
  - plan-marshall:ref-code-quality
  - ...
```

On error: `status: error` with an `error` discriminator (`persona_not_found`, `not_a_persona`, `composition_cycle`, `composed_persona_not_found`).

## Canonical invocations

The canonical argparse surface for `manage_personas.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### manage-personas — resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-personas:manage_personas resolve \
  --persona-key PERSONA_KEY [--domains DOMAINS]
```

`--persona-key` is the `bundle:skill` notation of the persona to resolve (e.g. `plan-marshall:persona-implementer`). `--domains` is an optional comma-separated list of domain names whose `profile × domain` skills are merged.
