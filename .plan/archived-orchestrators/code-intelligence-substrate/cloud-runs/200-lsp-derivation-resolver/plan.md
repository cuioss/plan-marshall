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

# A language server as a derivation resolver — real symbol edges in the module graph

**Epic:** code-intelligence-substrate
**Branch prefix:** feature

## Problem

A language server knows what this substrate cannot derive: **real symbol references, resolved by a
real parser**. But the protocol is built for a long-lived editor session amortizing index cost over
thousands of queries, while this project's consumers are one-shot subprocesses and dispatched
leaves — **booting a server per query is not viable.**

The resolution is to use the language server as a **derivation resolver** rather than as a query
backend. It runs **once at derivation time**, harvests symbol references, lifts them from file-level
to module-level through the attribution seam, and emits edges into the persisted store that the
resolver seam already ships. Cold start is paid once, like any crawl; reads stay cheap and
persistent; provenance stamps the edges with the producing resolver, and the capability report
distinguishes *no resolver ran* from *it ran and found nothing*.

**This is the plan that puts real edges in the graph** — the thing the earlier retirement of the
edge-derivation gap explicitly did not do.

## Goal

The module graph carries edges derived from actual symbol references for at least one language,
stamped with their producer, with every failure mode of the server reported honestly rather than
collapsing into a zero-edge success.

## Deliverables

1. **D0 — GATE: can a language server be driven headlessly to completion in batch, yielding a
   reference set worth harvesting, within a tolerable time budget?**
   ⛔ **This is the plan's central risk and its cheapest possible test — run it against a RUNNING
   server before scoping anything else.** This repository's own Python surface is the obvious first
   target.
   *Done when:* a batch harvest has been driven end-to-end and its timing recorded, **or** the
   premise is refuted.
   ⛔ **On refutation: HALT and re-scope to the recorded daemon-hosted alternative** — do not proceed
   to D1–D4 on an unverified premise, and do not substitute a hand-built reference list for a real
   harvest.
2. **D1 — an LSP-backed derivation resolver** implementing the shipped resolver contract: launch a
   configured server, initialize the workspace, harvest references, shut down, return module pairs
   plus notes.
   ⛔ **No new extension point** — the seam exists and this is an implementor of it. **If this plan
   finds itself extending the seam, stop and record why**; that is a co-design signal, not a licence
   to widen.
   *Done when:* the resolver runs through the existing seam and its edges appear in the store.
3. **D2 — the file-to-module lift.** Symbol references are file-granular; edges are module-granular.
   The lift goes through the path-attribution seam.
   ⛔ **A reference whose endpoint cannot be attributed produces NO edge and a note — never a guessed
   module.** The seam's own contract already forbids inventing a node: an endpoint that is not a
   known module is dropped.
   *Done when:* an unattributable endpoint produces a note and no edge, asserted by test.
4. **D3 — server lifecycle and its honest failure modes.** A server that is absent, fails to start,
   times out, or does not support the workspace must produce **"resolver ran: no" with a stated
   reason** — never a silent zero-edge result.
   ⛔ **This is the exact failure the provenance contract was built for**: a resolver reporting
   success with zero edges because its server never started is the confident-empty-answer archetype
   this epic exists to eliminate.
   *Done when:* each failure mode produces a distinct stated reason, verified with a negative control
   per mode.
5. **D4 — configuration**: which servers, for which languages, enabled or not.
   ⚠ **Coordinate with the resolver-configuration plan, which owns that surface.** This supplies
   language-server-specific settings **within** it and ⛔ **MUST NOT ship a parallel config
   mechanism.** If that plan has not landed, record the coupling and define the minimum.
6. **D5 — documentation.** The resolver on the code-intelligence concepts page (which currently names
   a single shipped resolver), the tier-ladder correction, and the **lifecycle rationale** so the next
   reader does not re-propose live pass-through.
   ⚠ **State precisely what is and is not built** — a half-built tier described as built is this
   epic's own theme.

Six deliverables with D0 a gate — **at the split guard, and D1/D3 are substantial.** ⚠ **Evaluate the
split at outline**; the natural cut is (D0+D1+D2+D3: one language end-to-end) then (D4+D5:
configuration and generalization).

## Out of scope

