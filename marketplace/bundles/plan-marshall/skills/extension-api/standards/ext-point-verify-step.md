# Extension Point: Verify Step

> **Type**: Phase-5 Step Doc Extension | **Hook Method**: `implements:` frontmatter on each step doc | **Implementations**: 1 | **Status**: Active

## Overview

A verify step is one canonical verification command in the phase-5-execute pipeline — `quality-gate`, `module-tests` (`verify`), `coverage`, and the whole-tree-only gates `integration-tests` and `e2e`. Every built-in verify step is backed by a single **parameterized** step body doc (`phase-5-execute/standards/canonical_verify.md`): the doc reads the canonical from the trailing segment of a `default:verify:{canonical}` step ID, resolves it via `architecture resolve --command {canonical}`, and runs the resolved executable. The canonical is a parameter, never a hardcoded branch, so one doc backs the whole set.

This extension point names that step-doc archetype so verify steps are identified by an `implements:` frontmatter declaration — the same identification model every other archetype already uses (domain-bundle, build, triage, recipe, outline, self-review, finalize-step) — rather than by hand-maintained registry constants. The declaration IS the membership marker: a step doc that carries `implements: plan-marshall:extension-api/standards/ext-point-verify-step` is a verify-step implementor; one that does not is not. There is no `verify_step: true` marker and no per-source glob within the built-in discovery surface.

> **Scope of this ext-point**: This extension point governs **built-in** verify steps only — those declared in `phase-5-execute/standards/` and discovered via `implements:` frontmatter. The full verify-step universe surfaced by `_discover_all_verify_steps()` and `cmd_list_verify_steps` also includes **project** `verify-step-*` skills installed under `.claude/skills/`. Project verify steps are not governed by this ext-point and do not declare an `implements:` marker — they are discovered by a directory-name scan in `_discover_all_verify_steps()` as a separate source. The `verification_steps` seed (built-in defaults) and `cmd_list_verify_steps` (full listing) consume different subsets of the total universe; callers that need the full listing use `_discover_all_verify_steps()`, not just `find_implementors()`.

This extension point mirrors [ext-point-finalize-step.md](ext-point-finalize-step.md), which established the `implements:`-frontmatter discovery pattern for the phase-6-finalize step pipeline. The structural difference is the per-step membership shape: a finalize-step doc enumerates exactly one step (it declares a single `name`), whereas a verify-step doc enumerates a **set** of canonicals via a `canonicals:` list that the discovery query expands into one `default:verify:{canonical}` step ID per list entry. The single parameterized `canonical_verify.md` therefore declares the whole built-in canonical set in one frontmatter block.

