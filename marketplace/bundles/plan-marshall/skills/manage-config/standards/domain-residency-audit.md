# Domain-residency audit

An enumeration of every domain-specific item resident in the core `plan-marshall`
bundle, each carrying a fix-or-justify disposition mapped to the mechanism that
homes it. The governing decision is `ADR-010` (`Domain content is active only when
its domain is active`): domain-specific content is in play only when its domain is
active, capability-provision layers gate invisibly (null-on-absent), status-bearing
gate layers refuse diagnosably, and the executor notation layer stays deliberately
domain-blind.

Two residency shapes are classified:

- **Shape (D) — domain-conditional gating site.** A core site whose behaviour must
  vary with the active-domain set (the seed / resolve / dispatch of a
  domain-owned capability). It is CORRECT when it gates on the right axis with the
  right visibility semantic, and a DEFECT when the gating axis or the resolvability
  check is wrong.
- **Shape (L) — domain literal in core.** A specific domain name (`java`, `python`,
  `javascript`, `oci-containers`, …) or a domain-owned tool (`archunit`,
  `import-linter`, `dependency-cruiser`, …) that appears in a core-resident skill,
  script, or standard. It is CORRECT (JUSTIFY) when it is illustrative inside
  domain-neutral machinery, and a DEFECT (FIX) when it hardcodes domain-specific
  behaviour into the domain-agnostic core.

Each FIX disposition maps to a concrete mechanism: **D1** (a gating/visibility
decision — the ADR), **D2** (the domain-owned-verb contract), **D3** (the executor
notation decision), or **D5** (the arch-gate seed/resolve fix). A **JUSTIFY** states
why the item is legitimately core-owned.

## Surveyed scope

This is an enumeration (not a sample) over the declared survey scope — the sites in
the core `plan-marshall` bundle where domain-specific residue lives by construction:

- the extension-resolution + seeding scripts
  (`manage-config/scripts/_cmd_skill_domains.py`, `_config_defaults.py`);
- the composer's domain-conditional handling
  (`manage-execution-manifest/scripts/manage-execution-manifest.py`);
- the extension-api contract surface
  (`extension-api/standards/extension-contract.md`,
  `ext-point-build-verify-step.md`, `ext-point-domain-verb.md`) and the
  `extension_base.py` optional-hook surface;
- the domain-neutral resolve verbs (`manage-config` `resolve-*`).

The core bundle is domain-agnostic by design, so domain residue does not appear
uniformly across every skill — it clusters in the extension machinery above. Every
domain-specific item within that scope appears below with a disposition.

The retrospective `affected_files_recall` check runs against the
*expected-to-mutate* subset — this single audit document — NOT the survey scope
enumerated above.

## Surveyed sites

### manage-config/scripts/_cmd_skill_domains.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `_configured_domains_provide_arch_gate` + the `verification_steps['default:verify:arch-gate'] = {}` seed append (arch-gate seed block) | (D) | **FIX (D5).** The seed appends `default:verify:arch-gate` for the project when ANY configured domain's extension returns a non-None `provides_arch_gate()` — the correct *availability-axis* signal ("a configured domain declares an arch-gate tool"). The seed's extension-presence gate itself is LEFT INTACT and JUSTIFIED. The mismatch is downstream: the seed cannot express whether any in-scope module actually resolves the `arch-gate` command (a per-plan/per-footprint property). D5 corrects it at the compose layer with a diagnosable resolvability skip; this seed site is the availability-axis half of the fix and stays as-is. |
| `_discover_all_verify_steps()` (built-in `find_implementors` set + project `verify-step-*` skills) | (D) | **JUSTIFY.** Domain-agnostic discovery — enumerates verify-step implementors uniformly by `implements:` frontmatter and project-skill scan, with no domain literal and no per-domain branch. |
| `load_domain_config_from_bundle` / `discover_available_domains` / `convert_extension_to_domain_config` / `resolve-domain-skills` / `attach-project` / `active-profiles` handlers | (D) | **JUSTIFY.** Domain-neutral machinery: iterates whatever domains are configured/discovered and reads each extension's hooks. No domain is named or special-cased; the docstring examples (`'java'`, `'javascript'`) are illustrative parameter values, not hardcoded behaviour. |
| `load_domain_config_from_bundle` docstring example `domain_key` values (`'java'`, `'javascript'`) | (L) | **JUSTIFY.** Illustrative docstring examples inside a domain-neutral loader — the function accepts any domain key; no behaviour is gated on the named domains. |

