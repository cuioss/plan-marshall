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
- The base `persona-plan-marshall-agent` is always assembled, unconditionally — it is never read from `composes:` — and is then subject to the exclusion lists configured for the requested `--domains`, like every other skill.

## What `resolve` does

Given `--persona-key {bundle:persona}` and optional `--domains a,b,c`, the resolver reads the persona's `SKILL.md` frontmatter and produces a flat, deduped `skills[]` by unioning, in deterministic order:

1. **Base** — always `plan-marshall:persona-plan-marshall-agent` at assembly time (unconditional; same guarantee as the current foundational base load), then subject to the exclusion lists configured for the requested `--domains`.
2. **Direct composition** — every `bundle:skill` notation in the persona's `composes:` frontmatter list (`ref-*` concerns and, for meta personas, other `persona-*` skills).
3. **Recursive composition** — for each composed `persona-*`, the transitive closure of *its* `composes:` and `profiles:` resolution (DAG walk; cycles rejected).
4. **Profile × domain** — for **each** profile in the persona's `profiles:` frontmatter list, the `profile × {domains}` domain skills resolved via the Extension API (`manage-config resolve-domain-skills --domain {domain} --profile {profile}`), for every domain in `--domains`. When `--domains` is omitted, no profile×domain skills are merged (the resolver emits base + composition only).

**Module qualification of optionals.** A cell's `defaults` are kept unless a repository-level exclusion names them. An `optional` is merged only when `--module` names a module the domain extension qualifies for that skill through its module-level applicability hook (`qualifies_optional`; the Java extension excludes its CDI- and Lombok-dependent optionals for a module without that dependency, and every other domain's hook default admits the optional) — not merely because the cell lists it. A repository-level exclusion in `skill_domains.{domain}.excluded_skills` (``bundle:skill`` or bare skill name; the resolver compares both) always removes a skill, even one the module qualifies for. A bare-name entry removes the same-named skill whatever bundle carries it; a bundle-qualified entry narrows to its own bundle — it removes the skill only when the entry's bundle is the domain's configured `bundle`, whichever notation the cell used. When `--module` is omitted, or the module's frameworks cannot be read, the resolver keeps defaults only and reports `module_status: not_requested` / `unreadable`; it never falls back to every optional.

The persona's frontmatter (`profiles:` + `composes:`) is the sole binding source of truth — there is no hardcoded table anywhere in the resolver.

## Output

```toon
status: success
persona_key: plan-marshall:persona-implementer
module: my-module
module_status: resolved
skills[N]:
  - plan-marshall:persona-plan-marshall-agent
  - plan-marshall:ref-code-quality
  - ...
```

`module` echoes the `--module` value (empty when omitted). `module_status` is `resolved` (the module was read wherever a cell had optionals to qualify, and no cell reported it unreadable), `not_requested` (no `--module` supplied), or `unreadable` (at least one cell could not read the module's data or its domain extension's applicability, so that cell contributes no optionals).

On error: `status: error` with an `error` discriminator (`persona_not_found`, `not_a_persona`, `composition_cycle`, `composed_persona_not_found`, `profile_required`, `skill_exclusions_unreadable`). `skill_exclusions_unreadable` means the repository's exclusion list exists but could not be read — the call is refused rather than answered with an unfiltered skill list.

## Canonical invocations

The canonical argparse surface for `manage_personas.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT, matching its heading only — the body is never read; `manage-invocation-invalid` derives its accept-set from a live `--help` walk rather than from this section. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### manage-personas — resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-personas:manage_personas resolve \
  --persona-key PERSONA_KEY [--domains DOMAINS] [--module MODULE]
```

`--persona-key` is the `bundle:skill` notation of the persona to resolve (e.g. `plan-marshall:persona-implementer`). `--domains` is an optional comma-separated list of domain names whose `profile × domain` skills are merged. `--module` is the task's module name; profile×domain optionals are admitted only when that module qualifies for them, and omitting it admits defaults only.

### manage-personas — resolve-task-skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-personas:manage_personas resolve-task-skills \
  --profile PROFILE [--domains DOMAINS] [--module MODULE]
```

`--profile` is the task's primary profile (e.g. `implementation`). The verb derives the persona from it — the persona whose FIRST `profiles:` entry equals `PROFILE` — and returns that persona's flattened `skills[]` as `resolve` does, plus `profile` and the derived `persona_key`. An unclaimed profile answers `persona_key: ""` with `reason: no_persona_for_profile` and an empty `skills[]`. This is the one call phase-4-plan's persona augmentation makes: the derivation is a script's job, not a scan the workflow is asked to perform by hand.
