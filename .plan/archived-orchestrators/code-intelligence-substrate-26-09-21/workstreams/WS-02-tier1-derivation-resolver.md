# WS-02: Tier 1 — The Derivation Resolver

epic: code-intelligence-substrate

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-tier1-derivation-resolver.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Tier 1 derives real dependency edges with **no external dependency and nothing configured**. It is
the **load-bearing tier**: it is what makes Tier 2 optional rather than required. It closes when
`graph`, `path`, `neighbors`, and `impact` return real answers for a bundle project, a Python
project, and an npm project — not only for Maven.

The mechanism is the operator's **resolver pattern**: `manage-architecture` stays the stable query
surface consumers already speak, and gains a pluggable derivation resolver behind it. Core declares
the seam; domain bundles implement it — the same shape as the seven existing extension points.

## Scope

- **In scope**: the resolver extension-point seam in core; `manage-architecture` delegating edge
  derivation to it; the marketplace-component resolver; native coordinate resolvers for the
  non-Maven build systems; and the capability-reporting contract for the **graph-family** verbs.
- **Out of scope**: the files inventory and content search (WS-01); the skill-corpus reference index
  as an editor-facing product (WS-03) — this workstream produces the *index*, WS-03 presents it;
  measurement and cost accounting (WS-04); planning-phase detector integrity (WS-05).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-resolver-ext-point-seam | staged | **N-resolver** seam + per-edge **provenance**; retires the Maven-only join as *a* resolver, not *the* derivation |
| PLAN-08-lsp-shaped-query-api | staged | LSP vocabulary over the query surface + capability report + the vacuous-guard fix |
| PLAN-04-marketplace-dependency-resolver | staged | ⛔ Implementation at `pm-plugin-development` (operator). **TWO resolvers**: markdown + Python |
| PLAN-05-native-coordinate-resolvers | staged | pyproject / npm resolvers — the consumer-facing half |
| PLAN-09-resolver-configuration | staged | `marshall-steward` menu + machine-local `.plan/local/run-configuration.json` binding |

## The four operator constraints this workstream implements

1. **N resolvers, configurable** — plan-marshall itself needs one for markdown and one for Python.
   The edge set is the union across active resolvers (PLAN-02 D1/D2, PLAN-04 D1).
2. **Every result names the resolver that produced it** — the anti-vacuity property; a zero-edge
   answer must distinguish *no resolver ran* from *ran and found nothing* (PLAN-02 D3).
3. **Configuration at `marshall-steward`, persisted machine-locally** in
   `.plan/local/run-configuration.json` (PLAN-09).
4. **API adapted to LSP structure** to simplify usage (PLAN-08).

## Documentation contract (binds every plan in this epic)

**Docs ship WITH the change, never in a follow-up plan.** Doc-contract divergence is a recorded
recurring defect in this repository, and a docs-later plan is precisely how it recurs. Every
architectural plan therefore carries an explicit documentation deliverable naming its target pages.

- **`doc/concepts/`** — ⭐ **no page covers the code-intelligence substrate today** (verified: the 21
  pages include `extension-architecture`, `build-management`, `tools-and-scripts`, none on code
  intelligence). **PLAN-02 owns the new page**; later plans extend it rather than each inventing one.
- **`doc/developer/`** — mechanism and migration: the old→new verb mapping (PLAN-08), the protocol
  decision (PLAN-07), gate status (PLAN-06).
- **`doc/user/`** — operator-facing: search (PLAN-03), configuration (PLAN-09, extending the existing
  `doc/user/configuration.adoc`), consumer-project benefit (PLAN-05), editor setup (PLAN-07).

⚠ The per-plan deliverable is authored **in each spec**, not here — an emitted command is a one-line
pointer, so a charter-only obligation would never reach the executing plan.

## Sequencing and Surface Notes

- **PLAN-02 is the gate**: PLAN-08, PLAN-04, PLAN-05 and PLAN-09 all depend on it. ⭐ It also gates
  the docs, since it creates the `doc/concepts/` page the others extend.
- ⚠ **PLAN-02 ↔ PLAN-08 co-design risk**: PLAN-08 reshapes the same query surface PLAN-02 wires the
  seam into. If the reshape changes the seam's return contract, **co-design or merge them** rather
  than sequencing — building the query layer twice is the failure mode.
- ✅ **PLAN-04, PLAN-05 and PLAN-09 are mutually surface-disjoint** (`pm-plugin-development` ·
  `build-*` bundles · `marshall-steward`+`manage-run-config`) and MAY all run concurrently once
  PLAN-02 lands — a full `parallelization_scope = 3` wave.
- ⚠ **PLAN-09 is best paired with PLAN-04/PLAN-05, not run before them**: landing a configuration
  menu when only the Maven resolver exists is technically correct and practically untestable.
- ⛔ **PLAN-04 collides with WS-03's PLAN-06 and WS-01's PLAN-01** on `tools-marketplace-inventory`.
- ⛔ **PLAN-02 and PLAN-08 collide with WS-01's PLAN-01 and PLAN-03** on `manage-architecture`.
- ⚠ **PLAN-09 touches `manage-run-config`**, a widely-consumed core skill — check the sibling epic's
  queue before emitting.
- ⚠ **Granularity distinction, do not conflate**: PLAN-04's Python resolver derives **file-level
  import** edges inside the marketplace tree; PLAN-05's Python resolver derives **module-level
  package-coordinate** edges for consumer projects. Different granularity, different bundle, both
  legitimately called "the Python resolver".
- ⚠ **The layering rule the operator set, and it binds every plan here**: the resolver
  IMPLEMENTATION lives in the domain bundle (`pm-plugin-development` for the marketplace domain, the
  `build-*` bundles for their coordinate schemes). Core owns ONLY the seam. A core module reaching
  into a domain bundle would invert the dependency direction the extension-point contract exists to
  prevent.
