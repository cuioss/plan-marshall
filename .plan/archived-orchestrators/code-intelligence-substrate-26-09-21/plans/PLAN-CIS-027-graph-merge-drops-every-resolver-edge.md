# PLAN-CIS-027: 29 Resolver Edges Become Zero Graph Edges — and the proof that missed it

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

PLAN-CIS-003 (#1074) wired three derivation resolvers and reported the epic's founding defect
closed. **It is not closed.** At HEAD the resolvers report 24 + 0 + 5 edges while
`architecture graph` returns `edge_count: 0`, `impact` is empty for every module probed, and all
12 modules are listed as both roots and leaves.

Close the gap between derived edges and graph edges — and **audit the proof that reported it
already closed**, because a deliverable whose end-to-end assertion passes in-plan while the live
system returns empty is a second defect, in the evidence rather than the code.

## Deliverables

1. **Derive why 29 resolver edges yield 0 graph edges.** ⛔ **Derive it — do not adopt any
   hypothesis in this spec as a conclusion.** Candidates, all UNCONFIRMED: the merge dropping pairs
   whose endpoints are not both known module names (the documented "a resolver cannot invent a
   node" limit); the surviving markdown edges collapsing to self-edges after module-granular
   mapping; or `graph` reading a persisted edge set the live resolvers never write into.
2. **Fix it**, so `architecture graph` / `impact` / `neighbors` / `path` answer over the derived
   edge set for this marketplace.
3. **Audit D4's proof and replace it with one that cannot pass while main is empty.** The landing
   records two facts that make this mandatory: D4's assertion was **rewritten mid-plan** away from
   `producers == [python]` to "three things that are actually true", and its non-emptiness is
   **gated on a hidden identity check** — `plugin_discover` early-returns `[]` unless
   `marketplace.json` name == `plan-marshall`. ⭐ **A test that passes on a fixture while the live
   repo returns empty is the test-pins-the-defect archetype**; the replacement must assert against
   the merged graph, not the resolver-level count.
4. **The `ext-point-derivation-resolver.md:3` count-prose defect that SHIPPED in #1074.** Line 3
   claims "three resolvers … two from Axis-A and one from Axis-B" with the enumeration behind a
   cross-reference, so a fourth resolver needs a header edit nothing forces. ⛔ Replace with the
   **roster-free formulation q-gate `817899` already prescribed**. ⚠ **This is a live defect in
   merged main**, not a new finding.
5. **Document the one-resolver-id-per-bundle cardinality.** The CIS-003 spec allocated two
   implementors from one bundle; the seam permits one, and the constraint was undocumented. Record
   it in the extension-point contract so the next spec cannot repeat it.

⚠ **Five deliverables, D1 is a research task with an unknown floor.** Evaluate the split guard at
outline: D4+D5 (documentation corrections) can ship independently of D1–D3 and may be the natural
cut if D1's derivation proves deep.

## Claim Labels

- **OBSERVED (orchestrator, probed live at HEAD 2026-08-02, post-merge)**: `architecture graph` →
  `edge_count: 0`, `edges[0]`, all 12 modules in both `roots` and `leaves`;
  `impact --module plan-marshall` → empty; `impact --module pm-documents` → empty;
  `neighbors --module plan-marshall` → itself only; `resolvers[3]` → `markdown, 24, ok` ·
  `maven, 0, ok` · `python, 5, ok`.
- **OBSERVED (rules out stale data)**: `derived-module --module pm-documents` carries
  `component_refs[8]` including **five RESOLVED cross-bundle refs** (4× `plan-marshall`,
  1× `pm-plugin-development`, all `resolved: true`). Inputs fresh and resolved; output empty.
- **OBSERVED (rules out a stale plugin cache)**: the three new resolvers are present and
  executing, so #1074's code is the code running.
- **OBSERVED (from the CIS-003 landing message, first-party to that plan)**: "D4's non-empty
  assertion is only reachable for THE plan-marshall marketplace. `plugin_discover` early-returns
  `[]` unless `marketplace.json` name == `plan-marshall`." And: "The python resolver never produces
  an edge ALONE. Every pair its import join derives is also derived by the markdown resolver."
- **OBSERVED (from `marketplace-dependency-resolver-021`)**: the line-3 count-prose defect, that
  CodeRabbit flagged it as `cd99e7`, that triage declined it on a premise false for that line, and
  that the cited authority `817899` prescribes the opposite of the refutation it was cited for.
- **HYPOTHESIS (the mechanism)**: any of the three candidates in D1. Confirm/refute at
  `manage-architecture/scripts/_cmd_client_query.py` § `get_module_graph` against
  `tools-marketplace-inventory/scripts/_dep_index.py` § the index structure (verify-at-outline).
  ⛔ **This is the plan's entire premise — settle it before scoping D2.**
- **HYPOTHESIS (asserted absence)**: no consumer currently depends on the graph being empty.
  Confirm/refute by enumerating consumers of `graph`/`impact`/`neighbors`/`path`
  (verify-at-outline). ⚠ `phase-2-refine`'s Feasibility Check and `architecture-refresh` both read
  `graph` and are documented as vacuous at zero edges — **they will start firing.** That is the
  point, and it may surface latent breakage.
- **Verify-first clause**: ⛔ **The CIS-003 spec's central risk — module-granular 12 nodes vs
  component-granular 294 components, with an explicit instruction to LOOP BACK rather than
  proceed — appears to have gone unsettled.** Settle it here against the implementing source
  before scoping. If module-granularity is the wrong exposure, D2 becomes a design decision and
  this plan loops back rather than forcing the existing shape.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py` — the merge and `get_module_graph`
- **OBSERVED**: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/` — `_dep_index.py`, `_dep_detection.py`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md`:3 and § Current implementations — D4/D5
- **HYPOTHESIS**: `pm-plugin-development/.../plugin_discover.py` — the identity gate (verify-at-outline)
- **OBSERVED**: `test/pm-plugin-development/`, `test/plan-marshall/manage-architecture/` — the D4 proof and its replacement

## Dependencies and Sequencing

- **Depends on**: PLAN-02 (#1067) and PLAN-CIS-003 (#1074), both shipped.
- ⛔ **GATES PLAN-CIS-004 and PLAN-CIS-026.** Both add resolvers through this same merge path.
  **Adding a fourth and fifth producer to a merge that drops its inputs adds nothing** — neither
  may be emitted until this lands.
- **Overlaps with**: `manage-architecture` (PLAN-CIS-001, PLAN-CIS-002) and
  `pm-plugin-development` (PLAN-CIS-006, PLAN-CIS-021, PLAN-CIS-025). ⛔ **Never pair with any of
  them** — this plan is unusually wide because the defect spans the producer/consumer boundary.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-027-graph-merge-drops-every-resolver-edge.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
