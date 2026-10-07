# PLAN-CIS-026: The LSP Derivation Resolver — symbol truth harvested into the module graph

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

A language server knows what the substrate cannot derive: real symbol references, resolved by a
real parser. But LSP is built for a long-lived editor session amortizing index cost over thousands
of queries, while this project's consumers are one-shot subprocesses and dispatched leaves —
booting a server per query is not viable.

The resolution is to make the language server a **derivation resolver** rather than a query
backend. It runs once at derivation time, harvests symbol references, lifts them from file→file to
module→module through the attribution seam, and emits edges into the store PLAN-02 already ships.
Cold start is paid once, like any crawl; reads stay cheap and persistent; the provenance contract
stamps the edges `lsp-{language}` and the capability report distinguishes *no LSP resolver ran*
from *it ran and found nothing*.

This is the plan that puts **real** edges in the graph — the thing F2's retirement explicitly did
not do.

## Deliverables

1. **An LSP-backed derivation resolver** implementing the shipped `DerivationResolverBase`
   contract: launch a configured server, initialize the workspace, harvest references, shut down,
   return `(from, to)` module pairs plus `notes[]`. ⛔ **No new extension point** — the seam exists
   and this is an implementor of it. If this plan finds itself extending the seam, stop and record
   why; that is a co-design signal, not a licence to widen.
2. **The file→module lift.** Symbol references are file-granular; edges are module-granular. The
   lift goes through the path-attribution seam, and ⛔ **a reference whose endpoint cannot be
   attributed produces NO edge and a `notes[]` entry** — never a guessed module. The seam's own
   contract already forbids inventing a node: an endpoint that is not a known module is dropped.
3. **Server lifecycle and its honest failure modes.** A server that is absent, fails to start,
   times out, or does not support the workspace must produce `resolver ran: no` with a stated
   reason — never a silent zero-edge result. ⛔ **This is the exact failure the provenance contract
   was built for**; a resolver reporting `status: ok` with zero edges because its server never
   started is the confident-empty-answer archetype this epic exists to eliminate.
4. **Configuration** — which servers, for which languages, enabled or not. ⚠ **Coordinate with
   PLAN-CIS-005 (resolver-configuration), which owns the resolver config surface.** This
   deliverable supplies LSP-specific settings *within* that surface and MUST NOT ship a parallel
   config mechanism. If PLAN-CIS-005 has not landed, record the coupling and define the minimum.