### manage-config/scripts/_config_defaults.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `_seed_verify_steps()` (expands each `ext-point-build-verify-step` implementor's `canonicals` list into `default:verify:{canonical}` IDs) | (D) | **JUSTIFY.** Domain-agnostic seed of the built-in canonical set from the single discovery query; no domain literal, no per-domain branch. The domain-conditional arch-gate append is layered on top in `_cmd_skill_domains.py` (the FIX-D5 site above), not here. |
| `validate_domain_invariants` / `validate_domain_inclusion` (domain-config invariant validators) | (D) | **JUSTIFY.** Structural validators over the `skill_domains` shape — they enforce the domain-registration contract without naming or special-casing any specific domain, and fail closed (raise `ValueError`) on an invalid shape rather than silently accepting it. |
| `DEFAULT_SYSTEM_DOMAIN` and the system-domain default | (L) | **JUSTIFY.** The `general-dev` / system-domain default is the core's own domain-neutral baseline, not a language/content domain; it is legitimately core-owned. |

### manage-execution-manifest/scripts/manage-execution-manifest.py

| Site | Shape | Disposition |
|------|-------|-------------|
| Domain-seeded verify-step resolvability filter over `phase_5.verification_steps` (the D5 compose-layer skip) | (D) | **FIX (D5).** The composer must drop a domain-seeded verify-step (`default:verify:arch-gate`, generalized over the domain-seeded step class) whose canonical resolves for no in-scope module, emitting a diagnosable `[STATUS]` warning rather than a silent drop — the status-bearing-gate visibility semantic from `ADR-010`. This is the concrete compose-layer half of the arch-gate seed/resolve fix. |
| `_classify_paths_via_extensions` (names `build-pyproject` / `build-maven` / `build-gradle` / `build-npm` in docstrings) | (L) | **JUSTIFY.** The aggregator delegates file classification to the build-system extensions via `classify_paths()`; the build-system names are illustrative docstring references to the extensions that own the claims, not hardcoded classification. Documentation recognition is a generic suffix rule, also domain-neutral. |
| `_CANONICAL_TO_ROLE` / `_apply_canonical_verify_inactive` / `_stamp_phase_5_step_execution_tier` | (D) | **JUSTIFY.** Canonical-command-keyed, domain-agnostic role resolution and footprint/tier handling; a domain-contributed canonical (e.g. `arch-gate`) is handled by the generalized domain-seeded class (D5), not by a per-domain branch. |

### extension-api contract surface

| Site | Shape | Disposition |
|------|-------|-------------|
| `extension-contract.md` `provides_arch_gate` example tool names (`archunit` / `import-linter` / `dependency-cruiser`) | (L) | **JUSTIFY.** Illustrative examples inside a domain-neutral optional-hook contract — the hook itself hardcodes no tool; each domain declares its own via the descriptor. |
| `extension-contract.md` `get_skill_domains` examples + "Bundles Implementing This Convention" table (names all 10 bundles / domains) | (L) | **JUSTIFY.** Documentation of the domain-neutral registry surface; it enumerates the installed domains for the reader but gates no behaviour on any of them. |
| `extension_base.py` optional hooks (`provides_triage` / `provides_outline_skill` / `provides_recipes` / `provides_arch_gate` / `config_defaults`) | (D) | **JUSTIFY.** Domain-neutral optional hooks with safe `None`/`[]` defaults — each domain declares its own capability; the core hardcodes none. This is the null-on-absent degrade machinery `ADR-010` builds on. |
| Absence of a general domain-owned *executable verb* declaration surface | (D) | **FIX (D2).** Before this design package, a domain that owns an executable verb (e.g. a relocated marker detector) had no first-class core-side contract to declare/discover/dispatch it beyond the arch-gate special case. D2 (`ext-point-domain-verb.md`) homes this as a sibling ext-point with null-on-absent resolution. |
| `ext-point-build-verify-step.md` § Domain-Appended Verify Steps (`default:verify:arch-gate`) | (D) | **JUSTIFY.** Correctly domain-conditional: the step is appended only for a project whose configured domains declare an arch-gate tool, and resolves through the same parameterized `canonical_verify.md`. The runnability gap is corrected by D5; the contract description itself is accurate and domain-neutral in mechanism. |

