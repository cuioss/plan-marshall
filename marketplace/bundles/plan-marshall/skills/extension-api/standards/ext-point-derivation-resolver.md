# Extension Point: Derivation Resolver

> **Type**: Module-Edge Derivation (Axis-C) | **Hook Method**: `DerivationResolverBase` subclass | **Implementations**: 1 (`maven`) | **Status**: Shipped — the `extension_base.py` ABC is wired and `build-maven` implements it

## Overview

A **derivation resolver** answers one question: which modules depend on which. It contributes `(from, to)` module-name pairs that become the edge set behind the `graph` / `path` / `neighbors` / `impact` query family and the adjacency surfaces of `overview` and `module` / `info`.

Edge derivation is an extension point rather than core logic because there is no domain-neutral way to derive it. A Maven reactor derives edges from `groupId:artifactId` coordinates, a documentation tree from cross-document references, a Python package from import statements — each is domain knowledge owned by the bundle that already understands that data. Core owns the merge, the provenance, and the traversal; it owns none of the derivation.

The contract is **N-resolver by construction**: several resolvers are active at once and the graph is the union of their edge sets. The union needs no conflict rule — edges are unweighted booleans, so union is idempotent and commutative and no conflict is expressible (see § N-resolver union semantics).

## Mechanism choice: a sibling Axis-C ABC

`DerivationResolverBase` is a **standalone ABC declared alongside** `ExtensionBase` and `BuildExtensionBase` in `extension_base.py`, opted into by multiple inheritance. It is deliberately NOT either of two nearby designs:

- **NOT a face on `ExtensionBase`.** `ExtensionBase` is Axis-A (skill loading), subclassed by language and content domain bundles. `build-maven`'s `class BuildExtension(BuildExtensionBase)` does **not** inherit `ExtensionBase` — the two hierarchies are disjoint. A `provides_derivation_resolver()` hook on `ExtensionBase` would therefore be structurally unreachable from `build-maven`, which is exactly where the Maven coordinate join belongs: it consumes Maven `metadata.group_id` / `artifact_id` and the `groupId:artifactId:scope` dependency-string contract, and no other bundle owns that knowledge.
- **NOT a face on `BuildExtensionBase`.** Axis-B is the file-to-build map — "what build does a changed file trigger." Folding edge derivation into it would force a markdown resolver or a Python-import resolver to masquerade as a build system to declare edges, the same category error [ext-point-domain-verb.md](ext-point-domain-verb.md) § "Mechanism choice" rejects for executable verbs. It would also entangle two hierarchies [ADR-004](../../../../../../doc/adr/004-The_file-to-build_contract_is_owned_by_build-system_extensions_not_languagecontent_domains.adoc) deliberately keeps un-entangled.

The resolution is a third axis. `DerivationResolverBase` inherits from neither existing ABC and is inherited by neither, so an implementor from **either** hierarchy opts in by multiple inheritance:

```text
ExtensionBase (Axis-A)        BuildExtensionBase (Axis-B)      DerivationResolverBase (Axis-C)
  skill loading                 file-to-build map                 module-edge derivation
  get_skill_domains()           classify_paths()                  derivation_resolver_id()
  provides_triage() ...         classify_globs() ...              derive_edges()
        ▲                              ▲                                  ▲
        │                              │                    opted into by EITHER hierarchy
   pm-dev-python                  build-maven ─────────────────────────────┘
   pm-documents                   build-pyproject
```

This follows the precedent [ext-point-domain-verb.md](ext-point-domain-verb.md) sets — an optional hook and a standalone contract doc are complements, not alternatives — and the carve-out precedent `BuildExtensionBase` itself established when Axis-B was split out of `ExtensionBase`.

## The four contract faces

### 1. Declaration

A resolver subclasses `DerivationResolverBase` and implements both methods. Because the ABC has no abstract method (both carry safe defaults), a subclass that overrides nothing is a valid no-edge resolver.

```python
from extension_base import BuildExtensionBase, DerivationResolverBase


class BuildExtension(BuildExtensionBase, DerivationResolverBase):
    def derivation_resolver_id(self) -> str:
        """Stable provenance identity stamped onto every edge this resolver produces."""
        return 'maven'

    def derive_edges(
        self,
        derived_by_name: dict,
        enriched_by_name: dict,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        """Return ``(edges, notes)`` — ``(from, to)`` pairs plus suppression notes."""
        ...
```

