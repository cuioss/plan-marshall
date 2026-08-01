# Extension Point: Path Attribution

> **Type**: Path-to-Module Ownership (Axis-D) | **Hook Method**: `PathAttributionBase` subclass | **Implementations**: see [§ Current implementations](#current-implementations) | **Status**: Shipped — the `extension_base.py` ABC is wired and `plan-marshall-plugin` implements it

## Overview

A **path attributor** answers one question: which module owns this path. It contributes `(path_prefix, module_name)` claims that become the ownership map behind `which-module`'s rung-3 resolution and behind `resolve_module_for_path`, the helper the change-footprint classifiers call once per changed path.

Path attribution is an extension point rather than core logic because there is no domain-neutral way to derive it. The `plan-marshall` bundle knows that `.plan/**` and `.claude/skills/**` are its own; a documentation bundle knows what `doc/**` is; a build bundle knows which tree its production sources live in. Each is domain knowledge owned by the bundle that already understands that tree. Core owns the merge, the provenance, and the resolution order; it owns none of the claims.

**Ownership is not build routing.** Axis-D answers "which module *owns* this path". Axis-B (`classify_globs` / `classify_build_class`, see [extension-contract.md](extension-contract.md) § BuildExtensionBase Methods) answers "what build does a changed file *trigger*". The two vocabularies are deliberately separate: a path may be owned by a module that triggers no build, and a `build_map` route is a `(pattern, role)` fnmatch glob while a path claim is a literal directory prefix. Neither table feeds the other.

## Mechanism choice: a sibling Axis-D ABC

`PathAttributionBase` is a **standalone ABC declared alongside** `ExtensionBase`, `BuildExtensionBase` and `DerivationResolverBase` in `extension_base.py`, opted into by multiple inheritance. It is deliberately NOT either of two nearby designs:

- **NOT a face on `ExtensionBase` or `BuildExtensionBase`.** The legitimate implementor population straddles both hierarchies. `build-pyproject` knows that `marketplace/bundles/*.py` is its production surface (Axis-B); `pm-documents` knows what `doc/**` is (Axis-A); the `plan-marshall` bundle knows that `.plan/**` and `.claude/skills/**` are its own (Axis-A). Declaring the capability as a face on either existing ABC would structurally exclude the other side — the containment failure [ADR-013](../../../../../../doc/adr/013-A_capability_spanning_both_extension_hierarchies_lives_in_a_sibling_ABC_not_a_face_on_either.adoc) names as invisible at the declaration site.
- **NOT a face on `DerivationResolverBase`.** Axis-C answers "which modules depend on which". "Which module owns this path" is a different question with a different return type, and bolting it on would give one ABC two unrelated contracts.

The resolution is a fourth axis. `PathAttributionBase` inherits from none of the other three and is inherited by none, so an implementor from **either** hierarchy opts in by multiple inheritance:

```text
ExtensionBase (Axis-A)     BuildExtensionBase (Axis-B)    PathAttributionBase (Axis-D)
  skill loading              file-to-build map              path-to-module ownership
  get_skill_domains()        classify_paths()               path_attributor_id()
  provides_triage() ...      classify_globs() ...           claim_paths()
        ▲                            ▲                                ▲
        │                            │                  opted into by EITHER hierarchy
   plan-marshall-plugin         build-pyproject ────────────────────────┘
   pm-documents                 build-maven
```

This follows the precedent [ext-point-derivation-resolver.md](ext-point-derivation-resolver.md) sets for a cross-hierarchy capability, and the carve-out precedent `BuildExtensionBase` itself established when Axis-B was split out of `ExtensionBase`.

## The four contract faces

### 1. Declaration

An attributor subclasses `PathAttributionBase` and implements both methods. Because the ABC has no abstract method (both carry safe defaults), a subclass that overrides nothing is a valid no-claim attributor.

```python
from extension_base import ExtensionBase, PathAttributionBase


class Extension(ExtensionBase, PathAttributionBase):
    def path_attributor_id(self) -> str:
        """Stable provenance identity stamped onto every claim this attributor produces."""
        return 'plan-marshall'

    def claim_paths(self) -> tuple[list[tuple[str, str]], list[str]]:
        """Return ``(claims, notes)`` — ``(path_prefix, module_name)`` pairs plus suppression notes."""
        return [('.claude/skills', 'plan-marshall'), ('.plan', 'plan-marshall')], []
```

| Method | Default | Contract |
|--------|---------|----------|
| `path_attributor_id()` | `''` | A short, stable, lower-case identity. It is stamped into every merged claim's `producers[]` and names the attributor on the per-attributor report. An empty id marks the attributor unidentifiable and discovery skips it — a producer-less claim is never emitted. |
| `claim_paths()` | `([], [])` | Returns `(claims, notes)`. `claims` is a list of `(path_prefix, module_name)` pairs where `path_prefix` is a repo-relative directory prefix and `module_name` is the owning module. `notes` is a list of short strings describing conditions that **suppressed** a claim. |

An attributor is a **pure function of its arguments**: no subprocess, no filesystem access. It declares what its bundle owns from static knowledge; it never scans the tree to discover it.

**Why `notes[]` rides the `claim_paths` return** rather than a separate accessor: a second method readable only after `claim_paths` had run would be temporally coupled to it, and an attributor is otherwise a pure function of its arguments. Pairing the two in one return keeps the attributor stateless.

### 2. Discovery

Attributors are discovered by `discover_path_attributors()` in `extension_discovery.py`, a collector spanning **both** existing discovery paths — `discover_all_extensions()` (Axis-A implementors) and `discover_build_extensions()` (Axis-B implementors) — filtered by `isinstance(obj, PathAttributionBase)`. Because the opt-in is multiple inheritance from either hierarchy, both paths must be spanned; scanning only one would silently hide every attributor on the other side.

There is **no new registry, no new scan surface, and no per-attributor glob**. An attributor is discovered because its bundle is already a registered extension that happens to also subclass `PathAttributionBase`. Results are returned sorted by attributor id for deterministic downstream ordering. An attributor whose `path_attributor_id()` raises, returns a non-string, returns empty, or duplicates an already-seen id is skipped with an `[EXTENSION]` WARNING, matching the existing per-hook guarded-call idiom.

### 3. Dispatch

Attributors are dispatched at **query time**, not at discovery time. The caller collects the known module names once, then hands the discovered attributors to the merge:

```text
merge_path_claims(attributors, module_names)
    → (claims, attributor_reports)

lookup_claim(path, claims)
    → module_name | None
```

`merge_path_claims` is core-owned and produces the claim set; `lookup_claim` is the single shared matcher both consuming call sites use, so neither re-derives the containment predicate. The merge result is memoized at process lifetime by the consuming caller — the seam replaces what was an O(1) constant scan on a helper called once per changed path, so an unmemoized seam would run discovery and merge once per path.

### 4. Null-on-absent resolution

Zero registered attributors is a **first-class, non-error outcome**. The merge returns zero claims, `attributor_count: 0`, and an empty `attributors[]` — never an exception and never a fabricated claim. `lookup_claim` returns `None`, and the consuming verb returns its normal success payload with `module: null`.

This is the null-on-absent contract every extension point in this API shares: a capability no bundle provides is invisible, and its absence asserts no positive property. The two states MUST be distinguishable without inspecting the claim list:

| Response | Meaning |
|----------|---------|
| `attributor_count: 0`, `module: null` | **No attributor ran.** The unattributed path is an absence of capability, not a finding. |
| `attributor_count: N`, `module: null` | **N attributors ran and none claimed this path.** The unattributed path is a real, positive answer. |

This is the same fail-closed reporting discipline [ADR-009](../../../../../../doc/adr/009-Status_reporting_fails_closed_with_an_explicit_unknown_state.adoc) establishes and that the `find` / `which-module` verbs already apply via their `truncated` / `elided` flags.

## Keyed-mapping merge semantics

A path claim is a **keyed mapping**: the identity is the normalized path prefix (`rstrip('/')`), and the value is the claimed module. This is materially different from the Axis-C edge set, where an edge is an unweighted boolean and therefore no conflict is expressible. Here a value exists to disagree about, so a conflict **is** expressible, and the merge needs a rule for it:

| Case | Axis-C edge analogue | Path-attribution resolution |
|------|----------------------|-----------------------------|
| Same normalized prefix, same module, two attributors | Duplicate identity = corroboration | Collapse to ONE claim, `producers[]` = sorted ids of both |
| Same normalized prefix, **different** module | *No analogue — not expressible for edges* | Emit **no** claim for that prefix, report the collision in `notes[]` |
| Different-length prefixes, both containing the path | n/a | **Not** a collision — longest prefix wins, deterministically (see § below) |

The merge applies three validity filters of its own before the union — a malformed claim candidate, a blank or root-ish prefix, and a claim naming a module absent from `module_names`. Each such drop is core suppressing a claim, so each appends its own note to that attributor's report, prefixed `merge:` so a reader can tell a core-side drop from an attributor-side one. An attributor whose candidates were all discarded would otherwise report `status: ok`, `claim_count: 0` and an empty `notes[]`: a confident zero that reads exactly like "ran and legitimately found nothing".

An attributor that raises reports `status: error` with `claim_count: 0` and contributes no claims; its siblings still contribute. An errored attributor never aborts the merge. Claims are returned sorted by `(prefix, module)` for byte-stable output, and every claim carries a non-empty `producers[]`.

## The ambiguous-ownership obligation

When **two attributors claim the same normalized prefix and name different modules**, the merge:

1. MUST NOT resolve the disagreement by iteration order. A last-write-wins dict assignment silently drops one module's claim, and which module survives depends on discovery ordering — a non-deterministic answer presented as a confident one.
2. Emits **no claim** for the colliding prefix. Both claims are well-formed and mutually exclusive assertions of ownership over the same tree; core has no basis for preferring either, and a path whose ownership is genuinely disputed is better reported as unattributed than attributed to an arbitrary winner.
3. **Reports the collision** in `notes[]` naming both modules, so it rides the attributor reports into the response. A disputed prefix thereby stays distinguishable from an unclaimed one — a `module: null` accompanied by a collision note is a different answer from a bare `module: null`.

The rationale here is **not** the Axis-C one. [ext-point-derivation-resolver.md](ext-point-derivation-resolver.md) § "The ambiguous-identity-key obligation" abstains because an ambiguous *reference* cannot be attributed from the key alone and guessing is worse than abstaining. Here nothing is ambiguous at the attributor: two bundles have each made a definite, well-formed ownership claim, and they contradict each other. The abstention is not a refusal to guess an unknown — it is a refusal to arbitrate a declared conflict that only the bundles' owners can resolve.

## Longest prefix is resolution order, not a tie-break

`lookup_claim(path, claims)` resolves a path to the **longest claimed prefix that contains it**. This is core's resolution *order*, not a tie-break over a collision: `.plan` claimed by one module and `.plan/local` claimed by another is a perfectly well-formed claim set with no ambiguity, and a path under `.plan/local` resolves to the latter while `.plan/marshal.json` resolves to the former. Do not read longest-prefix-wins as the resolution for the middle row of the merge table above — that row emits no claim at all, so there is nothing left for the lookup to order.

Containment is **prefix nesting, not fnmatch**:

```text
path == prefix  or  path.startswith(prefix + '/')
```

The trailing-separator half is the **nest-inside guard**. A path belongs to a claim only when it nests inside the claimed directory, so `.plans/x` does NOT resolve through a `.plan` claim even though it shares the string prefix. An fnmatch `**/`-shaped pattern is the wrong tool here for the mirror-image reason: a single `*` spans `/` in `fnmatch`, and a `**/`-prefixed glob would fail to match the bare root segment `.plan` itself.

## Current implementations

| Attributor | Id | Owner | Claims |
|------------|-----|-------|--------|
| Plan Marshall core tree | `plan-marshall` | `plan-marshall-plugin` (`Extension(ExtensionBase, PathAttributionBase)`) | `.claude/skills → plan-marshall`, `.plan → plan-marshall`. The first is the re-homed form of the project-local prefix map that previously lived inline in `manage-architecture`; the owner is carried over unchanged. The second closes the `module: null` answer every `.plan/` script path previously received. |

**Out of scope for this contract's current implementations** — named so the table reads as the complete shipped set rather than an open-ended promise:

- **`doc/resources/**` attribution** — `doc/resources/diagrams/*.svg` currently resolves to no module while its sibling `doc/concepts/*.adoc` files resolve to `documentation`. Whether a third claim is warranted is not settled here.
- **Whether `.claude/skills/**` belongs to `pm-plugin-development`** rather than to `plan-marshall` — the re-homing preserved the existing owner and is not a fresh ownership ruling.
- **Build-side attributors** — no `BuildExtensionBase` subclass ships a claim yet, though the discovery collector already spans that hierarchy.

None of the three requires a change to this contract.

## Related Specifications

- [extension-contract.md](extension-contract.md) — The core extension-hook contract; registers this extension point in the Extension Points table and carries the `PathAttributionBase` Methods (Axis-D) section.
- [ext-point-derivation-resolver.md](ext-point-derivation-resolver.md) — The Axis-C sibling this contract's four-face shape follows, and whose union semantics § "Keyed-mapping merge semantics" above contrasts against.
- [ext-point-domain-bundle.md](ext-point-domain-bundle.md) — The domain-bundle manifest archetype every Axis-A attributor is discovered through.
- [client-api.md](../../manage-architecture/standards/client-api.md) — The `which-module` response contract that surfaces `attributors` / `attributor_count` and the four-rung resolution order this seam occupies at rung 3.
- [ADR-013](../../../../../../doc/adr/013-A_capability_spanning_both_extension_hierarchies_lives_in_a_sibling_ABC_not_a_face_on_either.adoc) — The containment test that makes this capability a sibling axis rather than a face on an existing ABC.
- [ADR-014](../../../../../../doc/adr/014-An_aggregation_over_N_independent_producers_carries_producer_identity_and_no_producer_suppresses_an_element_silently.adoc) — The provenance-and-no-silent-suppression decision the merge semantics and the ambiguous-ownership obligation implement.
