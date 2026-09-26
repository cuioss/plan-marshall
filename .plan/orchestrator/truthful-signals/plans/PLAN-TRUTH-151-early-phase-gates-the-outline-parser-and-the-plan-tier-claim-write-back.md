# PLAN-TRUTH-151: Early-phase gates, the outline parser, and the plan-tier claim write-back

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

## Objective

The early phases decide what the rest of a run believes, and three of their surfaces cannot be told apart
from a confident answer. An early-phase gate reads identically to a settled result; the scope extractor
invents paths, drops bullets, and reports success over both; and a claim refuted by an executing agent has no
write-back channel at the plan tier, so the refutation reaches the caller once and is then laundered back into
corroboration by the next report that restates it. Merged because all three are the verify-first contract
applied one tier below the orchestrator, on the same outline and status surfaces.

## Deliverables

9 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: decide the early-phase cut, and derive the parser and claim-carrier populations.** Decide the gate cut before implementing (PLAN-TRUTH-119 D0); derive the outline-parser exposed population (PLAN-TRUTH-134 D0); establish the plan-tier claim carrier and the restatement population, including PLAN-TRUTH-137's genuine fork — whether the plan tier needs its own persisted field at all, or whether a refutation should route to the ORCHESTRATOR as an inbox message and be stamped through the existing `corpus set-verdict`. ⛔ The second arm reuses a landed mechanism entirely and may be the whole fix; it must be costed, not dismissed. (PLAN-TRUTH-137 D0.)
2. **D1 — The early-phase gate cut, per D0.** Carries PLAN-TRUTH-119 D1–D3 as one deliverable: the source left them unheadlined precisely because D0 decides the cut, so splitting them before that decision would fabricate a boundary.
3. **D2 — A deterministic Q-Gate for the D1 instance.** That instance was caught by an LLM pass and not by a rule, which is why it needs one. (PLAN-TRUTH-119 D4.)
4. **D3 — Anchor the bullet pattern to start-of-line.** (PLAN-TRUTH-134 D1.)
5. **D4 — Publish `bullets_parsed` against `bullets_seen`, and FAIL the phase when they disagree.** A parser that silently drops input is the volume-read-as-coverage archetype. (PLAN-TRUTH-134 D2.)
6. **D5 — A plan-tier claim carries `OBSERVED` / `HYPOTHESIS` labelling.** The Verify-First Contract applied one tier down; the labelling rules are inherited, not restated. (PLAN-TRUTH-137 D1.)
7. **D6 — A refutation has a write-back channel and it is not a return payload.** (PLAN-TRUTH-137 D2.)
8. **D7 — A report-authoring step quotes an upstream rationale AS a quote.** *"The spec claims X"*, never *"X"*. The cheapest half, and it closes the laundering path even if the others land narrowly. (PLAN-TRUTH-137 D3.)
9. **D8 — Matched controls, both directions.** ⛔ An unrefuted claim must still read exactly as it does today — a change that makes every claim look provisional pushes agents to re-derive everything, the opposite failure and strictly more expensive. (PLAN-TRUTH-134 D3 + PLAN-TRUTH-137 D4.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-119 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-119-early-phase-gates-cannot-be-told-apart-from-confident-answers.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-119 Claim Labels: 5 verdicts, 3 corroborated + 2 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-134 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-134-the-scope-extractor-invents-paths-and-drops-bullets-and-reports-success.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-134 Claim Labels: 6 verdicts, 3 corroborated + 3 unverifiable.
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-137 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-137-a-refuted-spec-claim-has-no-write-back-channel-at-the-plan-tier.md` § `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-137 Claim Labels: 6 verdicts, 4 corroborated + 2 unverifiable.

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/phase-2-refine/**` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/**` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/**` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-lessons/**` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_change_type_heuristic.py` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — carried from PLAN-TRUTH-119
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py` — carried from PLAN-TRUTH-134
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md` — carried from PLAN-TRUTH-134
- `test/plan-marshall/manage-solution-outline/` — carried from PLAN-TRUTH-134
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/` — carried from PLAN-TRUTH-137
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-security-audit.md` — carried from PLAN-TRUTH-137
- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — carried from PLAN-TRUTH-137
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/request-result-alignment.md` — added 2026-09-14, folded from `truthful-signals-010.md` finding 3
- `marketplace/bundles/plan-marshall/skills/manage-plan-documents/**` — added 2026-09-14, same fold (verify-against target for the proposed decision-log destination)

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-119-early-phase-gates-cannot-be-told-apart-from-confident-answers.md` (PLAN-TRUTH-119)
- `PLAN-TRUTH-134-the-scope-extractor-invents-paths-and-drops-bullets-and-reports-success.md` (PLAN-TRUTH-134)
- `PLAN-TRUTH-137-a-refuted-spec-claim-has-no-write-back-channel-at-the-plan-tier.md` (PLAN-TRUTH-137)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-151-early-phase-gates-the-outline-parser-and-the-plan-tier-claim-write-back.md"
```

## ⭐ FOLDED 2026-09-14 — OPERATOR DECISIONS MADE DURING EXECUTE DO NOT REACH THE SPEC

Forwarded via `truthful-signals-010.md` finding 3 (revision 3). Expected Surface EXTENDED in the same act
(see above) — this deliverable's own D6 ("a refutation has a write-back channel and it is not a return
payload") is the exact shape this fold widens: the missing channel is for operator answers, not only
agent refutations.

PLAN-TRUTH-035 carried "3 operator decisions SUPERSEDED the spec." The plan's opening intent IS captured
(`phase-1-init/templates/request.md`, already in this spec's surface), and `plan-retrospective`'s
`request-result-alignment.md` checks the result against that request — but mid-flight `AskUserQuestion`
answers that redefine the intent have no documented durable destination. The consequence is sharper here
than a generic gap: a request-result alignment check that compares against a request the operator already
superseded reports a divergence that is not one, or misses one that is. Lead, carried with its own caveat:
an append-only decision log per plan, written when an operator answer changes the contract, read by
request-result alignment as an amendment — modelled on an upstream tool's `audit.md` append-only-never-
edited property, the one piece of that source treated as prior art. ⛔ The claim that no such destination
exists today is from a targeted search, not an exhaustive one — verify against `manage-plan-documents`
before scoping (surface added above for exactly this).

## ⭐ FOLDED 2026-09-15 — OUTLINE DECLARED-INTENT GAP, A SELF-REVIEW CLUSTER, AND A FALSE-POSITIVE Q-GATE

Forwarded from `plan-truth-148-004.md`, `plan-truth-157-008..012.md` (all resolved `accepted` within
their own plans — corpus-learning value, not open work), and `review-apparatus-041.md` § C-019. Expected
Surface unchanged — `phase-3-outline/`, `phase-1-init/**`, `phase-2-refine/**` already cover all of these.

**Genuinely open: the outline declared-intent vocabulary has no third state for a gate-dependent file**
(`plan-truth-148-004`). Two deliverables each correctly declared `intent: write-replace` on a file a gate
deliverable ultimately decided did NOT need editing — both outcomes correct, but the vocabulary (only
`write-replace`/`read`) forces guessing at outline time, and the coverage metric then penalises exactly
the plan shape the gate exists to enable. Proposed: a third declared intent for gate-contingent files,
excluded from the coverage denominator (the way `read` already is) but kept in the scope-creep comparison.

**Self-review corpus lessons from PLAN-TRUTH-157's own outline/refine (all already `accepted`, recorded
here for the pattern):** an all-100 confidence score is a prompt to corroborate with first-party evidence,
not a score to argue down; a Design-notes classification should be derived from the deliverable's actual
`affected_files`, not from the mechanism it names in prose; an exclusion rationale settled for one
deliverable must be RE-TESTED against every other deliverable sharing the same coupling, not assumed to
generalize; when a request phrase ("pin to an opus tier") is satisfied for some pinned surfaces and
deliberately delegated for another, the delegation needs its own explicit record, not silence; and a
verification criterion for an invariant ("every such invocation still carries `--workflow`") must sit on
the deliverable that actually EDITS the guarded site, not only on sibling deliverables that reference it.

**A false-positive Q-Gate, corroborating the class from a different plan** (`review-apparatus-041` §
C-019): an outline Q-Gate reasoned over line ranges execution never touched, and predicted a defect that
never happened — the false-positive half of this deliverable's own subject (an early-phase gate reading
identically to a settled result), worth keeping distinct from the false-negative instances already
carried.

## ⭐ FOLDED 2026-09-15 (c) — AN OUTLINE THAT TRANSITIONED PAST ITS OWN Q-GATE, THREE CRITERIA WRITTEN AHEAD OF THEIR EVIDENCE, AND A MANDATED FLAG NO CLAIM CLASS COVERS

Forwarded from `api-sheriff-deployment-configurability-014.md` (bundling API-Sheriff PR #305's
`release-docs-and-tls-scenario-guide-001/-002/-003/-008`) and `api-sheriff-deployment-configurability-018.md`
(bundling `-006`, an orchestrator self-report). Expected Surface unchanged — `phase-3-outline/`,
`manage-solution-outline/**` and `persona-plan-orchestrator/standards/orchestration-model.md` are already
declared. Each item is a single-run lead, not re-verified against source by the relaying orchestrator.

**The genuine bug (`-008`) — phase-3-outline advanced itself to `4-plan` BEFORE the 3-outline q-gate ran.**
Its findings (`eb29c6`, `8c18c6`, `444e7e`) were filed against a phase already left; phase-4-plan does not
read 3-outline q-gate findings, so they would have been silently dropped. The orchestrator re-opened
3-outline by hand. This is the purest instance of D1's subject: a gate whose result arrives after the
transition it was meant to guard reads identically to a gate that passed. Lead: the outline agent returns
without calling the transition, and the `3-outline → 4-plan` transition refuses while any 3-outline q-gate
finding is `pending`. ⚠ Adjacent to `PLAN-TRUTH-147` D10 (a transition-time phase-array invariant) —
different invariant (pending findings, not the phase array); D0 records whether one guard carries both.

**Three outline-authoring disciplines, each an early-phase answer written ahead of its evidence:**

- `-001`: a deep-lane outline reached q-gate with zero CERTAIN_INCLUDE assessments recorded
  (`findings_store_state: missing`), so assessment coverage could not pass and missing-coverage could not be
  evaluated at all — 26 assessments were recorded only after q-gate fired.
- `-002`: a deliverable's criteria named a build lane (`jfr` profile image + `ImageMetadataJfrIT`) while its
  Verification Command was `verify -Ppre-commit`, which exercises neither — a criterion no command exercises
  is unverified, and phase-4 derives a verification step that never touches the only changed build input.
- `-003`: a "search returns only Y" criterion was written before running the search; running it found two
  unlisted legitimate hits and one listed file with no hit, so a literal verifier would have failed the
  deliverable. Lead: run the search at outline time and write the allow-list from its actual result.

**A claim class the Verify-First Contract does not name (`-018`/`-006`).** The API-Sheriff orchestrator's
own spec mandated `-Dsurefire.failIfNoSpecifiedTests=false` on a targeted-test example whose reactor
(`-pl api-sheriff -am`) contains no other module binding surefire, so the flag prevented nothing and only let
a misspelled selector pass with zero tests. The contract labels mechanisms, surfaces and counts; a
**spec-mandated command flag** slipped through as none of the three. Lead for D5 (the contract applied one
tier down) and for `orchestration-model.md` § Verify-First Contract: a mandated build flag is a claim, and a
flag that suppresses a failure mode must name a module in the command's actual reactor that would trigger
it.

## FOLDED 2026-09-24 — references entries need deliverable-surface coverage at outline time

From `truth-147-lane-reports-green-002.md` (candidate-lesson, 11 references-only files outside
every deliverable's declared surface, absorbed downstream by the manifest aspect): outline
verification checks declared-vs-realized recall but has no references-subset-declared direction.
Lead for D0/D4 (parser + recall coverage): an outline-phase check that every references entry is
covered by at least one deliverable's declared file surface or carries an explicit survey-scope
annotation. Adds no file surface: check inside the declared `manage-solution-outline/**`.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
