# PLAN-CIS-029: The Persisted Architecture Store Has No Concept Model — No Identity, No Type, No Provenance

epic: code-intelligence-substrate
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`.plan/project-architecture/` is already shaped like a knowledge bundle — a directory of
per-module concept documents (`{module}/enriched.json`) under a root index (`_project.json`) —
but it carries none of the constructs that make such a bundle answerable without reading all of
it. Concepts have no declared **type**, their inner package entries use a **second identity
system** that resolves to no filesystem path, the root index carries **no descriptions** so it
cannot serve as a pre-flight read, and no concept records **who generated it, against which tree,
or when it goes stale** — the only freshness signal is file mtime, which the epic has repeatedly
ruled inadmissible as evidence.

Give the store a concept model: path-as-identity, a required type, a description-bearing index,
and generation provenance keyed on `worktree_sha`. This is the substrate the LSP-shaped query API
(PLAN-CIS-002) is meant to query and the surface every derivation resolver writes into.

The design is adapted from the Open Knowledge Format (OKF v0.1 conformance + v0.2 trust-signal
families, Google Cloud, June 2026). **Only the data model is adopted — not the serialization and
not the conformance posture.** The store stays JSON: its consumers are scripts
(`architecture resolve`, `files --module`, `which-module`), so markdown+frontmatter would buy
rendering we do not need. OKF's leniency rules (consumers MUST tolerate broken links and unknown
types) and its no-central-type-registry stance are **explicitly rejected** — they invert the
fail-closed detector posture and the closed-vocabulary posture that PLAN-CIS-008 and
PLAN-CIS-009 exist to defend.

## Deliverables

1. **Path is identity.** Retire the dotted pseudo-ids in `key_packages` (`skills.manage_architecture`,
   `skills.phase_workflow`) in favour of repo-relative paths, so a concept's key resolves to a real
   filesystem location and no second identity system needs keeping in sync. Migrate the existing
   entries; reject a non-resolving key at write time.
2. **A required `type` on every concept document.** A closed, validated vocabulary — not OKF's
   open producer-defined one — so the store can hold more than modules (skill, script, standard,
   ADR) without standing up a parallel store. An unknown type is refused at write time.
3. **The root index carries per-module descriptions.** `_project.json`'s `modules` map holds one-line
   descriptions so a consumer can decide which concept documents to open instead of opening all
   twelve. ⛔ This MUST NOT reintroduce `modules` as the discovery gatekeeper — see the verify-first
   clause below.
4. **Generation provenance and freshness.** Every concept document records `generated: {by, at,
   worktree_sha}`, and reads surface a staleness verdict derived from `worktree_sha` rather than
   mtime. `worktree_sha` is the stronger primitive than OKF's wall-clock `stale_after`: it answers
   *generated against which tree*, not merely *when*. The signal must be readable without parsing
   the concept body, so a consumer can filter before loading.

Four deliverables — below the ~6 split-guard threshold, no split rationale owed. The
`*_reasoning` field family (which conflates source citation with inference — see Claim Labels) is
deliberately OUT of scope here and stays an open epic defect.

## Claim Labels

- OBSERVED: The store holds 12 module concept documents plus `_project.json`; every module
  directory contains exactly one `enriched.json` — read by direct enumeration of
  `.plan/project-architecture/`.
- OBSERVED: `internal_dependencies` is `[]` in all 12 concept documents, and `key_dependencies` is
  `[]` in 11 of 12 (`default` carries 4) — read from each `enriched.json`.
- OBSERVED: `_project.json`'s `modules` map holds 12 bare keys mapped to **empty objects**, so the
  index carries no description content — read at `.plan/project-architecture/_project.json`.
