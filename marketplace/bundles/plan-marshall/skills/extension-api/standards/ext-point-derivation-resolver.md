# Extension Point: Derivation Resolver

> **Type**: Module-Edge Derivation (Axis-C) | **Hook Method**: `DerivationResolverBase` subclass | **Implementations**: see [§ Current implementations](#current-implementations) | **Status**: Shipped — the `extension_base.py` ABC is wired and implementors exist on both hierarchies

## Overview

A **derivation resolver** answers one question: which modules depend on which. It contributes `(from, to)` module-name pairs that become the edge set behind the `graph` / `path` / `neighbors` / `impact` query family and the adjacency surfaces of `overview` and `module` / `info`.

Edge derivation is an extension point rather than core logic because there is no domain-neutral way to derive it. A Maven reactor derives edges from `groupId:artifactId` coordinates, a documentation tree from cross-document references, a Python package from import statements — each is domain knowledge owned by the bundle that already understands that data. Core owns the merge, the provenance, and the traversal; it owns none of the derivation.

Which of the discovered resolvers actually run is a **machine-local** decision, bound by resolver id in the run-configuration store — see [§ Which resolvers run](#which-resolvers-run-the-machine-local-activation-binding). An unconfigured project runs them all.

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
  provides_triage() ...         classify_globs() ...              derive_edges() ...
        ▲                              ▲                                  ▲
        │                              │                                  │
   pm-plugin-development          build-maven                    opted into from EITHER
   pm-dev-python                  build-pyproject                hierarchy, by multiple
   pm-documents                                                  inheritance
```

The Axis-A and Axis-B bundle names illustrate what each hierarchy is for; which of them currently also subclass `DerivationResolverBase` is enumerated once, in [§ Current implementations](#current-implementations).

This follows the precedent [ext-point-domain-verb.md](ext-point-domain-verb.md) sets — an optional hook and a standalone contract doc are complements, not alternatives — and the carve-out precedent `BuildExtensionBase` itself established when Axis-B was split out of `ExtensionBase`.

## The four contract faces

### 1. Declaration

A resolver subclasses `DerivationResolverBase` and implements the two methods that carry its derivation; a third declares its file domain for display. Because the ABC has no abstract method (all three carry safe defaults), a subclass that overrides nothing is a valid no-edge resolver.

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
| `derivation_file_patterns()` | `[]` | Glob patterns naming the files this resolver derives from. **Descriptive metadata, never a filter** — it answers "active over which files?" on the configuration menu, read from the resolver that owns the answer rather than transcribed into a menu document. The default `[]` asserts nothing: a resolver declaring no patterns is reported *not declared*, not as deriving from no files. |

A resolver is a **pure function of its arguments**: no subprocess, no filesystem access. Both maps are pre-loaded by the caller and keyed by module name, so a resolver never re-derives module discovery.

**Why `notes[]` rides the `derive_edges` return** rather than a separate accessor: a second method readable only after `derive_edges` had run would be temporally coupled to it, and a resolver is otherwise a pure function of its arguments. Pairing the two in one return keeps the resolver stateless.

### 2. Discovery

Resolvers are discovered by `discover_derivation_resolvers()` in `extension_discovery.py`, a collector spanning **both** existing discovery paths — `discover_all_extensions()` (Axis-A implementors) and `discover_build_extensions()` (Axis-B implementors) — filtered by `isinstance(obj, DerivationResolverBase)`. Because the opt-in is multiple inheritance from either hierarchy, both paths must be spanned; scanning only one would silently hide every resolver on the other side.

There is **no new registry, no new scan surface, and no per-resolver glob**. A resolver is discovered because its bundle or build skill is already a registered extension that happens to also subclass `DerivationResolverBase`. Results are returned sorted by resolver id for deterministic downstream ordering. A resolver whose `derivation_resolver_id()` raises or returns empty is skipped with an `[EXTENSION]` WARNING, matching the existing per-hook guarded-call idiom.

**One registration site registers at most one resolver**, and the site differs by axis:

| Axis | Registration site | Open to | Resolution |
|------|-------------------|---------|------------|
| A | One per **bundle** | **Any bundle.** `discover_all_extensions()` scans every bundle directory. | The bundle's single `extension.py` — the manifest skill's sibling, located by the `implements:` archetype declaration. |
| B | One per **build skill** | **`plan-marshall` only** (see below). | `get_build_extension_paths()` iterates the hard-coded `_BUILD_EXTENSION_SKILLS` tuple under `resolve_skills_root(Path(__file__))` and keys each on its **skill** name. Discovery is name-driven, not a tree scan. |

The cardinality is structural, not a convention: `derivation_resolver_id()` returns a single string, so each registration site has exactly one resolver identity to stamp. Two derivations that must stay distinguishable in `producers[]` therefore have to live at two **sites** — two bundles on Axis-A, or two build skills on Axis-B.

Do not read this as "one resolver per bundle". The `plan-marshall` bundle alone contributes three Axis-B resolvers — `maven`, `npm` and `pyproject` — from its `build-maven`, `build-npm` and `build-pyproject` skills. That is what the per-skill keying is for: a build system's edge derivation belongs beside the rest of that build system's knowledge, not pooled into one resolver per bundle.

⚠ **Axis-B registration is closed; Axis-A is open.** `_BUILD_EXTENSION_SKILLS` is a fixed tuple and the paths resolve under **`plan-marshall`'s own** skills root, so a third-party bundle cannot register an Axis-B resolver by shipping a build skill — adding one means editing that tuple in `extension_discovery.py`. A bundle outside `plan-marshall` that wants to contribute edges registers on **Axis-A** instead, by subclassing `DerivationResolverBase` alongside `ExtensionBase` on its own `extension.py`, which is exactly how `markdown`, `python` and `documentation` are registered.

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

**Declared dependencies take precedence over derived ones.** After the merge, core discards a module's resolver-derived edges entirely when that module carries a **non-empty** declared `internal_dependencies` — from the `enriched.json` curated overlay, else from the crawl-time `derived.json` — and stamps that module's edges `declared` rather than with the contributing resolver ids. An **empty** `internal_dependencies` is not a declaration: `architecture init` seeds an empty list into every module, so an empty container is indistinguishable from unset, carries no assertion, and suppresses nothing. Every declared-wins discard is reported on the losing resolver's report, prefixed `declared:` (see [§ Suppression must be reported, never silent](#suppression-must-be-reported-never-silent)), so a resolver author can distinguish "a declaration overrode my edges" from "my derivation produced none".

### 4. Null-on-absent resolution

Zero registered resolvers is a **first-class, non-error outcome**. The merge returns zero edges, `resolver_count: 0`, and an empty `resolvers[]` — never an exception and never a fabricated edge. The consuming graph-family verb returns its normal success payload with an empty result.

This is the null-on-absent contract every extension point in this API shares: a capability no bundle provides is invisible, and its absence asserts no positive property.

## N-resolver union semantics

Several resolvers are active at once and the graph is the **union** of their edge sets. No conflict rule exists because none is expressible: an edge is an unweighted `(from, to)` boolean, so union is idempotent and commutative.

The nearest thing to a conflict is duplicate **identity**, not duplicate value: the `markdown` resolver deriving an edge from a cross-document reference and the `python` resolver deriving the same module pair from an import statement have not disagreed — they have independently corroborated. That case resolves by collapsing the duplicates into one edge carrying both producer ids, which is also exactly what the provenance contract needs. This is the common case rather than a hypothetical one: on the plan-marshall marketplace every edge the `python` resolver derives is also derived by `markdown`, so per-edge provenance is the only thing that keeps the import join's contribution visible at all.

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

The obligation binds **core as well as the resolver**. The merge applies three validity filters of its own — a malformed candidate pair, a self-edge, an endpoint naming no known module — and each of those is core suppressing an edge. Every such drop appends its own note to that resolver's report, prefixed `merge:` so a reader can tell a core-side drop from a resolver-side one. A resolver whose candidates were all discarded by the merge would otherwise report `status: ok`, `edge_count: 0` and an empty `notes[]`: a confident zero that reads exactly like "ran and legitimately found nothing".

The declared-wins precedence branch (see [§ 3 Dispatch](#3-dispatch)) is the second core-side suppression and discharges the same obligation with its own `declared:` prefix. Its notes are appended AFTER the merge returns, so a resolver's `edge_count` still counts what it derived while the report says which of those edges a declaration then overrode.

### The ambiguous-identity-key obligation

A resolver keys its derivation on some identity — a Maven `groupId:artifactId` coordinate, a document path, a package name. When **two distinct module names claim the same identity key**, the resolver:

1. MUST NOT resolve the collision by insertion order. A plain last-write-wins dict assignment silently drops one module and every edge pointing at it, and which module survives depends on map iteration order — a non-deterministic answer presented as a confident one.
2. Emits **no edge** for the colliding key. A genuinely ambiguous reference cannot be attributed to a single module from the key alone, and guessing is worse than abstaining.
3. **Reports the collision** in `notes[]`, so it rides the resolver's report into the response. A genuinely ambiguous key thereby stays distinguishable from an absent one — the same anti-vacuity principle applied one level down.

This obligation is stated generically because it binds every resolver, not only Maven. The markdown resolver facing two documents that claim the same anchor, and the python resolver facing two modules that export the same package name, are bound by the identical rule. Both discharge it upstream: the `component_refs` materialization projects each reference onto a single owning bundle and stamps whether it resolved, so an unresolvable reference reaches the resolver already marked rather than being guessed at — and each resolver drops it and reports it under the `unresolved-target` category.

## Which resolvers run: the machine-local activation binding

Discovery answers which resolvers **exist**. A separate, machine-local binding answers which of them
**run** in a given checkout: the `derivation_resolvers` section of the run-configuration store, keyed
on the resolver **id**. See
[`manage-run-config/standards/run-config-standard.md`](../../manage-run-config/standards/run-config-standard.md)
§ "Derivation-Resolvers Section" for the schema and the operator verbs.

The binding is machine-local rather than version-controlled because resolver availability and cost
are machine-local facts — the `lsp` resolver's harvest needs a language server on `PATH` — so the
same project can legitimately have a different active set on two machines. It lives beside the
`language_servers` binding in that one store, not in a parallel one.

**The key is the id, and it could not be a file pattern.** A resolver is handed module maps and
returns `(module, module)` pairs carrying no file provenance, so there is no point in the dispatch at
which a per-file binding could be applied and no edge attribute to match one against. Resolvers scope
themselves by build system (`maven`, `npm`, `pyproject`), by module kind (`documentation`), by
`component_refs` dep type (`markdown`, `python`), and by language (`lsp`) — none by a pattern an
operator supplies. `derivation_file_patterns()` reports the file domain for display; it does not
select on it.

**Absent configuration means active.** A discovered resolver is dispatched unless an entry explicitly
disables it, and every read failure fails open. The inverse default was rejected rather than merely
not chosen: resolvers that ran only once configured would leave a fresh checkout with an empty edge
set — the zero-edge outcome this extension point exists to prevent, arriving as a configuration
failure instead of a derivation one.

**A disabled resolver is reported, not pruned — but it is not counted as having run.** It still
appears in `resolvers[]` with `edge_count: 0`, a `configuration:` note, and the extra key
`dispatched: false` (whose absence marks the ordinary dispatched case).
`resolver_count` counts only `dispatched` records, so an envelope with every resolver switched off
reports `resolver_count: 0` — which is the truth ("no resolver ran"), keeps the anti-vacuity
discriminator's meaning intact, and stops `capabilities` from reporting `module_edges` as `derivable`
on a registered-but-unrun producer. Dropping the record entirely would instead make "switched off by
the operator" indistinguishable from "never registered" — precisely the vacuity
[§ The anti-vacuity provenance property](#the-anti-vacuity-provenance-property) forbids, and the same
reasoning [§ Suppression must be reported, never silent](#suppression-must-be-reported-never-silent)
applies to merge-side drops.

**No precedence knob exists, because none is expressible.** Configuration decides *whether* a
resolver runs, never how its edges rank against another's: the graph is the union (see
[§ N-resolver union semantics](#n-resolver-union-semantics)), edges are unweighted booleans, and two
resolvers deriving one pair have corroborated rather than disagreed. The single real precedence is
**declared-over-derived**, which core owns (see [§ 3 Dispatch](#3-dispatch)) and configuration cannot
override.

## Current implementations

Resolvers are shipped on both hierarchies — some opting in from Axis-A (`ExtensionBase`), some from Axis-B (`BuildExtensionBase`) — so the discovered set exercises the span-both-hierarchies property the collector exists for. The table below is the one place the shipped roster is enumerated.

| Resolver | Id | Axis | Owner | Role |
|----------|-----|------|-------|------|
| Maven coordinate join | `maven` | B | `build-maven` (`BuildExtension(BuildExtensionBase, DerivationResolverBase)`) | Derives edges by joining each module's `metadata.group_id` / `artifact_id` coordinate against every module's `dependencies` strings (`groupId:artifactId:scope`, matched on the first two parts). The re-homed form of the coordinate join that previously lived inline in `manage-architecture`. It is the first producer of `notes[]`: two modules sharing one `groupId:artifactId` yield no edge for that coordinate and a reported collision. Gradle modules are joined by this same resolver, since Gradle discovery publishes the same coordinate pair — see [§ Gradle rides the Maven join](#gradle-rides-the-maven-join). |
| Python distribution-name join | `pyproject` | B | `build-pyproject` (`BuildExtension(BuildExtensionBase, DerivationResolverBase)`) | Derives edges by joining each module's PEP 621 `[project] name` (carried on `metadata.name`) against every module's `dependencies` strings (`name:scope`), compared in PEP 503 normalised form so the `-`/`_`/`.`/case variants of one distribution resolve to the same module. Scoped to modules the Python build system discovered — see [§ A name join must be build-system scoped](#a-name-join-must-be-build-system-scoped). |
| npm package-name join | `npm` | B | `build-npm` (`BuildExtension(BuildExtensionBase, DerivationResolverBase)`) | Derives edges by joining each module's `package.json` name (carried on `metadata.name`) against every module's `dependencies` strings (`name:scope`), case-folded. Scoped names (`@scope/pkg`) join unchanged — the scope is part of the name, not a coordinate segment — and workspace members need no special case, since discovery already resolves the `workspaces` globs into one module per member and the `workspace:*` protocol never reaches the join. Scoped to modules the npm build system discovered. |
| Markdown cross-reference join | `markdown` | A | `pm-plugin-development` (`Extension(ExtensionBase, DerivationResolverBase)`) | Derives edges from the four markdown reference kinds — script notation, skill references, relative-path xrefs, and `implements:` — read out of the `component_refs` field `discover_modules()` materializes. Suppressions are reported in **aggregated** form, one note per category (unresolved-target, unknown-endpoint, self-edge) with a count and a bounded sample. |
| Python import join | `python` | A | `pm-dev-python` (`Extension(ExtensionBase, DerivationResolverBase)`) | Derives edges from AST-parsed Python imports, read out of the same `component_refs` field. Python-language knowledge belongs to the Python domain bundle rather than to a build-system bundle, which is why this resolver is Axis-A and not on `build-pyproject`. Same aggregated-notes discipline as the markdown resolver. |
| Language-server symbol join | `lsp` | A | `pm-code-intelligence` (`Extension(ExtensionBase, DerivationResolverBase)`) | Derives edges from symbol references a language server resolved with a real parser, read out of the `component_refs` field under the `lsp` dep type. The harvest is a discovery-time engine (`pm-plugin-development:plan-marshall-plugin:lsp_harvest`) that boots a server, drives it to completion in batch, and lifts its file-granular references to module granularity through the path-attribution seam; an endpoint no module owns yields no edge and a note rather than a guessed module. Unlike every sibling above, its producer is a subprocess that can fail, so the harvest's `lsp_harvest` status record rides each module and the resolver reports `ran: false` with a distinct stated reason — absent, failed to start, timed out, unsupported workspace — so a dead server never reads as a zero-edge success. **Off by default**: it runs only for a language carrying an enabled entry in the shared machine-local `language_servers` binding — the same binding `plan-marshall:lsp-client` reads, whose store is git-ignored, so a fresh clone boots no server. Enabling it trades Tier 0's subprocess-free property for the reference set. It also reuses that skill's LSP session rather than shipping a second client. |
| Documentation cross-reference join | `documentation` | A | `pm-documents` (`Extension(ExtensionBase, PathAttributionBase, DerivationResolverBase)`) | Derives edges from the doc corpus's `xref:` / `link:` / `include::` / markdown-link references, read out of the same `component_refs` field (materialized by the bundle's `doc_references` engine). Scoped to documentation modules, so it does not re-derive the marketplace-bundle references the `markdown` resolver owns; where both see one reference the merge unions them into one edge carrying both producer ids. Its `unresolved-target` note is the dangling-reference / deleted-heading class only the documentation domain detects. Same aggregated-notes discipline as the markdown resolver. |

**Each Axis-A resolver reads a pre-materialized field; none reads the filesystem.** The detection engine that produces `component_refs` parses files from disk, so it runs at module-discovery time. A resolver is a pure function of its arguments (see § 1 Declaration), which is why the engine cannot be called from `derive_edges`. No resolver imports another bundle's engine, so each registration stands alone — the roster creates no coupling between the owning bundles.

**Why the markdown, python, documentation, and lsp joins are separate resolvers, not one.** All four are Axis-A, where the registration site is the bundle (see [§ 2 Discovery](#2-discovery)), so the split across `pm-plugin-development`, `pm-dev-python`, `pm-documents`, and `pm-code-intelligence` is what makes per-edge provenance — was this edge a marketplace markdown reference, a Python import, a cross-document reference, or a parser-resolved symbol reference? — expressible at all. Collapsing them into one resolver would forfeit exactly that distinction.

That same one-per-bundle cardinality is what put `lsp` in its own bundle rather than on `pm-dev-python`, whose Python-language ownership would otherwise have made it the obvious host: a second resolver there would have been stamped `python`, and its parser-resolved edges would have become indistinguishable from the AST-import join's. Where both derive the same pair they have corroborated rather than disagreed, and the union preserves that only because the two ids stay distinct.

**Why `python` and `pyproject` are both registered, and both wanted.** They answer different questions over the same language. `python` (Axis-A, `pm-dev-python`) joins AST-parsed **import statements** — what the code actually reaches for — which is language knowledge. `pyproject` (Axis-B, `build-pyproject`) joins **declared distribution dependencies** — what the project says it depends on — which is build-system knowledge. The two disagree in both directions, and each disagreement is informative: a declared dependency nothing imports is a stale declaration, and an import with no declaration is a missing one. They also have different reach — `component_refs` is materialized only by the bundles that crawl a marketplace or doc corpus, so an ordinary Python consumer project gets its graph from `pyproject` alone. Per-edge provenance is what keeps the two distinguishable, which is why they are two registration sites — one Axis-A bundle and one Axis-B build skill — rather than one resolver.

### A name join must be build-system scoped

The Maven join is scoped by the *shape* of its key: only Maven and Gradle publish a `groupId:artifactId` pair, so a module from another ecosystem simply has no coordinate and cannot enter the map. A **name** join has no such natural scoping — a bare distribution/package name is a key shape every ecosystem uses — so `pyproject` and `npm` each filter `derived_by_name` to the modules their own `build_systems` entry names, at both ends of the join.

Without that filter a mixed repository breaks in two ways at once, and both were observed before the scoping existed:

1. **Provenance is misattributed.** The `npm` resolver derived all 11 edges of a pure-Python project, so every edge carried `producers: [npm, pyproject]` — asserting that the npm join found something it never looked at.
2. **Cross-ecosystem edges are fabricated.** A Python distribution and an npm package that merely share a name would be joined into an edge that exists in neither ecosystem.

The second is the more serious: the first misreports a true edge, while the second invents one.

### Neither name join falls back to the module name

A module's `name` is **not** an identity anything can depend on, and the two ecosystems reach that conclusion by different routes. For npm it is *sometimes* the published name: `_build_module` uses `package.json`'s `name` when there is one and falls back to the directory (or `default` at an unnamed root) when there is not, so the field cannot say which case it is in. For Python it is *never* the published name: `build_module_base` derives it from the directory (or `default` at the root) and never reads `[project] name` at all, so the module name and the distribution name are unrelated strings that merely often coincide.

Both name joins therefore read the published name from `metadata.name` and treat its absence as "publishes nothing" — such a module is never an edge **target**, though it remains a valid edge **source**, since it can still declare dependencies.

Falling back to the module name would invent a key the ecosystem never published, and could match an unrelated registry package that happens to share the directory's name. A fabricated edge is worse than the missing one it would paper over, which is the same reasoning the Maven join applies when it requires **both** `group_id` and `artifact_id` before admitting a coordinate.

An absent published name is deliberately **not** reported in `notes[]`. A directory that is a module but not a distribution — a scripts folder, an unnamed workspace root — is outside the join rather than suppressed by it, and reporting it would bury the genuine collisions the report exists to surface. The same applies to a dependency naming no known module: that is an **external** dependency, and it is the overwhelming majority of any real project's dependency list.

### Gradle rides the Maven join

Gradle needs no resolver of its own for the coordinate case. Its discovery publishes `metadata.group_id` / `metadata.artifact_id` exactly as Maven's does and emits `groupId:artifactId:compile` dependency strings, so the `maven` resolver joins Gradle modules unchanged — a second reference implementation of the coordinate join rather than a second implementor of it.

One Gradle form does **not** join, and is recorded here rather than fixed: an inter-project dependency (`implementation project(':core')`) is rendered by `gradle dependencies` as `+--- project :core` and extracted as `project:core:compile`. The join reads the first two colon-separated parts, so the key becomes the literal `project:core`, which matches no module's published coordinate. A Gradle build whose modules depend on each other by the idiomatic `project(...)` form therefore derives no internal edges, while one that depends by full coordinate derives them correctly.

Both halves are pinned by `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py`, which drives the real dependency parser into the real Maven resolver — so closing the limitation later fails a test rather than silently outdating this section.

## Related Specifications

- [extension-contract.md](extension-contract.md) — The core extension-hook contract; registers this extension point in the Extension Points table and carries the `DerivationResolverBase` Methods (Axis-C) section.
- [ext-point-domain-verb.md](ext-point-domain-verb.md) — The sibling-ext-point precedent this contract follows, including the "would force a non-build bundle to masquerade as a build system" category-error argument.
- [ext-point-build.md](ext-point-build.md) — The build-system extension point that owns `discover_modules()`, whose output populates the `derived_by_name` map a resolver reads.
- [ADR-004](../../../../../../doc/adr/004-The_file-to-build_contract_is_owned_by_build-system_extensions_not_languagecontent_domains.adoc) — The ownership split that keeps Axis-A and Axis-B un-entangled, and which this third axis preserves.
