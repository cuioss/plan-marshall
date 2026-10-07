> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Give the persisted architecture store a concept model

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

The persisted architecture store is already **shaped** like a knowledge bundle — a directory of
per-module concept documents under a root index — but it carries none of the constructs that make
such a bundle answerable without reading all of it:

- concept documents have **no declared type**;
- their inner package entries use a **second identity system** — dotted pseudo-identifiers that
  resolve to no filesystem path, so two identity schemes must be kept in sync by hand;
- the root index maps module names to **empty objects**, carrying no descriptions, so it cannot serve
  as a pre-flight read that tells a consumer which documents to open;
- no concept records **who generated it, against which tree, or when it goes stale**. The only
  freshness signal is filesystem mtime, which this project has repeatedly ruled inadmissible as
  evidence.

Give the store a concept model: **path as identity**, a **required type**, a
**description-bearing index**, and **generation provenance keyed on the tree it was generated
against**. This is the substrate an LSP-shaped query API is meant to query, and the surface every
derivation resolver writes into.

**Design provenance, and its bounds.** The data model is adapted from a published open knowledge
format. ⛔ **Only the data model is adopted — not the serialization and not the conformance
posture.** The store stays JSON: its consumers are scripts, so a markdown-with-frontmatter
serialization would buy rendering nobody needs. And the source format's **leniency rules** (consumers
must tolerate broken links and unknown types) and its **no-central-type-registry stance** are
**explicitly rejected** — they invert the fail-closed detector posture and the closed-vocabulary
posture two sibling plans exist to defend.

## Goal

A consumer can tell what a concept document *is*, resolve its keys to real filesystem paths, choose
which documents to open from the index alone, and know whether a document was generated against the
tree it is now being read against — without parsing the document body.

## Deliverables

1. **D1 — path is identity.** Retire the dotted pseudo-identifiers in the package entries in favour
   of repo-relative paths, so a concept's key resolves to a real filesystem location and no second
   identity system needs keeping in sync. Migrate existing entries; **reject a non-resolving key at
   write time.**
   *Done when:* every persisted key resolves to a path, and a write with a non-resolving key is
   refused with a named error rather than accepted.
2. **D2 — a required `type` on every concept document.** A **closed, validated** vocabulary — not an
   open producer-defined one — so the store can hold more than modules (skill, script, standard,
   decision record) without standing up a parallel store. **An unknown type is refused at write
   time.**
   *Done when:* the vocabulary is enumerated in one place, an unknown type is refused, and the
   refusal names the accepted set.
3. **D3 — the root index carries per-module descriptions**, so a consumer can decide which concept
   documents to open instead of opening all of them.
   ⛔ **This MUST NOT reintroduce the index as the discovery gatekeeper** — see the verify-first
   claim below. Descriptions are a **read-side enrichment** of the index, never a **discovery-side
   filter**.
   *Done when:* the index carries descriptions and a module present on disk but absent from the index
   is still discovered.
4. **D4 — generation provenance and freshness.** Every concept document records who generated it, at
   what point, and **against which tree**; reads surface a staleness verdict derived from the tree
   identifier rather than from mtime.
   ⭐ The tree identifier is the stronger primitive than a wall-clock expiry: it answers *generated
   against which tree*, not merely *when*.
   ⛔ **The signal must be readable without parsing the concept body**, so a consumer can filter
   before loading.
   *Done when:* a document generated against a different tree is reported stale, one generated
   against the current tree is not, and neither check reads the body.

Four deliverables — below the split guard.

## Out of scope

- **The reasoning-field family** that conflates source citation with inference. Excluded
  deliberately; it stays an open defect in the epic rather than being folded in here, because
  separating citation from inference is a distinct design question and would push this plan past the
  split guard.
- **Markdown or frontmatter serialization.** Excluded: consumers are scripts, so it would buy
  rendering nobody needs and cost a parser.
- **Tolerating broken links and unknown types.** ⛔ Explicitly rejected from the source format:
  leniency inverts the fail-closed posture this project defends elsewhere. Unknown means refused.
- **Whether the absence of a per-module existence-marker file causes the founding zero-edge defect.**
  ⛔ Excluded and **explicitly not a claim of this plan** — it belongs to the resolver-merge work.
  Recorded here only so it is not re-derived.