- **Live symbol pass-through** — answering a definition or rename query at a position against a warm
  server. ⛔ **Deliberately excluded, and recorded so the next reader does not treat its absence as an
  oversight.** A batch harvester and a warm interactive client are **two incompatible lifecycles**,
  and a plan carrying both would ship neither. A separate plan in this epic now commissions that
  alternative; ⛔ **do not fold the two together.**
- **Querying the graph.** Excluded: this plan **produces** edges and never reads them. ⛔ **If it
  finds itself editing the query layer, the resolver seam was incomplete — loop back** rather than
  patching the query side here.
- **A parallel configuration mechanism.** Excluded — see D4.
- **Broad multi-language coverage.** Excluded at this stage: the per-language parser cost is the real
  argument against chasing this tier broadly, so one language end-to-end is the deliverable, and
  generalization follows evidence.

## Expected surface

- The resolver's home bundle — a language-specific bundle for a Python-first implementation, or a
  language-neutral home. **HYPOTHESIS; decide at outline**, following the seam's own logic that
  domain knowledge lives with the domain that owns it.
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md`
  — the contract implemented. **OBSERVED, read not edited.**
- `doc/concepts/code-intelligence.adoc` — resolver list, tier ladder, lifecycle rationale.
  **OBSERVED.**
- The resolver configuration surface — shared. **HYPOTHESIS**, verify at outline.
- Tests under the owning bundle's test tree. **HYPOTHESIS**, follows the home decision.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The derivation-resolver seam is shipped and implementors opt in by inheritance | **OBSERVED** | The extension-point standard plus the concepts page. Both git-reachable — **read them; this plan is an implementor, not an author, of that seam.** |
| The edge union needs no conflict rule, because an edge is an unweighted boolean pair whose duplicate identity collapses to one edge carrying both producer ids | **OBSERVED** | The concepts page's union section. ⇒ **An edge corroborating another producer's edge is additive, not conflicting.** |
| The provenance contract already distinguishes "no resolver ran" from "resolvers ran and found nothing" | **OBSERVED** | The concepts page's provenance section. **D3 implements this rule; it does not invent it.** |
| A resolver cannot invent a node — edges are derived only for module sets already discovered | **OBSERVED** | The concepts page's honest-limit section. **D2's drop-and-note behaviour is that rule.** |
| The protocol has no module-level edge method, no transitive traversal, and no path-to-owner method | **OBSERVED (analysis)** | This is **why** the server is a derivation-time producer rather than a query backend, and why navigation stays on the persisted store. Re-derive against the protocol specification if the design is questioned. |
| A server can be driven headlessly to completion in batch within a tolerable budget | **HYPOTHESIS — the load-bearing one** | **D0.** ⛔ Settle it **against a running server**, not by reading documentation. |
| The lift produces edges that are **correct**, not merely present | **HYPOTHESIS** | Spot-check derived edges against known dependencies. ⚠ Provenance **makes an answer auditable; it does not make it correct** — and ⛔ **a confidently-labelled wrong edge is worse than no edge.** This plan is capable of producing them **at volume**, which is why this claim is called out separately. |

An asserted **absence** ("no resolver derives symbol-level edges today") is verified exactly as an
asserted presence — confirm against the shipped resolver list before building.

## Verification

- **D0 is verified by execution.** A timing from a live server, or an explicit refutation. No
  documentation read substitutes.
- **D2 is verified by the drop case, not the happy case**: an unattributable endpoint must produce a
  note and **no edge**. A test that only exercises attributable references passes against a guessing
  implementation.
- **D3 is verified with one negative control per failure mode** — absent, fails to start, times out,
  unsupported workspace. Each must yield a distinct stated reason; ⛔ none may yield a zero-edge
  success.
- **Correctness spot-check**: sample derived edges and verify them against known dependencies by hand.
  Report the sample size and how it was chosen — ⚠ **a sample is not a population**, and this plan
  should say so about its own evidence.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Dependencies.** The resolver seam and the attribution seam have both shipped; confirm both in the
  clone rather than assuming. ⛔ **The attribution seam is a hard gate for D2** — without a
  trustworthy path-to-module answer the lift guesses, and a guessed edge is exactly what D2 exists to
  prevent.
- **Adjacency.** Two other resolvers land edges through the same seam. ⚠ **Disjoint by file, adjacent
  by contract**: different bundles, same seam and same union semantics. Pairing is permissible —
  **re-verify at emit that none of them is editing the seam itself.**
- ⛔ **Never run concurrently with the live-language-server plan or the editor-facing server plan** —
  shared server binary and configuration surface.
