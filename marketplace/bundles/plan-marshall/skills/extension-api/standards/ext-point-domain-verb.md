# Extension Point: Domain-Owned Executable Verb

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_domain_verb()` | **Implementations**: 0 (candidate contract) | **Status**: Specified — contract only, no `extension_base.py` hook wired in this plan

## Overview

A **domain-owned executable verb** is a domain-contributed *command* — a script or resolvable notation a domain bundle owns — that core dispatches through a resolved notation when the domain is active, and degrades to null-on-absent when it is not. It is the executable-capability sibling of the knowledge-contribution hooks (`provides_triage()` returns a *skill* to load; a domain verb returns a *command* to run).

This contract exists because domains legitimately own executable surfaces, not only knowledge. The already-shipped precedent is `provides_arch_gate()`: a domain declares its native architectural-constraint tool, core appends a `default:verify:arch-gate` step, and the step resolves through `architecture resolve --command arch-gate` and runs the domain's tool. A domain verb generalises that shape — a domain declares a named executable capability, core resolves it null-on-absent, and dispatches the resolved notation — without inventing a new registry, a new discovery structure, or a new dispatch mechanism.

The active-domain axis, the visibility semantics (invisible for a not-provided capability, diagnosable-refusal for a promised-but-unrunnable gate), and the degrade path this contract follows are decided in `ADR-010` (`Domain content is active only when its domain is active`, `doc/adr/`). A domain verb is a capability-provision surface: an inactive domain's verb resolves to a first-class `null`, and the calling workflow's documented null-branch continues with the core default. That invisibility is ADR-009-consistent because a not-provided verb asserts no positive property.

## Mechanism choice: a sibling ext-point

This is a **sibling extension point** that reuses the existing optional-hook + null-on-absent-resolve model. It is deliberately NOT either of two nearby designs:

- **NOT an extension of `ext-point-build`.** [ext-point-build.md](ext-point-build.md) is scoped to build-system module discovery (`discover_modules()`) and the `ExecuteConfig` factory — the "which modules exist and how do I build them" concern. A domain verb is a different concern (a domain-owned command, not a build-system module contract); folding it into `ext-point-build` would couple verb dispatch to build-system discovery and force every non-build domain that wants a verb to masquerade as a build system.
- **NOT a `find_implementors` domain-filter generalization.** `find_implementors(ext_point)` (see [ext-point-build-verify-step.md](ext-point-build-verify-step.md)) enumerates *skill/doc* implementors by `implements:` frontmatter for discovery of static step docs. Generalizing it into a per-domain verb filter would couple executable-verb dispatch to skill-implementor discovery — a category error: a domain verb is resolved by domain registration + null-on-absent, not by scanning skill frontmatter for a step doc. Verb discovery reuses the SAME `discover_all_extensions()` machinery the other optional hooks use, keyed on the domain's registration, not a new registry.

The contract therefore adds no new registry and no new discovery structure. It reuses `discover_all_extensions()` for discovery, the `workflow_skill_extensions` map for per-domain registration, and the `architecture resolve` / `resolve-*` null-on-absent pattern for resolution.

## The four contract faces

### 1. Declaration

A domain extension declares the verb by **either** of two forms, mirroring the existing hooks:

- An **optional Python hook** on the domain's `Extension` subclass, returning a descriptor-or-`None` (the `provides_arch_gate()` descriptor-or-None shape):

  ```python
  def provides_domain_verb(self) -> dict | None:
      """Return this domain's executable-verb descriptor, or None.

      Returns:
          A descriptor dict ``{'verb': str, 'notation': str}`` naming the verb
          type and the resolvable script notation the domain owns (e.g.
          ``{'verb': 'marker-detect', 'notation': 'pm-dev-java-cui:search-markers'}``),
          or None when the domain provides no such verb.

      Default: None
      """
  ```

  The `None` default is the silent-skip contract every optional hook shares: a domain that provides no verb implements nothing and core resolves the verb to null for that domain.

- A **`workflow_skill_extensions`-style entry** in `marshal.json`, keyed by verb type, under the domain's registration:

  ```json
  {
    "skill_domains": {
      "java-cui": {
        "bundle": "pm-dev-java-cui",
        "workflow_skill_extensions": {
          "marker-detect": "pm-dev-java-cui:search-markers"
        }
      }
    }
  }
  ```

  This is the same map `provides_triage()` / `provides_outline_skill()` persist through — keyed by verb type, value is the resolvable notation.

The verb type is the addressing key: it is `snake_case`/`kebab-case`, scoped within the domain, and names the capability (`marker-detect`, `arch-gate`, …), not the implementing script.

### 2. Discovery

Core discovers verb implementors uniformly through the **existing** `discover_all_extensions()` machinery and the `workflow_skill_extensions` map — the same path `provides_triage()` / `provides_outline_skill()` use. Discovery is keyed on the domain's `implements: plan-marshall:extension-api/standards/ext-point-domain-bundle` manifest declaration and the declared verb type. There is **no new registry, no new scan surface, and no per-verb glob**: a domain verb is discovered because its domain is a registered extension that declares the verb, exactly as a triage skill is discovered because its domain declares `provides_triage()`.

### 3. Dispatch

The domain-owned script/command is dispatched through the **resolved notation**, consistent with how `arch-gate` resolves and dispatches:

- For a build-canonical verb (the `arch-gate` precedent), the notation resolves through `architecture resolve --command {verb}` and core runs the returned `executable`.
- For a plain script-notation verb, the descriptor's `notation` is the executor notation core dispatches through the standard `python3 .plan/execute-script.py {notation} …` proxy.

Dispatch introduces no new execution mechanism — it reuses the executor proxy and the `architecture resolve` seam already in place. The verb's output (findings, a result TOON) flows into whatever consuming seam the caller already owns; the verb contract governs discovery/resolution/dispatch, not the output schema (which each verb type owns).

### 4. Core-side null-on-absent resolution

A `manage-config resolve-*` verb — a **sibling of the registered `resolve-workflow-skill-extension --domain --type {outline,triage}`** — resolves the domain-owned verb, returning `null` when no active domain implements it. The proposed verb shape (NOT yet registered — this is a contract-only spec) is:

```text
manage-config resolve-domain-verb --domain {domain} --type {verb_type}
```

The follow-up implementation MAY realise this either as a new sibling verb (`resolve-domain-verb`) or as a new `--type` value on the existing `resolve-workflow-skill-extension` verb — both express the same null-on-absent resolution; the choice is left to the implementing plan. The resolver never raises and never fabricates a positive: it returns the resolved notation when the active domain declares the verb, and a first-class `null` when it does not. The consuming workflow carries a documented null-branch that degrades to the core default per `ADR-010` § "Degrade path when no implementor exists" — the same degrade path `resolve-workflow-skill-extension` establishes for `outline` / `triage`.

> **Scope of this plan.** This document specifies the contract; it wires no `extension_base.py` hook and no `manage-config resolve-domain-verb` verb. The Python implementation is a follow-up gated on this contract and ADR-010. The registration in [extension-contract.md](extension-contract.md) is documentation-only.

## Resolution

The proposed resolution surface (contract-only — not yet registered) resolves the domain-owned verb notation for a domain + verb type, returning `null` on absent:

```text
manage-config resolve-domain-verb --domain {domain} --type {verb_type}
```

The already-registered precedent this mirrors is `resolve-workflow-skill-extension --domain {domain} --type {outline,triage}` (see [ext-point-triage.md](ext-point-triage.md) § Resolution).

**Path**: `skill_domains.{domain_key}.workflow_skill_extensions.{verb_type}`

## Current + candidate implementations

There are no shipped `provides_domain_verb()` implementors yet — the hook is contract-only in this plan. The contract is validated as sufficient against two concrete cases:

| Case | Domain | Verb | Role in validation |
|------|--------|------|--------------------|
| Relocated marker detector | `java-cui` (pm-dev-java-cui) | `marker-detect` (e.g. `pm-dev-java-cui:search-markers`) | The **contributed candidate**. A domain-owned OpenRewrite/TODO marker detector that must run only when the java-cui domain is active — its relocation out of the core bundle into a domain bundle is exactly the "domain content is active only when its domain is active" case `ADR-010` governs. It declares `provides_domain_verb()` / a `workflow_skill_extensions.marker-detect` entry, core resolves it null-on-absent, and a project without java-cui active resolves the verb to null (the marker gate simply does not run — a capability-provision invisibility, not a silent gate). |
| Arch-gate command | java / python / javascript | `arch-gate` | The **already-shipped precedent**. `provides_arch_gate()` returns a descriptor, `skill-domains configure` seeds `default:verify:arch-gate`, and the step resolves through `architecture resolve --command arch-gate` and dispatches the domain's tool. This proves the declaration→discovery→dispatch→null-on-absent pattern already resolves and dispatches in production, so a generalized `provides_domain_verb()` inherits a validated mechanism rather than an untested one. |

The two cases bracket the contract: the arch-gate precedent proves the pattern is production-real for a build-canonical verb resolved through `architecture resolve`, and the marker detector proves the same shape covers a plain script-notation verb dispatched through the executor proxy — with the same null-on-absent degrade when the domain is inactive.

## Related Specifications

- `ADR-010` (`Domain content is active only when its domain is active`, `doc/adr/`) — the gating-axis, visibility, and degrade decisions this verb realises for executable capabilities.
- [extension-contract.md](extension-contract.md) — The core extension-hook contract; registers this hook in the Extension Points table and the optional-methods index.
- [ext-point-build-verify-step.md](ext-point-build-verify-step.md) — The `arch-gate` domain-appended verify-step (§ Domain-Appended Verify Steps), the already-shipped executable-capability precedent this contract generalises.
- [ext-point-triage.md](ext-point-triage.md) — The `provides_triage()` hook whose `workflow_skill_extensions` registration and `resolve-workflow-skill-extension` null-on-absent resolver this verb's resolution mirrors.
- [ext-point-build.md](ext-point-build.md) — The build-system extension point this contract is a sibling of, NOT an extension of.
- [marshal-json-reference.md](marshal-json-reference.md) — Central marshal.json path reference, including `skill_domains.{key}.workflow_skill_extensions`.
