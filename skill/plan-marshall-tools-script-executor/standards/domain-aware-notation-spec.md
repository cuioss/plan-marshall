# Specification: Domain-Aware Executor Notation Exposure

> **Status**: Specification only — NO implementation in this plan. This document specifies a *possible* domain-aware change to executor notation registration and records an explicit recommendation on whether to make it. Any change to `generate_executor.py` is a follow-up plan gated on this specification and on `ADR-010`.

## Scope and non-goals

`generate_executor.py` is a **deterministic generator** that materialises the `.plan/execute-script.py` proxy by embedding a `SCRIPTS` map — a `{bundle}:{skill}:{script}` → absolute-path table — built from the whole bundle inventory. The executor is **domain-blind by design today**: it registers every discovered bundle's scripts regardless of which domains a project has activated in `marshal.json`.

This document reasons about whether that should change: whether notation registration should become domain-aware, so that a notation belonging to an inactive domain is either absent from the generated proxy or resolves to a diagnosable inactive-domain refusal. It covers the migration path, the backward-compatibility story, the inactive-domain-notation failure mode (tied to `ADR-010`'s visibility decision), and an explicit recommendation — which includes recognising **"specify then decline"** as a legitimate, first-class outcome.

It does **not** implement any of this. `generate_executor.py`, its `SCRIPTS` map shape, and the regeneration surface (`/marshall-steward`, `preflight`) are unchanged by this plan.

## What "domain-aware notation" would mean

Under the domain-blind status quo, the generated `SCRIPTS` map is the union of every bundle's registered scripts. A `pm-dev-java:build-maven:maven` notation is present in a Python-only project's executor exactly as it is in a Java project's, because generation reads the bundle inventory, not the project's `skill_domains` registration.

A domain-aware generator would consult the per-project active-domain set (the per-project axis in `ADR-010`: `skill_domains.{key}` in `marshal.json` plus the discovered extension set) at generation time and gate each notation on whether its owning bundle's domain is active for the project. Two shapes are possible, and they correspond directly to `ADR-010`'s two visibility semantics:

| Shape | Generated-proxy effect | `ADR-010` visibility semantic |
|-------|------------------------|-------------------------------|
| **Invisible** | An inactive-domain notation is omitted from the `SCRIPTS` map entirely. A call to it fails with the generator's existing unknown-notation path (`unknown_notation`). | Invisible — the notation asserts no positive property when absent. |
| **Present-but-refusing** | An inactive-domain notation is kept in the map but resolves to a diagnosable inactive-domain refusal (a legible "domain not active for this project" error) rather than dispatching the script. | Present-but-refusing — a diagnosable refusal, never a silent success. |

## Migration path (if the change were made)

A migration from domain-blind to domain-aware registration would proceed:

1. **Additive generation input.** Extend `generate_executor.py` to read the project's active-domain set at generation time (the same `skill_domains` / `discover_all_extensions()` per-project axis every domain-aware surface already reads). Generation stays deterministic — the active-domain set is a pure function of `marshal.json` and the installed bundles.
2. **Gate at map-build time.** When building the `SCRIPTS` map, classify each notation's owning bundle by its domain and apply the chosen visibility semantic (omit for invisible; annotate for present-but-refusing). Core-bundle (`plan-marshall`) notations are never gated — they belong to the domain-agnostic core (the "deliberately not gated" machinery in `ADR-010`).
3. **Regeneration is the migration unit.** Because the executor is regenerated per project (`/marshall-steward`, and the `preflight` staleness path), the migration is picked up the next time a project regenerates. There is no in-place mutation of an existing executor and no cross-project coordination — each project's next regeneration adopts the new behaviour.
4. **Staleness signalling.** The existing `preflight` staleness machinery (`MARSHALL_VERSION` vs the installed `dist-manifest.json`) already forces regeneration on a version bump, so a domain-aware generator ships to every project through the normal staleness path without a bespoke migration step.

## Backward-compatibility story

- **Existing notations.** Every notation that resolves today continues to resolve for a project whose owning domain is active. The change is subtractive only for *inactive*-domain notations, which a correctly-configured project never calls.
- **Already-generated executors.** An executor generated before the change stays domain-blind until its project regenerates. Nothing breaks: a stale domain-blind executor is a strict superset of a domain-aware one (it registers more notations, not fewer), so every call that would succeed under the new behaviour still succeeds under the old.
- **Consumer repositories.** Consumer projects of plan-marshall carry their own generated executor. They adopt the change only on their next `/marshall-steward` run, and until then behave exactly as today. No consumer-side action is required, and no consumer executor is invalidated by the change landing in the marketplace.
- **Self-healing resolution.** The executor's self-healing path resolution (stale-embedded-path recovery, target-aware resolver, upward walk) is orthogonal to domain gating and is unaffected either way.

## Inactive-domain-notation failure mode

The failure mode a domain-aware executor must define is: *what happens when a notation is requested whose owning domain is inactive for the project.* This is where the specification binds directly to `ADR-010`'s visibility decision:

- Under the **invisible** semantic, the notation is simply absent from the `SCRIPTS` map, so the request hits the generator's existing `unknown_notation` path — indistinguishable from a genuinely non-existent notation. This is ADR-009-consistent because an absent notation asserts no positive property; it is a capability that was never provided.
- Under the **present-but-refusing** semantic, the notation resolves to a diagnosable inactive-domain refusal that names the inactive domain and the notation, so the caller learns *why* the call did not dispatch rather than seeing a generic unknown-notation error.

The choice between them follows `ADR-010`: notation dispatch is a capability-provision surface, not a status-bearing gate — a not-registered notation claims no positive verdict — so the invisible semantic is the ADR-consistent default *if the layer is gated at all*. The present-but-refusing semantic buys legibility (a clearer error) at the cost of keeping inactive-domain entries in every executor.

## Recommendation: decline executor-layer gating

**The recommendation is to DECLINE executor-notation-layer gating and keep the executor domain-blind**, deferring inactive-domain enforcement to resolve/dispatch time per `ADR-010`. This is a deliberate "specify then decline" outcome — a legitimate, first-class result of a specification: the design space is characterised in full above so a future plan can act on (or override) the decision, and the decision is to not build it.

The rationale:

- **Notation registration is a static build-time artifact, not a runtime gate.** The active-domain question `ADR-010` governs is answerable at resolve/dispatch time, where the domain-aware `resolve-*` verbs already live. Pushing enforcement into a build-time generator gates the *wrong layer*: it couples a regenerated-per-project artifact to per-project domain state it would have to re-embed, duplicating a check the dispatch layer already performs correctly.
- **The blast radius on this file is high.** Notation registration is load-bearing for every script call in the project, and the generator's path-resolution surface has historically been the source of more than one epic-scale defect — a worktree-basename resolution fault and a stale/multi-version embedded-path shadowing fault. Adding a domain-gating branch to the map-build path enlarges exactly the surface those defects came from, for a benefit the dispatch layer already delivers.
- **The domain-blind superset is safe.** A domain-blind executor registering a notation a project never calls costs nothing: an inactive-domain notation is simply never dispatched. There is no correctness or security gain from removing it from the map, because the enforcement that matters — refusing to *run* an inactive domain's capability — belongs at resolve/dispatch time, which `ADR-010` already assigns the diagnosable-refusal semantic to.
- **`ADR-010` already places this layer in the "deliberately not gated" set.** This recommendation is the executor-layer realisation of that decision: the executor stays domain-blind, and inactive-domain enforcement is the dispatch layer's job.

If a future plan overrides this recommendation, the migration path and backward-compatibility story above are the contract it would build against, and the **invisible** semantic is the `ADR-010`-consistent default it should adopt.

## Related Specifications

- `ADR-010` (`Domain content is active only when its domain is active`, `doc/adr/`) — the gating-axis, visibility, and "deliberately not gated" decisions this specification realises for the executor-notation layer.
- [SKILL.md](../SKILL.md) — the executor notation format, the `SCRIPTS` map, self-healing resolution, and the `generate_executor` regeneration surface this spec reasons about.
- [ext-point-domain-verb.md](../../extension-api/standards/ext-point-domain-verb.md) — the dispatch-time domain-owned-verb contract that owns inactive-domain enforcement this spec defers to.