Built-in verify-step discovery routes exclusively through the canonical extension-discovery machinery. The reusable `extension_discovery.find_implementors(...)` query (see [Resolution](#resolution)) enumerates every step doc that declares this interface and returns each step's frontmatter as a structured record carrying the `canonicals` list. The `verification_steps` seed consumes that query and expands its `canonicals` lists into `default:verify:{canonical}` step IDs; it carries no parallel list. The `_discover_all_verify_steps()` consumer also starts from that query for the built-in set, then appends a second source — project `verify-step-*` skills from `.claude/skills/` — so its output is a superset of `find_implementors()` alone.

## Implementor Requirements

### Implementor Frontmatter

All verify-step docs must include in their frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-verify-step
```

A step doc that already declares another interface declares both in YAML block-sequence (list) form:

```yaml
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-verify-step
```

**Frontmatter is the sole source of truth for verify-step discovery.** The `find_implementors()` scanner reads the `implements:` declaration from each candidate step doc and selects every doc whose declaration includes the canonical value above. The scanner does **not** read the markdown body for a discovery signal, and it does **not** identify a step by a directory-name or filename heuristic. A step doc whose frontmatter omits the declaration is not discovered.

Beyond the `implements:` declaration, each verify-step doc carries the following four-field frontmatter contract:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | str | Yes | The parameterized step-doc identity (e.g. `default:verify`). This is the doc's name in the built-in dispatch table; the runnable step IDs are derived per-canonical from `canonicals` (see below), not from `name`. |
| `order` | int | Yes | Integer position of the parameterized step within the built-in dispatch table. It positions the doc, not the canonicals relative to one another — inter-canonical ordering comes from the `canonicals` list order. |
| `canonicals` | list[str] | Yes | The verify-step-specific list of canonical command names this doc backs (e.g. `[quality-gate, module-tests, coverage]`). The discovery query expands each entry `C` into a `default:verify:{C}` step ID, in list order. This list IS the built-in verify-step set; an empty list means the doc declares no runnable canonical. |
| `description` | str | Yes | The human-readable discovery description (shown by the verify-step discovery surface and the wizard). |

**Canonicals expansion.** The discovery consumer expands `canonicals: [quality-gate, module-tests, coverage]` into the ordered step-ID set `[default:verify:quality-gate, default:verify:module-tests, default:verify:coverage]`. List order is execution order: the seed and the discovery surface both preserve it. Each expanded step ID seeds as a config-less keyed-map entry (`{step_id: {}}`) in `verification_steps`.

### Addressing Surface

A verify-step declaration is discovered from exactly this location:

| Location | Step kind | Notes |
|----------|-----------|-------|
| `phase-5-execute/standards/canonical_verify.md` | Built-in (parameterized) | The sole built-in verify-step implementor. One doc declares the whole canonical set via `canonicals:`. |

The phase-5-execute standards surface is verify-step-specific: the finalize-step scan surfaces (`phase-6-finalize/{workflow,standards}/*.md`, opt-in bundle `skills/*/SKILL.md`, project-local `.claude/skills/finalize-step-*/SKILL.md`) do NOT cover `phase-5-execute/standards/`, and the verify-step scan does NOT cover the phase-6 surfaces. The per-ext-point `implements:` match keeps the two surfaces disjoint, so adding the phase-5 scan leaves finalize-step discovery unchanged.

### Excluded Supporting Docs

Not every `.md` file under `phase-5-execute/standards/` is a verify step. Supporting docs — workflow detail, recovery patterns, sync-with-main, operations, and other cross-cutting references consumed by the phase-5-execute body — MUST NOT declare this interface. A supporting doc that erroneously declared `implements: ...ext-point-verify-step` would be wrongly seeded as a runnable verify step. The exclusion is enforced by NOT adding the declaration to those docs; the discovery query only surfaces docs that opt in via frontmatter.

## Hook API

A verify step is not a Python hook method on `ExtensionBase` — it IS a frontmatter declaration on a step body doc. Discovery flows through the reusable `extension_discovery.find_implementors()` query:

```python
def find_implementors(ext_point: str) -> list[dict]:
    """Enumerate every component that declares implements: {ext_point}.

    For ext-point-verify-step, scans:
      - phase-5-execute/standards/*.md (built-in verify-step docs)

    Each implementor record carries the step's frontmatter:
      {name, order, canonicals, description, source, path}

    where source is built-in and canonicals is the (possibly empty)
    list of canonical command names the doc backs.

    Resolves both the source structure
    (marketplace/bundles/{bundle}/skills/...) and the versioned cache
    structure (cache/.../{version}/skills/...) via the cache-aware
    configurable_contract doc-root primitives, so consumer projects with
    no marketplace/ source tree resolve through the installed plugin cache.
    """
```

The verify-step scan reuses the cache-aware doc-root primitives from `configurable_contract.py` for the phase-5-execute standards surface, mirroring the phase-6 scan the finalize-step ext-point already uses. The `canonicals` key is read by the same block-sequence frontmatter reader that already parses list-valued keys; it defaults to `[]` when absent. The query is the canonical enumeration that the `verification_steps` seed and `_discover_all_verify_steps()` consume; there is no parallel glob.

## Resolution

Verify-step discovery is exposed as the reusable `find_implementors(...)` library query and through its CLI verb. The CLI verb emits the implementor records as TOON:

```bash
# Enumerate every component implementing the verify-step interface
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  implementors --ext-point plan-marshall:extension-api/standards/ext-point-verify-step
```

The `verification_steps` seed (`_config_defaults.py`) consumes the query internally: it reads `find_implementors(VERIFY_STEP_EXT_POINT)`, expands every record's `canonicals` list into `default:verify:{canonical}` step IDs in list order, and seeds each as a config-less keyed-map entry. The per-step `description` is sourced from the implementor record.

The `_discover_all_verify_steps()` consumer (`_cmd_skill_domains.py`) starts from the same `find_implementors(VERIFY_STEP_EXT_POINT)` query for the built-in set, then appends project `verify-step-*` skills discovered from `.claude/skills/`. The CLI verb (`implementors --ext-point ...`) returns only the built-in set from `find_implementors()`; it does not include project verify steps.

There is no parallel glob or second discovery structure **within the built-in ext-point surface**. Project verify steps are a distinct source covered by `_discover_all_verify_steps()` and not by this ext-point.

## Current Implementations

The single built-in verify-step implementor lives under `phase-5-execute/standards/`. Its `canonicals` list declares the built-in canonical set, which the discovery query expands into the `default:verify:{canonical}` step IDs.

| Name | Source | Order | canonicals |
|------|--------|-------|------------|
| `default:verify` | built-in | 10 | `[quality-gate, module-tests, coverage]` |

The three canonicals expand, in list order, into the built-in step IDs `default:verify:quality-gate`, `default:verify:module-tests`, and `default:verify:coverage`, in execution order.

## Related Specifications

- [ext-point-finalize-step.md](ext-point-finalize-step.md) — Finalize-step extension point; the `implements:`-frontmatter discovery pattern this point mirrors
- [ext-point-domain-bundle.md](ext-point-domain-bundle.md) — Domain-bundle manifest extension point (same `implements:` identification model)
- [ext-point-recipe.md](ext-point-recipe.md) — Recipe extension point (same `implements:` identification model)
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference, including `phase-5-execute.verification_steps`