- OBSERVED: `key_packages` keys are dotted pseudo-ids that resolve to no filesystem path — read at
  `.plan/project-architecture/plan-marshall/enriched.json` § `key_packages`, written at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py` §
  `enrich_package`.
- OBSERVED: No concept document carries a `type`, `generated`, `stale_after`, or `status` field —
  read across all 12 `enriched.json` top-level key sets.
- OBSERVED: 8 of the 12 concept documents are unmodified since 2026-06-29; the store's only
  freshness signal is filesystem mtime.
- OBSERVED: `internal_dependencies` is populated ONLY by an explicit enrich call — written at
  `_cmd_enrich.py` § `enrich_dependencies`. The field is therefore **not vestigial**; it is empty
  because nothing has called that verb, which is a separate question from the graph-merge defect.
- OBSERVED: `_project.json["modules"]` is deliberately NOT the module-discovery gatekeeper under
  the on-demand crawl model — read at
  `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py`,
  the `crawl_all_modules` fallback docstring ("what is on disk is what exists").
- OBSERVED: **Zero `derived.json` files exist anywhere in the store**, although
  `_architecture_core.py` treats a per-module `derived.json` as the on-disk marker of a module's
  existence — established by a full enumeration of `.plan/project-architecture/**/*.json`, which
  returns only `_project.json` and 12 `enriched.json`. See Adjacency.
- HYPOTHESIS: The write path for both files is `_architecture_core.py` § `save_project_meta` and
  § `save_module_enriched` (tmp-then-swap), and these are the only writers — confirm/refute at
  `_architecture_core.py` § `save_project_meta` / § `save_module_enriched` by enumerating callers
  (verify-at-outline).
- HYPOTHESIS: The `type` and `generated` fields can be added additively without breaking existing
  readers, because readers access `enriched.json` through the `load_module_enriched` accessor
  rather than by whole-dict schema assertion — confirm/refute at `_architecture_core.py` §
  `load_module_enriched` and its call sites (verify-at-outline).
- **Verify-first clause (deliverable 3):** Before scoping the index change, confirm against
  `_architecture_core.py` § `crawl_all_modules` that adding per-module descriptions to
  `_project.json["modules"]` does not restore that map to gatekeeper status. The on-demand crawl
  semantic ("what is on disk is what exists") is load-bearing and MUST survive: descriptions are
  a *read-side* enrichment of the index, never a *discovery-side* filter. If the implementing
  source shows the two cannot be separated, loop back and re-scope deliverable 3 to a separate
  index artifact.
- **Verify-first clause (deliverables 1 and 2):** Both are migrations of live persisted data.
  Confirm the migration path handles a store written before the field existed — an absent `type`
  on an existing document must produce a deterministic, named outcome (migrate-on-read or
  refuse-with-code), never a silent default that makes an unmigrated document indistinguishable
  from a migrated one.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py`
  — `save_project_meta`, `save_module_enriched`, `load_project_meta`, `load_module_enriched`,
  `get_module_enriched_path`, `DIR_PER_MODULE_ENRICHED`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py`
  — `enrich_package`, `enrich_project`, `enrich_module`, `enrich_dependencies`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py`
  and `_cmd_client_handlers.py` — read-side consumers that must surface the new freshness verdict
  (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md` and
  `standards/manage-api.md` — the canonical-invocation and schema documentation that must move in
  lock-step with the field additions (verify-at-outline)
- OBSERVED: `.plan/project-architecture/**` — the live persisted store the migration rewrites
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/tests/**` —
  test surface for the new validation and migration paths (verify-at-outline)

## Dependencies and Sequencing

- **Depends on: PLAN-CIS-027** — hard gate. CIS-027 is repairing the resolver-edge merge inside
  `manage-architecture` core; this plan rewrites the persisted concept model in the same module.
  Concurrent execution would collide on `_architecture_core.py` directly, not merely in a shared
  namespace. Do not emit until CIS-027 has landed and its landing is analyzed.
- Overlaps with: PLAN-CIS-004 (native-coordinate-resolvers) and PLAN-CIS-026
  (lsp-derivation-resolver) — both write into this store, so both should be sequenced AFTER this
  plan so they emit into the settled concept model rather than migrating twice. Both are already
  hard-gated on CIS-027.
- Adjacent to: PLAN-CIS-002 (lsp-shaped-query-api) — consumes this store but does not write it;
  stays untouched here.
- **Adjacency, ⛔ hand to CIS-027 before this plan runs:** the store contains **zero
  `derived.json` files**, while `_architecture_core.py` treats a per-module `derived.json` as the
  on-disk existence marker under the on-demand crawl model. Whether that absence is a cause of the
  founding zero-edge defect, a benign consequence of a different production path, or unrelated is
  **NOT settled here and is NOT a claim of this plan** — it is CIS-027's question, recorded so it
  is not re-derived.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-029-architecture-store-concept-model.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
