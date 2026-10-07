# PLAN-TRUTH-137: A refuted spec claim has no write-back channel at the plan tier

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-09-04 from `inbox/findings-from-cui-http.md` § 7.3 — a consolidated finding document
> relayed from the **cui-http** repository, aggregating 52 lesson records from the
> `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **That document is the sole surviving
> record of those lessons** — the source records were removed after it was written.

## Objective

**A claim introduced at spec-authoring time is treated as ESTABLISHED FACT by every downstream agent,
because nothing in the artifact distinguishes an author's hypothesis from a verified finding — and an
agent that REFUTES such a claim has no channel that propagates the refutation back into the artifact
the next agent reads.**

**Observed, and it came within one step of laundering a false claim into shipped source:**

1. A spec justified a change by asserting a latent **Turkish-locale defect**.
2. An executing agent **refuted it empirically** — `String.equalsIgnoreCase` is locale-independent.
3. **The refutation lived only in that agent's return payload.** The spec kept its original wording.
4. A later `finalize-step-security-audit` agent **re-asserted the false claim** in its report.
5. It was one step from a code comment.

⛔⛔ **The compounding property is the dangerous one: the claim GAINED APPARENT CORROBORATION AT EACH
HOP PURELY BY BEING RESTATED.** spec → execution report → audit report → (nearly) code comment. Every
restatement reads to the next agent as an independent source. **Nothing in the chain re-derived it, and
nothing needed to, because by hop three it looked settled.**

### ⭐⭐⭐ The exact gap is a TIER gap, and the source names it precisely

**This machinery already exists — at the orchestrator tier.** The `## Claim Labels`
`OBSERVED` / `HYPOTHESIS` contract plus the persisted re-grounding verdict field stamped through
`corpus set-verdict` / read through `corpus verdicts` is exactly this mechanism, and **it demonstrably
worked in this epic**: a `contradicted` verdict blocks emission, a `rescoped: yes` records absorption,
and the grammar has one emitter and one parser so producer and consumer cannot drift.

⇒ **The missing tier is the PLAN tier**, where an executing agent's mid-run refutation has **no
equivalent write-back**. This spec is therefore **not a design problem** — it is the extension of a
landed, proven contract down one tier, and the design work is mostly deciding what the plan-tier
analogue of `corpus set-verdict` writes to and who reads it.

⛔ **Do NOT re-invent the vocabulary.** `corroborated` / `contradicted` / `unverifiable`, plus the
`rescoped` rule and the admission table, are defined once at
`persona-plan-orchestrator/standards/orchestration-model.md` § Re-Grounding Verdict Field. A second
vocabulary at the plan tier would recreate at the boundary the exact drift this closes.

## Deliverables

1. **D0 — GATE: derive the carrier and the population.** Establish (a) which plan-tier artifact should
   hold a plan-scoped claim label — the request, the solution outline's deliverables, or a dedicated
   store — and (b) how many downstream report-authoring steps currently quote an upstream rationale.
   ⛔ **Publish the swept population and its size.** ⭐ **D0 must also settle a genuine fork:** whether
   the plan tier needs its own persisted field at all, or whether an executing agent's refutation
   should instead route to the ORCHESTRATOR as an inbox message and be stamped on the staged spec
   through the existing `corpus set-verdict`. **The second arm reuses a landed mechanism entirely and
   may be the whole fix; it must be costed, not dismissed.**
2. **D1 — a plan-tier claim carries `OBSERVED` / `HYPOTHESIS` labelling**, so a downstream agent can
   tell an author's inference from a verified finding **without re-deriving it**. This is the
   Verify-First Contract applied one tier down; the labelling rules are inherited, not restated.
3. **D2 — a refutation has a write-back channel and it is not a return payload.** Whichever carrier D0
   selects, an executing agent that refutes an upstream claim must be able to persist that verdict
   where the NEXT agent reads it — not only where the caller reads it once.
4. **D3 — a report-authoring step quotes an upstream rationale AS a quote.** *"The spec claims X"*,
   never *"X"*. ⭐ **This is the cheapest half and it closes the laundering path even if D1/D2 land
   narrowly**, because it removes the restatement that manufactures corroboration.
5. **D4 — matched controls, both directions.** A refuted claim must be visibly refuted to a downstream
   agent that did not run the refutation; and **an unrefuted claim must still read exactly as it does
   today** — ⛔ a change that makes every spec claim look provisional would push agents to re-derive
   everything, which is the opposite failure and strictly more expensive.

## Claim Labels

- OBSERVED: the four-hop chain (spec assertion → empirical refutation → refutation confined to a return payload → re-assertion by a later audit agent) — first-party in the source epic, quoted in the consolidation document.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Foreign cui-http epic narrative; source records removed, not reachable
- OBSERVED: the orchestrator tier HAS this machinery and it worked in this epic — `## Claim Labels`, `corpus set-verdict`, `corpus verdicts` are live and their behaviour is corroborated by this epic's own drains.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: orchestrator.py implements corpus epics/cross-check/surfaces/verdicts/set-verdict live
- OBSERVED: `String.equalsIgnoreCase` is locale-independent — a language-level fact the executing agent settled empirically, and the reason the original claim was false.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: String.equalsIgnoreCase is documented JDK locale-independent case folding
- HYPOTHESIS: the plan tier has NO equivalent write-back at HEAD. ⛔ **Asserted by the source, NOT read at source by this orchestrator.** Confirm/refute at `manage-plan-documents` / `manage-solution-outline` § the deliverable record, and `manage-references` § the claim surfaces (verify-at-outline).
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Zero claim/verdict/OBSERVED/HYPOTHESIS tokens found under manage-solution-outline manage-references manage-plan-documents
- HYPOTHESIS: report-authoring steps other than `finalize-step-security-audit` quote upstream rationale unqualified. ⛔ NOT enumerated; D0 settles it (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D0 report-authoring-step sweep not performed; not enumerated
- ⚠ Verify-first clause: before D1, settle whether the solution outline's deliverable record already carries a claim/label field that no consumer reads. **If it does, D1 is a consumer fix rather than a schema addition and the plan re-scopes** — the same distinction that turned `dual-homed-...-011` from a schema change into a call-site fix in this epic.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: solution-outline-standard.md carries 0 OBSERVED/HYPOTHESIS/verdict tokens, confirming no unread claim field

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/` — the deliverable record and its claim surface (D1, D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-security-audit.md` — the observed re-asserting consumer (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — § Verify-First Contract, extended one tier down (D1) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-solution-outline/` — the D4 controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Overlaps `PLAN-TRUTH-134`** on `manage-solution-outline/**`. **SERIALIZE.**
- ⚠ **Overlaps `PLAN-TRUTH-131`** on `orchestration-model.md`, and `-131` is itself serialized behind `-124`. Sequence at emit rather than trusting this note.
- Adjacent to: `PLAN-TRUTH-130` (an assessment is read at report time) — that spec is about a stored judgement read at the wrong TIME; this is about a stored claim read at the wrong CONFIDENCE. **Different axes, same artifact family**; keep separate and cross-reference in the shipped docs.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-137-a-refuted-spec-claim-has-no-write-back-channel-at-the-plan-tier.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-151-early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back.md` (PLAN-TRUTH-151)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
