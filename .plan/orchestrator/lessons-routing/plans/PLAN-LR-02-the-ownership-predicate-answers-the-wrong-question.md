# PLAN-LR-02: The ownership predicate answers the wrong question

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

### Machine-derived collision map (2026-08-24, `corpus cross-check` — 8 epics / 7 live plans / 4 specs)

✅ **The epic's first cross-check. Exactly ONE cross-epic overlap across all four specs then staged**,
which is the expected shape for a new epic on a surface (`manage-lessons`) no sibling owns.

- ⚠ **`truthful-signals/PLAN-TRUTH-091` (`agent-facing-documentation-surfaces`) — 1 file,
  `manage-lessons/SKILL.md`. Ordering constraint only.** Its subject is agent-facing doc surfaces across
  many skills; this plan changes the guard's behaviour and its documented contract. Different subjects
  on one file. ⛔ **Serialize if both are live** — a doc-surface pass and a behaviour change to the same
  document conflict textually even though neither contests the other's claim.
- ✅ **No overlap with any live plan, and none with `code-intelligence-substrate` or `review-apparatus`.**

⛔ Re-derive at emit time — this map was taken before any plan in this epic ran, and PLAN-LR-05 has been
staged into the epic since.

## Claim Labels

- OBSERVED: the `wrong_store` guard's ownership predicate tests whether `marketplace/bundles/{prefix}` exists in the resolved main-anchored store repo — read at `manage-lessons/SKILL.md` § `:108` and § the `wrong_store` error-table row.
- OBSERVED: `API-Sheriff` has no `marketplace/bundles/` directory, so in a consumer repo every prefixed component is foreign including the client's own — read at `~/git/API-Sheriff/` § absent path.
- OBSERVED: `--allow-foreign-store` records nothing on the filed lesson — read at `manage-lessons/SKILL.md` § `:108`.
- OBSERVED: `PLAN-103` shipped as PR #1050 / `a7a657b00` with subject *"scope the store-ownership guard to prefixed components"*, fixing the prefix-LESS case — read at `truthful-signals/landings/PLAN-103.md` § Deliverable Fidelity.
- HYPOTHESIS: the prefix-less carve-out PLAN-103 shipped is still intact at HEAD and this plan need only extend the prefixed branch — confirm/refute at `manage-lessons/scripts/**` § the guard implementation (verify-at-outline).
- HYPOTHESIS: #1050 carries untriaged post-merge CodeRabbit findings on the same code path — confirm/refute via `ci pr comments --pr-number 1050` (verify-at-outline). **Recorded because inheriting one accidentally is cheap to avoid and expensive to discover.**
- Verify-first clause: the replacement predicate must be exercised in a CONSUMER-shaped repo before it is believed — in a marketplace-shaped repo the old and new predicates agree, so this repo's own suite cannot refute the defect.
