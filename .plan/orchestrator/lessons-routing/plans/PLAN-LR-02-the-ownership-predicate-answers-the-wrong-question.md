# PLAN-LR-02: The ownership predicate answers the wrong question

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/lessons-routing-carry-over.md` as PM-MCP input.
> Do NOT emit; un-park only by explicit operator decision.

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

Replace the `wrong_store` ownership predicate with one that answers **"can a reader of this store act
on this?"** instead of **"does this repo contain `marketplace/bundles/{prefix}`?"**

⛔ **The current predicate is not merely incomplete — in a consumer repo it returns the SAME answer for
both classes.** Verified: `API-Sheriff` has no `marketplace/bundles/` directory at all, so
`api-sheriff:maven-build` (the client's own build, entirely theirs to fix) fails the ownership test
**exactly as** `plan-marshall:build-maven` does. A discriminator that cannot separate the two cases it
exists to separate is not a discriminator.

⚠ **The predicate is not wrong in THIS repo** — here, bundle ownership and actionability coincide,
which is why the defect was invisible until a consumer checkout was sampled. **That coincidence is the
whole trap**, and any replacement must be tested in both shapes.

## ⛔⛔ THIS IS THE RESIDUE OF A SHIPPED FIX — read `PLAN-103` before touching anything

**`truthful-signals/PLAN-103` (`wrong-store-guard-refuses-project-local-lessons`) SHIPPED as PR #1050
/ `a7a657b00` on 2026-07-29**, merged as *"fix(manage-lessons): **scope the store-ownership guard to
prefixed components**"*. ⭐ **It fixed the PREFIX-LESS case**: a component naming no bundle (e.g.
`integration-tests`) is now project-local and files without `--allow-foreign-store`. That is the
current documented behaviour and it is correct.

⇒ **This plan owns the half PLAN-103 did NOT reach: the PREFIX-BEARING case.** Scoping the guard to
prefixed components made the predicate apply *only* where it is wrong — because for a prefixed
component the ownership test is still *"does `marketplace/bundles/{prefix}` exist here?"*, which in a
consumer repo is `no` for `api-sheriff:maven-build` and `plan-marshall:build-maven` alike.

⛔ **Two failure modes a run must avoid, and both are live risks:**

1. **Concluding the subject is closed.** PLAN-103's title reads as if it already fixed exactly this.
   It did not — read its landing (`truthful-signals/landings/PLAN-103.md`) and the merge subject line,
   not the plan title.
2. **Re-deriving PLAN-103's narrowing as if it were new.** The prefix-less carve-out is shipped,
   documented at `manage-lessons/SKILL.md:108`, and **must be preserved** — this plan extends the
   predicate, it does not revisit that scoping.

⚠ **PLAN-103 also carries recorded verification debt** — *"per-deliverable fidelity is not established
(no plan report supplied)"* — and a live watch that a post-merge CodeRabbit re-review of its deliberate
`from-error` contract change may have landed findings untriaged in `main`. ⭐ **Check #1050's comments
before extending this code path**: an untriaged finding on the exact function this plan modifies is
the cheapest possible thing to inherit accidentally.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: consume PLAN-LR-01 D4's recommendation and commit to derived or declared.** ⛔ Do not
re-open the analysis; do not re-derive the populations. Record the choice and its reasoning, and — if
this plan departs from LR-01's recommendation — **state why in the spec before writing code**.

**D1 — implement the audience axis.** Per D0. If **declared**, the argument is additive and the absent
case must have a defined, non-silent default. If **derived**, the derivation must pass the control case
in § Verification.

**D2 — the refusal names a route, not just a rejection.** `wrong_store` today ends the interaction.
Once WS-02's route exists, a refusal must tell the caller where the finding goes instead. ⚠ **This plan
does not build the route** (PLAN-LR-03 does) — it makes the refusal *routable*, and must ship a
coherent message even while the route is absent. ⛔ **It must not fall back to filing locally**: that is
the stranding this epic exists to end, and a fallback would reproduce it under a new name.

**D3 — retire or re-scope `--allow-foreign-store`.** It bypasses the guard **and leaves no trace**: a
lesson filed with it is afterwards indistinguishable from a natively-local one. ⛔ **That is the
laundering step by which the three stranded `cui-jsf-test-basic` lessons became invisible** (subject to
LR-01 D2 establishing which mechanism was actually used). Either remove it, or make its use recorded on
the lesson so a bypass stays visible to the next reader. ⭐ **A bypass that erases the evidence of its
own use is worse than no guard**, because it produces a corpus that looks clean.

**D4 — tests in BOTH repo shapes, with the coincidence as the control.** The predicate must be
exercised in a marketplace-shaped repo **and** a consumer-shaped one, asserting that a client's own
prefixed component is **local** in a consumer repo while a `plan-marshall:*` component is **upstream**
in that same repo. ⛔ **The load-bearing control is the consumer shape**, because in the marketplace
shape the old and new predicates agree — a test suite run only here would pass against the defect.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**`
- `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md`
- `test/plan-marshall/manage-lessons/**`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time** — this epic's corpus has never been
cross-checked against its four siblings.

