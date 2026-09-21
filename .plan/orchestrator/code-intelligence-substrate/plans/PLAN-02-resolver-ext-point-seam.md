# PLAN-02: A Multi-Resolver Derivation Seam, With Provenance on Every Answer

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`architecture graph` reports 12 nodes and **0 edges** under `status: success`, and `impact` returns
`[]` for every module. The cause is not a missing engine: the sole edge-derivation path is a Maven
`groupId:artifactId` coordinate join, which cannot fire for any project without Maven coordinates —
this bundle repo, and **every Python and npm consumer project**.

Introduce a derivation-resolver extension point in core. `manage-architecture` keeps its query
surface; edge derivation moves behind a seam that domain bundles implement. The Maven join becomes
*a* resolver rather than *the* derivation.

⭐ **The seam is N-resolver by construction, not one-per-project.** A single project routinely needs
several at once — plan-marshall itself needs one for markdown (skill notation, xrefs) and one for
Python files (imports). The derived edge set is the **union** across all active resolvers.

⭐ **Every answer names the resolver that produced it.** A caller must never receive an edge, or an
empty edge set, without knowing which resolvers ran. This is the anti-vacuity property: the epic's
founding defect is a verb reporting `status: success` over an answer nobody could have produced.

## Deliverables

1. A derivation-resolver extension point in `extension-api` supporting **N simultaneously-active
   resolvers**, following the established declaration/discovery/dispatch/null-on-absent contract.
2. `manage-architecture`'s graph family (`graph`, `path`, `neighbors`, `impact`) delegating to the
   seam and **merging** the edge sets of all active resolvers.
3. **Provenance in every result**: each edge carries its producing resolver, and every response
   carries the list of resolvers that ran — so a zero-edge answer distinguishes *no resolver ran*
   from *resolvers ran and found nothing*.
4. The existing Maven coordinate join re-homed as the Maven resolver, behaviour preserved for Maven
   projects.
5. **Documentation — this plan owns the epic's cross-cutting concepts page.** Author a NEW
   `doc/concepts/` page describing the code-intelligence substrate: the Tier 0 / Tier 1 / Tier 2
   model, the resolver seam, the N-resolver union, and the provenance contract. ⭐ **No page in
   `doc/concepts/` covers this subject today** (verified: the 21 pages there include
   `extension-architecture`, `build-management`, `tools-and-scripts`, but nothing on code
   intelligence). Also extend `doc/concepts/extension-architecture.adoc` with the new extension
   point. ⛔ Ship the docs **in this plan**, not afterwards — doc-contract divergence is a recorded
   recurring defect in this repository, and a docs-later plan is exactly how it recurs.

## Claim Labels

- **OBSERVED**: `architecture graph` returns `node_count: 12, edge_count: 0`, all nodes at layer 0,
  every node both root and leaf. `architecture impact --module plan-marshall` returns empty. Both
  under `status: success`.
- **OBSERVED (mechanism)**: `_cmd_client_query.py` builds `artifact_to_module` keyed on
  `f'{group_id}:{artifact_id}'`, then derives an internal edge ONLY by `dep.split(':')` and joining
  the leading `groupId:artifactId` pair against that map. Sole edge-derivation path.
- **OBSERVED**: bundle modules carry `metadata.bundle_name` + `description` and **neither
  coordinate** — read from `architecture derived-module --module plan-marshall`.
- **OBSERVED**: `enriched.internal_dependencies` (LLM-curated) is consulted BEFORE the derivation
  fallback — the substrate's existing non-Maven answer is *curation*, not derivation.
- **HYPOTHESIS**: the seam belongs on `ExtensionBase` as a new face rather than as a standalone
  ext-point, since the build-system ext-point already has four implementations that know their own
  coordinate schemes — confirm/refute at
  `extension-api/standards/extension-contract.md` § the extension-point table and `ext-point-build.md`
  (verify-at-outline). **This changes the shape of deliverable 1** — settle before scoping.
- **HYPOTHESIS**: merging N resolvers needs a conflict rule — two resolvers may derive the same edge,
  or contradictory ones. Confirm/refute by enumerating the overlap between the marketplace markdown
  and Python resolvers (PLAN-CIS-003) at outline. ⚠ **If overlap is real, the merge rule is a design
  decision, not a union** — loop back rather than assuming set-union is correct.
- **Verify-first clause**: deliverable 4 asserts Maven behaviour is currently correct. That is an
  **untested assumption** — this orchestrator verified the join's *shape*, never that it produces
  correct edges on a real Maven project. Verify against an actual Maven consumer repo before
  re-homing, or the refactor faithfully preserves a defect.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/extension-api/` — new ext-point contract + `extension_discovery.py` (verify-at-outline)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py`:299-320 — the coordinate join and the graph family
- **OBSERVED**: `test/plan-marshall/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-01 (shares `manage-architecture`; ⛔ never pair).
- **Gates**: PLAN-CIS-003, PLAN-CIS-004 (implement against this seam) and PLAN-CIS-005 (configures it). None can
  start until this lands.
- **Overlaps with**: PLAN-01, PLAN-CIS-001, PLAN-CIS-002 on `manage-architecture`. ⛔ Never pair.
- ⚠ **Co-design risk with PLAN-CIS-002**: PLAN-CIS-002 reshapes this same query surface to LSP vocabulary. If
  outline finds the API reshape changes THIS seam's return contract, the two must be co-designed or
  merged rather than sequenced — building the seam twice is the failure mode to avoid.
- **Adjacent to**: `truthful-signals` PLAN-89 also touched `manage-architecture` but **landed as PR
  #1044** (merged at `57e1daec3`), so it no longer collides. Re-verify at outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-02-resolver-ext-point-seam.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
