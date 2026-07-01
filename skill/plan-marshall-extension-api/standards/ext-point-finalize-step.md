# Extension Point: Finalize Step

> **Type**: Phase-6 Step Doc Extension | **Hook Method**: `implements:` frontmatter on each step doc | **Implementations**: 25 | **Status**: Active

## Overview

A finalize step is one unit of work in the phase-6-finalize pipeline — push, create-pr, lessons-capture, sonar-roundtrip, archive-plan, and so on. Each step is an LLM-driven body doc (a `workflow/*.md` or `standards/*.md` file under `phase-6-finalize`, an opt-in bundle `SKILL.md`, or a project-local `.claude/skills/finalize-step-*/SKILL.md`) whose `---`-fenced frontmatter declares the step's identity, execution order, default-seed membership, and named-preset memberships.

This extension point names that step-doc archetype so finalize steps are identified by an `implements:` frontmatter declaration — the same identification model every other archetype already uses (domain-bundle, build, triage, recipe, outline, self-review) — rather than by hand-maintained registry constants. The declaration IS the membership marker: a step doc that carries `implements: plan-marshall:extension-api/standards/ext-point-finalize-step` is a finalize step; one that does not is not. There is no `finalize_step: true` marker, no second discovery structure, and no per-source glob.

Discovery routes exclusively through the canonical extension-discovery machinery. The reusable `extension_discovery.find_implementors(...)` query (see [Resolution](#resolution)) enumerates every step doc that declares this interface and returns each step's frontmatter as a structured record. The finalize-step registry, the named-preset builder, and every cross-bundle consumer CONSUME that one query; none of them carries a parallel list.

## Implementor Requirements

### Implementor Frontmatter

All finalize-step docs must include in their frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
```

A step doc that already declares another interface (e.g. `ext-point-execution-context-workflow`, which the `workflow/*.md` step bodies carry) declares both in YAML block-sequence (list) form:

```yaml
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
```

**Frontmatter is the sole source of truth for finalize-step discovery.** The `find_implementors()` scanner reads the `implements:` declaration from each candidate step doc and selects every doc whose declaration includes the canonical value above. The scanner does **not** read the markdown body for a discovery signal, and it does **not** identify a step by a directory-name or filename heuristic. A step doc whose frontmatter omits the declaration is not discovered.

Beyond the `implements:` declaration, each finalize-step doc carries the following five-field frontmatter contract. These fields replace the removed `BUILT_IN_FINALIZE_STEPS` / `OPTIONAL_BUNDLE_FINALIZE_STEPS` lists and the `*_DESCRIPTIONS` maps as the per-step source of truth:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | The step id. `default:{bare}` for a built-in phase-6-finalize step (e.g. `default:push`), `{bundle}:{skill}` for an opt-in bundle step (e.g. `plan-marshall:plan-retrospective`), `project:finalize-step-{bare}` for a project-local step (e.g. `project:finalize-step-deploy-target`). |
| `order` | int | Yes | Integer execution order. The seed and the discovery query both sort by this value, so the on-disk `phase-6-finalize.steps` order is deterministic. |
| `default_on` | bool | Yes | `true` ⇒ the step is included in the default seed (`_seed_finalize_steps()` filters to `default_on == true`). `false` ⇒ the step is discoverable but opt-in (it is added to a project's `phase-6-finalize.steps` only by an explicit preset or hand-registration). |
| `presets` | list[str] | Yes | The named presets this step belongs to — a (possibly empty) subset of `[local, standard, full]`. The preset builder derives "step S belongs to preset P" as `P ∈ S.presets`. An empty list `[]` means the step is in no named preset. |
| `description` | str | Yes | The human-readable discovery description (shown by `list-finalize-steps` and the wizard). This is the single source of the per-step description, replacing the removed `*_DESCRIPTIONS` maps. |

### Addressing Surface

A finalize-step declaration is discovered from exactly these locations:

| Location | Step kind | Resolver precedence |
|----------|-----------|---------------------|
| `phase-6-finalize/workflow/*.md` | Built-in (`default:{bare}`) | Wins on name collision with a `standards/` doc of the same bare name. |
| `phase-6-finalize/standards/*.md` | Built-in (`default:{bare}`) | Yields to a `workflow/` doc of the same bare name. |
| Opt-in bundle `skills/*/SKILL.md` | Bundle-optional (`{bundle}:{skill}`) | n/a — full bundle:skill name is unique. |
| Project-local `.claude/skills/finalize-step-*/SKILL.md` | Project (`project:finalize-step-{bare}`) | n/a — project namespace is unique. |

The `workflow/` ⇒ `standards/` precedence rule mirrors `configurable_contract.resolve_step_doc_path`: when a built-in step has both a `workflow/{name}.md` and a `standards/{name}.md`, the `workflow/` doc is the canonical body and carries the frontmatter declaration. (In practice each built-in step has exactly one of the two; `push`, for example, lives only at `standards/push.md` with `name: default:push`, so no precedence conflict arises.)

### Excluded Supporting Docs

Not every `.md` file under `phase-6-finalize/{workflow,standards}/` is a finalize step. Supporting docs — shared templates, validation rules, and cross-cutting references consumed by the step bodies — MUST NOT declare this interface. The known supporting docs that are explicitly excluded:

| Doc | Role |
|-----|------|
| `output-template.md` | Shared finalize-summary output template. |
| `validation.md` | Cross-step validation rules. |
| `required-steps.md` | Documents which steps are mandatory; not itself a step. |
| `disposition-to-hint-routing.md` | Disposition → architecture-hint routing reference. |
| `lessons-integration.md` | Lessons-capture integration reference. |
| `adr-integration.md` | ADR-proposal integration reference. |

A supporting doc that erroneously declared `implements: ...ext-point-finalize-step` would be wrongly seeded as a runnable step. The exclusion is enforced by NOT adding the declaration to these docs; the discovery query only surfaces docs that opt in via frontmatter.

## Hook API

A finalize step is not a Python hook method on `ExtensionBase` — it IS a frontmatter declaration on a step body doc. Discovery flows through the reusable `extension_discovery.find_implementors()` query:

```python
def find_implementors(ext_point: str) -> list[dict]:
    """Enumerate every component that declares implements: {ext_point}.

    For ext-point-finalize-step, scans:
      - every bundle's skills/*/SKILL.md (opt-in bundle steps)
      - phase-6-finalize/workflow/*.md + standards/*.md (built-in steps,
        workflow/ winning on name collision)
      - project-local .claude/skills/finalize-step-*/SKILL.md (project steps)

    Each implementor record carries the step's frontmatter:
      {name, order, default_on, presets, description, source, path}

    where source is one of: built-in, bundle-optional, project.

    Resolves both the source structure
    (marketplace/bundles/{bundle}/skills/...) and the versioned cache
    structure (cache/.../{version}/skills/...) via the cache-aware
    configurable_contract doc-root primitives, so consumer projects with
    no marketplace/ source tree resolve through the installed plugin cache.
    """
```

The query reuses the cache-aware doc-root primitives from `configurable_contract.py` (`resolve_step_doc_path`, `_phase_6_skill_dir`, `_extract_frontmatter_lines`, `_coerce_scalar`) for the phase-6 doc surface, and the existing bundles-root + cache-root resolution from `extension_discovery.py` for the `skills/*/SKILL.md` surface. It is the canonical enumeration that `_seed_finalize_steps()`, `_discover_all_finalize_steps()`, and the `FinalizeStepPresets` builder consume; there is no parallel glob.

## Resolution

Finalize-step discovery is exposed both as a library function and as a CLI verb. The CLI verb emits the implementor records as TOON:

```bash
# Enumerate every component implementing the finalize-step interface
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  implementors --ext-point plan-marshall:extension-api/standards/ext-point-finalize-step
```

The finalize-step registry surfaces the resolved universe through the existing `manage-config` CLI, which consumes the discovery query internally:

```bash
# List every discovered finalize step with name / description / source / order
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config list-finalize-steps
```

There is **no parallel glob and no second discovery structure**. The `find_implementors(...)` query is the sole discovery path; the seed (default-on filter), the discovery surface, and the preset builder all read its records.

## Current Implementations

Every step doc that declares the finalize-step interface. Built-in steps live under `phase-6-finalize/{workflow,standards}/`; the opt-in bundle step ships under its bundle's `skills/`; project steps are meta-project-local under `.claude/skills/`.

| Name | Source | Order | default_on | presets |
|------|--------|-------|:----------:|---------|
| `default:finalize-step-sync-baseline` | built-in | 3 | true | `[full]` |
| `default:pre-push-quality-gate` | built-in | 5 | true | `[full]` |
| `default:finalize-step-simplify` | built-in | 8 | true | `[full]` |
| `default:finalize-step-security-audit` | built-in | 9 | true | `[]` |
| `default:push` | built-in | 10 | true | `[local, standard, full]` |
| `default:create-pr` | built-in | 20 | true | `[standard, full]` |
| `default:ci-verify` | built-in | 22 | true | `[standard, full]` |
| `default:architecture-refresh` | built-in | 25 | false | `[]` |
| `default:automated-review` | built-in | 30 | true | `[standard, full]` |
| `default:sonar-roundtrip` | built-in | 40 | true | `[full]` |
| `default:lessons-capture` | built-in | 60 | true | `[local, standard, full]` |
| `default:adr-propose` | built-in | 62 | false | `[]` |
| `default:pre-submission-self-review` | built-in | 7 | false | `[]` |
| `default:branch-cleanup` | built-in | 70 | true | `[local, standard, full]` |
| `default:finalize-step-preference-emitter` | built-in | 80 | true | `[]` |
| `default:record-metrics` | built-in | 998 | true | `[local, standard, full]` |
| `default:finalize-step-print-phase-breakdown` | built-in | 999 | true | `[]` |
| `default:archive-plan` | built-in | 1000 | true | `[local, standard, full]` |
| `plan-marshall:plan-retrospective` | bundle-optional | 995 | false | `[full]` |
| `project:finalize-step-plugin-doctor` | project | 6 | false | `[]` |
| `project:finalize-step-pre-submission-self-review` | project | 7 | false | `[]` |
| `project:finalize-step-review-retrospective` | project | 50 | false | `[]` |
| `project:finalize-step-deploy-target` | project | 80 | false | `[]` |
| `project:finalize-step-sync-plugin-cache` | project | 85 | false | `[]` |
| `project:finalize-step-lessons-housekeeping` | project | 996 | false | `[]` |

Project steps carry `default_on: false` and `presets: []` because they are hand-registered in the meta-project's `phase-6-finalize.steps` array (presets ship to consumer projects, which do not have the meta-project's project-local finalize-step skills). The bundle-optional `plan-marshall:plan-retrospective` step is opt-in (`default_on: false`) and a member of the `full` preset only.

## Related Specifications

- [ext-point-domain-bundle.md](ext-point-domain-bundle.md) — Domain-bundle manifest extension point (same `implements:` identification model)
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference, including `phase-6-finalize.steps`