- ⛔ **Depends on PLAN-LR-01 (hard).** D0 consumes its D4.
- ⚠ **PLAN-LR-03 consumes this plan's axis.** Serialize; do not build the route against a provisional
  classification.

### Machine-derived collision map — STALE, superseded below (originally 2026-08-24, 8 epics / 7 live
plans / 4 specs)

⛔⛔ **RETIRED at cleanup 2026-09-23.** The `PLAN-TRUTH-091` ordering constraint this section named is
now INERT: `truthful-signals-26-09-21`'s `PLAN-TRUTH-091` is `superseded` (by `PLAN-TRUTH-155`) and that
whole epic is `phase: closed` — no live serialization constraint remains from that source. The original
"exactly ONE overlap across 8 epics" figure is also stale on its face — the epic population has grown to
24 active epics since (see R14/R17 in `epic.md`) — but re-deriving that FULL figure is `corpus
cross-check`'s job at emit time, not this note's; this section only retires the one constraint it named
that has since resolved. ⛔ **Re-derive fully with `corpus cross-check` at emit time** — do not treat
"the named constraint is inert" as "no constraint exists."

## Claim Labels

- OBSERVED: the `wrong_store` guard's ownership predicate tests whether `marketplace/bundles/{prefix}` exists in the resolved main-anchored store repo — read at `manage-lessons/SKILL.md` § `:108` and § the `wrong_store` error-table row.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: marketplace_paths.py:691-734 main_anchored_store_owns_bundle checks (main_root / MARKETPLACE_BUNDLES_PATH / bundle).is_dir(); consumed at _lessons_io.py:226-235
- OBSERVED: `API-Sheriff` has no `marketplace/bundles/` directory, so in a consumer repo every prefixed component is foreign including the client's own — read at `~/git/API-Sheriff/` § absent path.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: git -C ~/git/API-Sheriff ls-files marketplace returns empty
- OBSERVED: `--allow-foreign-store` records nothing on the filed lesson — read at `manage-lessons/SKILL.md` § `:108`.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: manage-lessons/SKILL.md:108; _lessons_io.py:218-219 confirm no recording on override
- OBSERVED: `PLAN-103` shipped as PR #1050 / `a7a657b00` with subject *"scope the store-ownership guard to prefixed components"*, fixing the prefix-LESS case — read at `truthful-signals/landings/PLAN-103.md` § Deliverable Fidelity.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: git log --oneline -1 a7a657b00 -> fix(manage-lessons): scope the store-ownership guard to prefixed components (#1050); orchestrator queue row PLAN-103 = shipped, pr 1050, landings/PLAN-103.md
- HYPOTHESIS: the prefix-less carve-out PLAN-103 shipped is still intact at HEAD and this plan need only extend the prefixed branch — confirm/refute at `manage-lessons/scripts/**` § the guard implementation (verify-at-outline).
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: _lessons_io.py:221-224 - if ':' not in component: return (project-local by construction), documented at SKILL.md:108; extendable branch at 226-235 as the spec assumes
- HYPOTHESIS: #1050 carries untriaged post-merge CodeRabbit findings on the same code path — DISCHARGED at cleanup 2026-09-23: `ci pr comments --pr-number 1050` shows both inline actionable findings `resolved: true`, each tagged "Addressed in commit 28a1e04", answered, with a completed re-review. Nothing to inherit — this plan may proceed without re-checking #1050's comment thread.
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: ci pr comments --pr-number 1050: both inline actionable findings resolved:true, each tagged 'Addressed in commit 28a1e04', answered, completed re-review. Discharged - spec text updated, nothing to inherit
- Verify-first clause: the replacement predicate must be exercised in a CONSUMER-shaped repo before it is believed — in a marketplace-shaped repo the old and new predicates agree, so this repo's own suite cannot refute the defect.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: predicate unchanged at HEAD (marketplace_paths.py:691-734); existing tests test_add_guard_component_store.py + test_add_wrong_store_guard.py override short-circuits to True at :730-731, reinforcing the clause