### tools-script-executor (executor notation layer)

| Site | Shape | Disposition |
|------|-------|-------------|
| `generate_executor.py` domain-blind `SCRIPTS` map (registers every bundle's notations regardless of active domains) | (D) | **JUSTIFY (D3 — deliberately not gated).** The executor is domain-blind by design. D3 (`domain-aware-notation-spec.md`) specifies the domain-aware alternative in full and explicitly DECLINES it, keeping the executor domain-blind and deferring inactive-domain enforcement to resolve/dispatch time. This is a legitimately core-owned domain-blind layer per `ADR-010`'s "deliberately not gated" decision. |

### manage-config resolve verbs

| Site | Shape | Disposition |
|------|-------|-------------|
| `resolve-workflow-skill-extension --domain --type {outline,triage}` / `resolve-domain-skills` / `resolve-outline-skill` / `resolve-recipe` | (D) | **JUSTIFY.** The null-on-absent resolve verbs are correctly domain-neutral: they ARE the gate — they resolve to null precisely when the domain is inactive — so they are legitimately core-owned and must NOT themselves be domain-gated (gating the gate). They are the degrade-path precedent D2's `resolve-domain-verb` mirrors. |

## Shared anchor

Every domain-conditional gating site (Shape D) resolves to ONE of two correct
postures, both owned by `ADR-010`:

- **Capability-provision** (skill loading, hook resolution, the resolve verbs, the
  domain verb, the domain-blind executor) gates **invisibly** — an inactive
  domain's capability resolves to a first-class `null` / is simply not registered,
  asserting no positive property. These are JUSTIFY (correctly domain-neutral core
  machinery) or homed by D2/D3.
- **Status-bearing gate** (a domain-seeded verify-step that was promised but cannot
  resolve for the footprint) refuses **diagnosably** — the D5 compose-layer
  skip-with-warning, never a silent drop that would launder into a false "gate
  passed."

The single concrete code defect the sweep found is the arch-gate seed/resolve
mismatch, split across its two halves (the availability-axis seed in
`_cmd_skill_domains.py`, left intact; the per-footprint resolvability check in the
composer, added by D5).

## Summary

- **Total domain-specific core-resident items enumerated:** 17.
- **FIX sites: 3.**
  - Arch-gate seed append (`_cmd_skill_domains.py`) — **D5** (availability-axis half; seed left intact).
  - Domain-seeded verify-step resolvability filter (`manage-execution-manifest.py`) — **D5** (compose-layer diagnosable skip).
  - Absence of a domain-owned executable-verb declaration surface (extension-api) — **D2** (sibling ext-point contract).
- **JUSTIFY sites: 14** — the domain-neutral extension-discovery / resolve / seed machinery, the illustrative domain literals inside domain-neutral contracts, the correctly domain-conditional arch-gate verify-step description, and the deliberately domain-blind executor (D3, declined).
- **Mechanism mapping:** the two concrete code FIXes both route to **D5** (the arch-gate seed/resolve fix); the one contract-gap FIX routes to **D2**; the executor-layer decision is homed by **D3** (specify-then-decline); the overarching gating/visibility model that classifies every site is **D1** (`ADR-010`).