- **Writing new content into the store.** Excluded — this plan settles the *model*; the resolvers
  that populate it are sequenced after, so they emit into a settled model rather than migrating
  twice.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py` — the
  save/load accessors, the per-module path helper, and the crawl fallback. **OBSERVED.**
- `.../manage-architecture/scripts/_cmd_enrich.py` — the enrichment writers. **OBSERVED.**
- `.../manage-architecture/scripts/_cmd_client_query.py` and `.../_cmd_client_handlers.py` — read-side
  consumers that must surface the freshness verdict. **HYPOTHESIS**, verify at outline.
- `.../manage-architecture/SKILL.md` and its schema standard — documentation that must move in
  lock-step with the field additions. **HYPOTHESIS**, verify at outline.
- Tests for the new validation and migration paths. **HYPOTHESIS**, verify at outline.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Package entry keys are dotted pseudo-identifiers resolving to no filesystem path | **OBSERVED in the WRITER** | The enrichment writer's package function — **in the clone.** ⛔ Confirm it there; the *persisted output* is not reachable (see below). |
| No concept document carries a type, generation, expiry, or status field | **OBSERVED** | Read the **writers**: if no writer emits the field, no document carries it. This settles the claim without the store. |
| The root index maps module names to empty objects | **OBSERVED** | Same — read the index writer. |
| The index is deliberately **not** the module-discovery gatekeeper; what is on disk is what exists | **OBSERVED, and load-bearing** | The crawl fallback's own docstring in the core module. ⛔ **Read it before scoping D3** — this semantic must survive. |
| The dependency field is populated only by an explicit enrichment call, so it is empty because nothing called that verb — **not** because it is vestigial | **OBSERVED** | The enrichment writer. Recorded because the distinction matters: this is a **separate question** from the resolver-merge defect. |
| The live store's current contents — document count, which fields are absent, how many are stale | **NOT REACHABLE FROM THIS CLONE** | The persisted store lives under the git-ignored `.plan/` tree. ⛔ **Do not go looking for it.** Every claim above is re-derivable from the **writers**, which are in the clone. **Derive from the writers, and build the migration against fixtures rather than against a live store.** |
| The named save/load accessors are the **only** writers | **HYPOTHESIS** | ⛔ **Enumerate the callers.** A second writer that does not learn the new validation would produce documents the readers refuse. |
| Type and provenance can be added additively without breaking existing readers, because readers use an accessor rather than a whole-dict schema assertion | **HYPOTHESIS** | Read the accessor and its call sites. If any reader asserts on the whole dict, the addition is breaking and the plan re-scopes. |
| Adding descriptions to the index does not restore it to gatekeeper status | **HYPOTHESIS — verify-first, and it gates D3** | ⛔ Confirm against the crawl fallback. **If the implementing source shows the two cannot be separated, loop back and re-scope D3 to a separate index artifact** rather than shipping a discovery regression. |
| The migration handles a store written before the fields existed | **HYPOTHESIS — verify-first, and it gates D1 and D2** | An absent type on an existing document must produce a **deterministic, named outcome** (migrate-on-read, or refuse with a code) — ⛔ **never a silent default that makes an unmigrated document indistinguishable from a migrated one.** |

An asserted **absence** ("no document carries a type") is verified exactly as an asserted presence —
and here it is settled from the writers, which is both cheaper and more reliable than sampling a
store.

## Verification

- **Every store-shape claim is verified against the WRITER, not against a store.** The live store is
  not in the clone, and a fixture is not evidence about production data. Reading the writer is the
  stronger check anyway: it establishes what *can* be persisted, not what one snapshot happens to
  hold.
- **The migration is verified in three states**: a pre-field document, a migrated document, and a
  document with an unknown type. The first must produce the named outcome, the third must be refused.
  ⛔ A silent default on the first is the defect this deliverable exists to prevent.
- **D3 is verified by a discovery negative control**: a module present on disk but absent from the
  index must still be discovered. If it is not, the index has become a gatekeeper and the deliverable
  has failed regardless of the descriptions being present.
- **D4 is verified without reading a body** — assert the freshness verdict is obtainable from the
  header alone, since filtering before loading is the whole point.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Sequencing.** This plan rewrites the persisted concept model inside the architecture core.
  ⛔ **Do not run it concurrently with any other plan touching that core** — the collision would be
  in the same file, not merely the same namespace. The resolver plans that write into this store
  should be sequenced **after** it, so they emit into a settled model rather than migrating twice.
- **Adjacency.** The query-vocabulary plan consumes this store but does not write it; it stays
  untouched here.