| Method | Default | Contract |
|--------|---------|----------|
| `derivation_resolver_id()` | `''` | A short, stable, lower-case identity. It is stamped into every merged edge's `producers[]` and names the resolver on the per-resolver report. An empty id marks the resolver unidentifiable and discovery skips it — a producer-less edge is never emitted. |
| `derive_edges(derived_by_name, enriched_by_name)` | `([], [])` | Returns `(edges, notes)`. `edges` is a list of `(from, to)` module-name pairs where `from` depends on `to`. `notes` is a list of short strings describing conditions that **suppressed** an edge. |

A resolver is a **pure function of its arguments**: no subprocess, no filesystem access. Both maps are pre-loaded by the caller and keyed by module name, so a resolver never re-derives module discovery.

**Why `notes[]` rides the `derive_edges` return** rather than a separate accessor: a second method readable only after `derive_edges` had run would be temporally coupled to it, and a resolver is otherwise a pure function of its arguments. Pairing the two in one return keeps the resolver stateless.

### 2. Discovery

Resolvers are discovered by `discover_derivation_resolvers()` in `extension_discovery.py`, a collector spanning **both** existing discovery paths — `discover_all_extensions()` (Axis-A implementors) and `discover_build_extensions()` (Axis-B implementors) — filtered by `isinstance(obj, DerivationResolverBase)`. Because the opt-in is multiple inheritance from either hierarchy, both paths must be spanned; scanning only one would silently hide every resolver on the other side.

There is **no new registry, no new scan surface, and no per-resolver glob**. A resolver is discovered because its bundle is already a registered extension that happens to also subclass `DerivationResolverBase`. Results are returned sorted by resolver id for deterministic downstream ordering. A resolver whose `derivation_resolver_id()` raises or returns empty is skipped with an `[EXTENSION]` WARNING, matching the existing per-hook guarded-call idiom.

### 3. Dispatch

Resolvers are dispatched at **graph-query time**, not at discovery time. The caller loads the derived and enriched module maps once, then hands both to every discovered resolver and merges the results:

```text
merge_resolver_edges(resolvers, derived_by_name, enriched_by_name)
    → (edges, resolver_reports)
```

The merge:

1. Calls each resolver's `derive_edges`, unpacking `(edges, notes)`.
2. Drops any pair whose endpoints are not both known module names, and drops self-edges.
3. Unions the surviving pairs keyed on `(from, to)`. A pair produced by more than one resolver collapses to **one** edge whose `producers[]` is the sorted list of contributing resolver ids.
4. Returns edges sorted by `(from, to)` for byte-stable output, plus one `{id, edge_count, status, notes[]}` report per resolver.

A resolver that raises reports `status: error` with `edge_count: 0` and contributes no edges; its siblings still contribute. An errored resolver never aborts the merge.

### 4. Null-on-absent resolution

Zero registered resolvers is a **first-class, non-error outcome**. The merge returns zero edges, `resolver_count: 0`, and an empty `resolvers[]` — never an exception and never a fabricated edge. The consuming graph-family verb returns its normal success payload with an empty result.

This is the null-on-absent contract every extension point in this API shares: a capability no bundle provides is invisible, and its absence asserts no positive property.

## N-resolver union semantics

Several resolvers are active at once and the graph is the **union** of their edge sets. No conflict rule exists because none is expressible: an edge is an unweighted `(from, to)` boolean, so union is idempotent and commutative.

The nearest thing to a conflict is duplicate **identity**, not duplicate value: a markdown resolver deriving an edge from a cross-document reference and a Python resolver deriving the same module pair from an import statement have not disagreed — they have independently corroborated. That case resolves by collapsing the duplicates into one edge carrying both producer ids, which is also exactly what the provenance contract needs.

```text
              resolver A            resolver B            resolver C
              (maven)               (markdown)            (python)
                  │                     │                     │
            (core → util)         (core → util)          (api → core)
                  │                     │                     │
                  └──────────┬──────────┘                     │
                             ▼                                ▼
              {from: core, to: util,              {from: api, to: core,
               producers: [markdown, maven]}       producers: [python]}
```