5. **Documentation** — the resolver on `doc/concepts/code-intelligence.adoc` (which currently
   names `build-maven` as "the one shipped resolver"), the tier-ladder correction (Tier 2 is no
   longer entirely "NOT BUILT" once symbol references are harvested — ⚠ **state precisely what is
   and is not built; a half-built tier described as built is this epic's own theme**), and the
   lifecycle rationale so the next reader does not re-propose live pass-through.

⚠ **Five deliverables, but D1 and D3 are substantial.** Evaluate the split guard at outline —
a natural cut is (D1+D2+D3: one language end-to-end) then (D4+D5: configuration and generalization).

## Claim Labels

- **OBSERVED** — the derivation-resolver seam is shipped: `DerivationResolverBase` inherits from
  neither `ExtensionBase` nor `BuildExtensionBase`, implementors opt in by multiple inheritance
  (`doc/concepts/code-intelligence.adoc` § Why a third axis; ADR-013).
- **OBSERVED** — the union needs no conflict rule because an edge is an unweighted `(from, to)`
  boolean; duplicate identity collapses to one edge carrying both producer ids
  (`code-intelligence.adoc` § N-resolver union). **An LSP-derived edge corroborating a Maven-derived
  one is therefore additive, not conflicting.**
- **OBSERVED** — the provenance contract already distinguishes `resolver_count: 0, edges: []`
  ("no resolver ran") from `resolver_count: N, edges: []` ("N ran and found nothing")
  (`code-intelligence.adoc` § The provenance contract).
- **OBSERVED** — the seam "derives edges only for module sets that Tier 0 discovered. A resolver
  cannot invent a node" (`code-intelligence.adoc` § The honest limit). **D2's drop-and-note
  behaviour is this rule, not a new one.**
- **OBSERVED** — `build-maven` is currently documented as "the one shipped resolver"
  (`code-intelligence.adoc` § Related).
- **OBSERVED (orchestrator analysis, 2026-08-01)** — LSP has no method returning module-level
  edges, no transitive traversal (`callHierarchy` is incremental and client-walked), and no
  file-glob or path→owner method. **This is why the server is used as a derivation-time producer
  rather than as a query backend**, and why Tier-1 navigation stays on the persisted store.
- **HYPOTHESIS** — a language server can be driven headlessly to completion in batch and yield a
  reference set worth harvesting, within a tolerable time budget. Confirm/refute by driving ONE
  server (the project's own Python surface is the obvious first target) end-to-end at outline
  (verify-at-outline). ⛔ **This is the plan's central risk and its cheapest possible test — run
  it before scoping anything else.** If a batch harvest is impractical, the plan re-scopes to the
  daemon-hosted alternative below rather than proceeding.
- **HYPOTHESIS** — the file→module lift produces edges that are *correct*, not merely present.
  Confirm/refute by spot-checking derived edges against known dependencies at outline. ⚠ The
  provenance contract "makes an answer auditable; it does not make it correct"
  (`code-intelligence.adoc` § The honest limit) — **a confidently-labelled wrong edge is worse
  than no edge**, and this plan is capable of producing them at volume.
- **HYPOTHESIS (recorded alternative, not this plan's scope)** — live symbol queries
  (`definition` at a position, `rename` for ADR-007) could pass through to a warm server hosted in
  `marshalld`, making Tier 2 an opt-in capability that reports itself absent rather than empty.
  **Deliberately OUT of scope here.** Recorded so the next reader does not treat its absence as
  an oversight, and so ADR-007's survivor sweep has a named landing place.
- **Verify-first clause**: the batch-harvest feasibility hypothesis gates every other deliverable.
  Settle it against a running server before scoping D2–D5; refutation loops back to re-scope.

## Expected Surface

- **HYPOTHESIS**: the resolver's home bundle — `pm-dev-python` for a Python-first implementation, or a language-neutral home in `plan-marshall`. **Decide at outline** (verify-at-outline); the choice follows the seam's own logic that domain knowledge lives with the domain that owns it.
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md` — the contract implemented (read, not edited)
- **OBSERVED**: `doc/concepts/code-intelligence.adoc` — resolver list, tier ladder, lifecycle rationale
- **HYPOTHESIS**: resolver configuration surface — shared with PLAN-CIS-005 (verify-at-outline)
- **HYPOTHESIS**: tests under `test/{owning-bundle}/` (verify-at-outline, follows the home decision)

## Dependencies and Sequencing

- **Depends on**: **PLAN-02** (shipped #1067 — the seam). **PLAN-CIS-023** (attribution seam) for
  D2's file→module lift. ⛔ **PLAN-CIS-023 is a hard gate for D2** — without a trustworthy
  path→module answer the lift guesses, and a guessed edge is the failure mode D2 exists to prevent.
- **Coordinates with**: **PLAN-CIS-005** (resolver-configuration) for D4 — not a hard gate.
- **Overlaps with**: **PLAN-CIS-003** and **PLAN-CIS-004** — all three are derivation resolvers
  landing edges through the same seam. ⚠ **Disjoint by file, adjacent by contract**: they touch
  different bundles but all consume the same seam and the same union semantics. **Pairing is
  permissible; re-verify at emit time that none of them is editing the seam itself.**
- **Adjacent to**: `manage-architecture` core — this plan produces edges, never queries them.
  ⛔ **If it finds itself editing the query layer, PLAN-02's seam was incomplete — loop back.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-026-lsp-derivation-resolver.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
