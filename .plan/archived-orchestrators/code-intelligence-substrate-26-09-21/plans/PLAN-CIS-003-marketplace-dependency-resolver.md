# PLAN-CIS-003: Wire the Working Marketplace Derivation Into the Vacuous Graph

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

This repository already contains a working cross-file dependency derivation for marketplace
components — `resolve-dependencies` derives real edges with line-number provenance across five edge
types — while `architecture impact` returns empty over the same repo. Two substrates coexist and do
not know about each other.

Implement the marketplace resolver against PLAN-02's seam, wrapping the existing engine so the
graph family answers from real derived edges for bundle projects.

⛔ **The resolver implementation lives at `marketplace/bundles/pm-plugin-development/` (operator
decision).** Core owns the seam only; marketplace-component knowledge is `pm-plugin-development`'s
domain, exactly as `arch-gate-*` and `ext-triage-*` are domain-owned.

## Deliverables

1. **TWO separately-registered resolvers**, not one — a **markdown resolver** (script notation, skill
   references, relative-path xrefs, `implements:`) and a **Python resolver** (AST-parsed imports).
   ⭐ This is the operator's N-resolver requirement made concrete: plan-marshall needs one for its
   markdown and one for its Python, independently enable-able and independently reported.
2. Reuse of the existing `_dep_detection.py` / `_dep_index.py` engine rather than a reimplementation
   — the derivation logic is proven and must not be forked. The split is a **registration** boundary
   over the existing five detectors, not a rewrite.
3. Per-edge provenance conforming to PLAN-02's contract: every derived edge names which of the two
   resolvers produced it.
4. Node/edge vocabulary reconciliation: the engine speaks component notation (`bundle:skill:script`),
   the graph family speaks module names. Settle which granularity the graph exposes and how the two
   map.
5. Tests proving `architecture impact` returns non-empty for a bundle project, closing the epic's
   founding open defect.
6. **Documentation.** Register both resolvers in `doc/concepts/extension-architecture.adoc`'s
   implementation table, and extend `tools-marketplace-inventory`'s SKILL.md to state that its
   engine now also serves the architecture graph. ⛔ Ship docs **in this plan**.

⚠ **At 6 deliverables this spec is AT the split guard.** The natural split line is deliverable 1's
two resolvers (markdown / Python) into two plans, or peeling deliverable 4 (vocabulary
reconciliation) out as its own. **Re-evaluate at outline and split unless the parts genuinely cannot
ship independently** — proceeding unsplit requires a recorded decision.

## Claim Labels

- **OBSERVED**: `resolve-dependencies rdeps --component plan-marshall:manage-architecture` returns
  **9 real cross-bundle dependents with line numbers** — `manage-run-config`, `phase-4-plan`,
  `phase-5-execute`, and the `arch-gate-*` / `ext-triage-*` skills of the js, java and python
  bundles. Run live.
- **OBSERVED**: `resolve-dependencies deps --component plan-marshall:marshall-orchestrator` returns
  **18 direct and 113 transitive** dependencies with `resolved` flags and depth-plus-via provenance.
- **OBSERVED**: `resolve-dependencies validate --scope marketplace` enumerates **294 components and
  2467 dependencies, 2347 resolved**.
- **OBSERVED (five edge types)**: `_dep_detection.py` declares `SCRIPT_NOTATION`,
  `SKILL_REFERENCE`, `PYTHON_IMPORT` (via AST parsing), `RELATIVE_PATH`, and `IMPLEMENTS`.
  ⭐ **This is what makes the two-resolver split cheap**: `PYTHON_IMPORT` is already a separate
  detector from the four markdown-facing ones, so the boundary already exists in the code and the
  split is a registration change rather than a decomposition.
- **HYPOTHESIS**: the four markdown detectors and the one Python detector partition cleanly with no
  shared state — confirm/refute at `_dep_detection.py` § the detector functions and `_dep_index.py`
  § the index build (verify-at-outline). ⚠ If they share an index pass, "two resolvers" may mean two
  *views* over one pass rather than two independent walks — a design decision, not a given.
- **OBSERVED (the side-by-side)**: over the same repository, `architecture impact --module
  plan-marshall` returns empty while `rdeps` returns 9 dependents. The derivation gap is an
  **unwired** capability, not a missing one.
- **HYPOTHESIS**: the two vocabularies can be mapped without loss — the graph family is
  module-granular (12 bundle nodes) while the engine is component-granular (294 components).
  Confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py`
  § the index structure, against `_cmd_client_query.py` § `get_module_graph` (verify-at-outline).
  ⚠ **This is the plan's central risk**: if module-granularity is the wrong exposure, deliverable 3
  becomes a design decision rather than a mapping, and the plan must loop back rather than proceed.
- **Verify-first clause**: the epic's strongest standing hypothesis is that the real coupling here is
  **skill-to-skill and script-to-script**, which a module-level graph does not model. If outline
  confirms that, exposing component-granular edges may matter more than populating the module graph —
  re-scope rather than force the existing shape.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/` — `_dep_detection.py`, `_dep_index.py`, `resolve-dependencies.py`
- **HYPOTHESIS**: `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/extension.py` — resolver registration (verify-at-outline)
- **OBSERVED**: `test/pm-plugin-development/` — tests
- **Adjacent, NOT touched**: `manage-architecture` — the seam is consumed, not edited. If this plan finds itself editing core, PLAN-02's seam was incomplete and this plan must loop back rather than patch across the boundary.

## Dependencies and Sequencing

- **Depends on**: PLAN-02 (the seam). Cannot start before it lands.
- **Overlaps with**: PLAN-01 and PLAN-CIS-006 on `tools-marketplace-inventory`. ⛔ Never pair those
  three.
- ✅ **Surface-disjoint from PLAN-CIS-004** (`pm-plugin-development` vs the `build-*` bundles) — the two
  MAY run concurrently once PLAN-02 has landed.
- ⚠ **PLAN-01 should land first even though it is not a hard gate**: PLAN-01 widens what the
  engine indexes (`workflow/` docs), which changes this resolver's output. Building the mapping
  against an incomplete index risks pinning the blind spot into the vocabulary reconciliation.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-003-marketplace-dependency-resolver.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