## The anti-vacuity provenance property

Every edge names its producers and every graph-family response names the resolvers that ran. The property this buys:

| Response | Meaning |
|----------|---------|
| `resolver_count: 0`, `edges: []` | **No resolver ran.** The empty graph is an absence of capability, not a finding. |
| `resolver_count: N`, `edges: []` | **N resolvers ran and found nothing.** The empty graph is a real, positive answer. |

The two states MUST be distinguishable without inspecting the edge list. This is the same fail-closed reporting discipline [ADR-009](../../../../../../doc/adr/009-Status_reporting_fails_closed_with_an_explicit_unknown_state.adoc) establishes and that the `find` / `which-module` verbs already apply via their `truncated` / `elided` flags: a confident-looking answer must carry the evidence that makes it confident.

Two obligations follow for implementors:

- **Every edge carries a non-empty `producers[]`.** An edge core adds as post-resolution augmentation (sibling cross-links) is stamped with the reserved producer id `sibling-cross-link`, so no edge in any response is producer-less.
- **Every suppressed edge is reported.** See the next section.

## Suppression must be reported, never silent

The `notes[]` half of the `derive_edges` return is the **required channel** for any condition that suppressed an edge — an ambiguous identity key, an unresolvable reference, a malformed declaration. A resolver that drops an edge silently violates this contract.

`notes[]` defaults to `[]`, so a resolver that emits nothing is indistinguishable in shape from one that cannot emit. The field exists precisely because a condition that suppresses an edge must be visible somewhere; silently dropping it is the vacuity this extension point was built to eliminate.

### The ambiguous-identity-key obligation

A resolver keys its derivation on some identity — a Maven `groupId:artifactId` coordinate, a document path, a package name. When **two distinct module names claim the same identity key**, the resolver:

1. MUST NOT resolve the collision by insertion order. A plain last-write-wins dict assignment silently drops one module and every edge pointing at it, and which module survives depends on map iteration order — a non-deterministic answer presented as a confident one.
2. Emits **no edge** for the colliding key. A genuinely ambiguous reference cannot be attributed to a single module from the key alone, and guessing is worse than abstaining.
3. **Reports the collision** in `notes[]`, so it rides the resolver's report into the response. A genuinely ambiguous key thereby stays distinguishable from an absent one — the same anti-vacuity principle applied one level down.

This obligation is stated generically because it binds every resolver, not only Maven. A future markdown resolver facing two documents that claim the same anchor, or a Python resolver facing two modules that export the same package name, is bound by the identical rule.

## Current implementations

| Resolver | Id | Owner | Role |
|----------|-----|-------|------|
| Maven coordinate join | `maven` | `build-maven` (`BuildExtension(BuildExtensionBase, DerivationResolverBase)`) | Derives edges by joining each module's `metadata.group_id` / `artifact_id` coordinate against every module's `dependencies` strings (`groupId:artifactId:scope`, matched on the first two parts). The re-homed form of the coordinate join that previously lived inline in `manage-architecture`. It is the first producer of `notes[]`: two modules sharing one `groupId:artifactId` yield no edge for that coordinate and a reported collision. |

**Out of scope for this contract's current implementations** — named so the table reads as the complete shipped set rather than an open-ended promise:

- **Markdown resolver** (PLAN-04) — would derive edges from cross-document references. Not implemented.
- **Python resolver** (PLAN-05) — would derive edges from import statements. Not implemented.

Both are future implementors of this same contract; neither requires a change to it.

## Related Specifications

- [extension-contract.md](extension-contract.md) — The core extension-hook contract; registers this extension point in the Extension Points table and carries the `DerivationResolverBase` Methods (Axis-C) section.
- [ext-point-domain-verb.md](ext-point-domain-verb.md) — The sibling-ext-point precedent this contract follows, including the "would force a non-build bundle to masquerade as a build system" category-error argument.
- [ext-point-build.md](ext-point-build.md) — The build-system extension point that owns `discover_modules()`, whose output populates the `derived_by_name` map a resolver reads.
- [ADR-004](../../../../../../doc/adr/004-The_file-to-build_contract_is_owned_by_build-system_extensions_not_languagecontent_domains.adoc) — The ownership split that keeps Axis-A and Axis-B un-entangled, and which this third axis preserves.
