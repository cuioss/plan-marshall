# PLAN-TRUTH-157: Dispatch is assumed to protect judgement quality, but the write-bound half of landing analysis never leaves the calling session

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-13 from an operator model-economy question raised in this orchestrator session ("I run
plans and orchestrators on Sonnet now instead of Opus — sensible if the important part, landing analysis,
is done by an execution-context. Is this throughout the case?"). Corroborated first-party against this
repo's LIVE `manage-config effort read` output before staging, not asserted from the doc alone.

## Objective

**The operating assumption — "switching the calling session to a cheaper model is safe because dispatch
elevates the heavy-judgement work to Opus" — is unverified as a general claim and OBSERVED FALSE for the
orchestrator's own `analyze` verb in this repo's current configuration.**

Two distinct gaps, corroborated live this session:

1. **`orchestrator.analyze` does not resolve to an opus-tier level.** `manage-config effort read --role
   orchestrator.analyze` returns `level-3` (sonnet/high), sourced from `plan.effort` — `orchestrator.effort`
   is unset, so the fallback walk never reaches an opus-tier level. Contrast: `phase-6-finalize`'s
   `default`, `verification-feedback`, and `post-run-review` roles all resolve to `level-5` (opus/high),
   pinned explicitly. The orchestrator's own analysis surface was never given the same treatment.
2. **The write-bound half of landing analysis is inline-only by design, and dispatch doesn't reach it at
   all.** Per the Dispatch Decision Rule (`orchestration-model.md`), `analyze.md` Step 2's ground-truth
   corroboration is the ONE dispatchable sub-step; everything else — landing-report authoring, every
   `queue --transition` / `--set-row`, every Step 5b candidate-lesson/finding disposition (fold / stage /
   promote / discard) with its rationale, new-spec authoring, epic.md reconciliation, the proactive-emit
   admission check — is enumerated "Inline-only." This was demonstrated directly in this session: reconciling
   PLAN-TRUTH-139's landing (7 inbox messages, 2 lessons promoted, 1 spec staged, 1 fold, 2 forwards) ran
   entirely on the calling session's own model. Dispatching the narrow corroboration sub-step, even at an
   opus-tier level, would leave the majority of the judgement — deciding what a candidate-lesson dedups
   against, drafting a new spec's Objective and Deliverables, deciding a Fold's same-act surface update —
   on whatever model launched the orchestrator session.

**What this spec does NOT propose.** The fork-freedom carve-out in the Dispatch Decision Rule — genuinely
fork-prone judgement (workstream cuts, split-guard verdicts, any `AskUserQuestion`-shaped decision) stays
inline because "the fork-prone sub-steps ARE the judgement" and no orchestrator-side resolution step
exists — is NOT contradicted here. The target is the write-BOUND-but-NOT-fork-prone drafting work: content
a leaf can produce and return as data (a landing-report draft, a disposition proposal with rationale, a
new-spec draft) for the orchestrator to review and apply through the SAME sanctioned write calls it uses
today. This is the identical shape S1/S2 already sanction for corroboration — extending it, not weakening
it.

## Deliverables

Six deliverables. D0 is a gate.

1. **D0 — GATE: derive the population, re-confirmed at HEAD.** Enumerate every `analyze.md` and
   `decompose.md` sub-step, classify each as inline-only-because-fork-prone (stays inline, out of scope),
   inline-only-because-nobody-extended-dispatch-there (candidate for this spec), or already-dispatchable.
   Re-run the live `manage-config effort read` checks this Objective cites (`orchestrator.analyze`,
   `orchestrator.decompose`, `phase-6-finalize.*`) against HEAD, since a re-grounding is owed before any
   downstream deliverable proceeds. Publish the population and its size — a remedy chosen before the
   population is derived is the archetype this epic exists to remove.
2. **D1 — Extend `analyze.md`'s dispatchable envelope to the write-BOUND, non-fork-prone drafting work.**
   Landing-report content, each inbox message's disposition proposal (with rationale and, for Fold, the
   same-act surface-update proposal), and new-spec draft content for a Stage disposition move into a
   dispatched leaf's return (structured TOON), alongside the existing corroboration. The leaf writes
   nothing; the orchestrator reviews the return as data and executes every write itself through the
   existing sanctioned calls (`queue --transition`/`--set-row`, `manage-lessons`, `corpus set-verdict`,
   `Write` within its own tree) — S1 (read-only by instruction) and S2 (no leaf writes the ledger) apply
   unchanged.
3. **D2 — Decide `decompose.md`'s shape from D0's population, and apply the same pattern if warranted.**
   `decompose.md`'s research sub-step is already dispatchable per the standard; D0 determines whether its
   OWN write-bound half (workstream-charter drafting, plan-spec drafting) has the same inline-only gap
   `analyze.md` does, and extends it identically if so — or states explicitly why not, per the same
   discipline D0 owes everywhere else in this corpus.
4. **D3 — Pin `orchestrator.effort` to an explicit opus-tier level, independent of `plan.effort`.** Set
   `orchestrator.effort.analyze` (and `.decompose`, `.reader` per D0/D2's finding) to an opus-tier level in
   this repo's `.plan/marshal.json`, so the resolution no longer falls through to whatever `plan.effort`
   happens to be — the orchestrator's own analysis surface must not silently downgrade when a plan's
   own effort is lowered for unrelated cost reasons. Document the recommended non-empty default in
   `marshal-json-reference.md` § Orchestrator Configuration and in `effort-roles.md`'s own text, so a
   fresh repo does not inherit today's silent gap.
5. **D4 — Matched controls, one per member.** A control proving a dispatched leaf's returned draft is
   NEVER applied without passing through the sanctioned write path (an untrusted/malformed draft must not
   silently become a ledger write) — the S1/S2 containment the extension leans on. A control proving
   `orchestrator.effort.analyze` resolves to the pinned level independent of `plan.effort` (vary
   `plan.effort` across the ordinal ladder, assert the orchestrator role is unaffected once pinned).
6. **D5 — Update the Dispatch Decision Rule text and `analyze.md`/`decompose.md`'s own Step 2 documentation**
   to state the new boundary precisely: which sub-steps are now dispatchable, which remain inline because
   they are fork-prone (unchanged), and why the two are not the same set. The existing rationale for
   NOT dispatching fork-prone work must survive verbatim — this deliverable extends the boundary, it does
   not relitigate why the fork-prone exclusion exists.

## Claim Labels

- OBSERVED: `manage-config effort read --role orchestrator.analyze` returns `level-3`, `source:
  plan.effort` (this repo, this session, before staging).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Re-ran manage-config effort read --role orchestrator.analyze at this HEAD: still level-3, source plan.effort
- OBSERVED: `manage-config effort read --role orchestrator.decompose` returns `level-3`, `source:
  plan.effort` (same corroboration).
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Re-ran manage-config effort read --role orchestrator.decompose at this HEAD: still level-3, source plan.effort
- OBSERVED: `manage-config effort read --role phase-6-finalize` / `.verification-feedback` /
  `.post-run-review` all return `level-5`, each sourced from its own explicit `plan.phase-6-finalize.effort.*`
  key — not `inherit`, not a fallthrough.
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Re-ran manage-config effort read --role phase-6-finalize/.verification-feedback/.post-run-review at this HEAD: all three still level-5, each sourced from its own explicit plan.phase-6-finalize.effort.* key
- OBSERVED: `analyze.md`'s own Step 2 "Inline-only" bullet list names landing-report authoring, every
  queue transition, Step 5b per-item disposition, and Step 6 logging/resume-anchor as inline-only; only
  ground-truth corroboration (and, for untrusted text, the two-stage reader path) is dispatchable.
  - verdict: corroborated | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: Re-read analyze.md Step 2 at this HEAD: the Inline-only bullet list is unchanged, still names landing-report authoring, every queue transition, Step 5b disposition, and Step 6 logging/resume-anchor as inline-only
- ⚠ HYPOTHESIS: `decompose.md`'s write-bound half (workstream-charter and plan-spec drafting) has the
  same inline-only gap as `analyze.md`'s. ⛔ NOT checked — reasoned by analogy to `analyze.md`'s shape,
  not read first-party. D0 confirms or refutes against `decompose.md`'s own text (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: decompose.md's write-bound half was not read against analyze.md's shape at cleanup time; D0/D2 own this comparison
- ⚠ HYPOTHESIS: extending the dispatchable envelope to landing-report/disposition/spec drafting does not
  weaken S1/S2 containment, because the leaf still returns data rather than writing, and the orchestrator
  still performs every sanctioned write itself. ⛔ Reasoned from the existing corroboration pattern, not
  independently verified against a constructed adversarial-draft scenario. D4's control settles it
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: The S1/S2 containment claim for a widened dispatch envelope needs D4's constructed adversarial control, not yet run
- ⚠ HYPOTHESIS: no other repo's `.plan/marshal.json` already sets `orchestrator.effort` to a non-default
  value that D3's documented-default change would silently override. ⛔ An asserted absence — verify
  directly against `marshal-json-reference.md`'s own migration/precedence guidance before writing a
  repo-level default recommendation (verify-at-outline).
  - verdict: unverifiable | checked_at: 77cb2e251 | by: truthful-signals/cleanup | rescoped: n/a | evidence: No other repo's marshal.json was surveyed for an existing orchestrator.effort override; not checked at cleanup time

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — Step 2
  dispatch boundary, Step 4/5b inline-only enumeration (D1, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md` — Step 2
  dispatch boundary (D2, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
  — the Dispatch Decision Rule, S1/S2, and the Orchestrator role group's effort resolution text (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md` — the
  Orchestrator role group section and its resolution-order text (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md`
  — Orchestrator Configuration section, the documented default for `orchestrator.effort` (D3)
- HYPOTHESIS: `.plan/marshal.json` — this repo's own `orchestrator.effort` block (D3) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/effort-menu.md` — the
  wizard UX, if it needs a new prompt for `orchestrator.effort` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/**` — new coverage for the extended dispatch boundary
  and the containment/config-resolution controls (D4) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ Surface adjacent to but distinct from PLAN-TRUTH-143 (orchestrator inbox delivery) and PLAN-TRUTH-149
  (landing payload / what the epic learns) — both touch `analyze.md` and `orchestration-model.md` but for
  DIFFERENT reasons (inbox delivery path; report↔inbox fact delta). Re-derive `corpus cross-check` before
  emitting, as always, rather than assuming disjointness by inspection.
- plan-truth-127 and plan-truth-148 were running when this plan was staged and were NOT re-scoped.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-157-dispatch-is-assumed-to-protect-judgement-quality-but-the-write-bound-half-never-leaves-the-caller.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
