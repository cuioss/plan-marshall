# PLAN-TRUTH-128: The freshness gate says `fresh` for a tree it never examined

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-03; the overloaded token is read by a fail-closed push gate

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-128-the-freshness-gate-says-fresh-for-a-tree-it-never-examined.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Finding `a03f17` (`improvement`, `manage-tasks`), surfaced in another session's triage prompt as a
data-point: the gate returned **two different verdicts for one unchanged tree** — first `stale` /
`build_scope_narrow` after a ledger scan, then `fresh` / `not_necessary` short-circuiting *before* the
scan. That run's own push was not compromised (it rested on a green whole-tree verify at that tree).

⭐⭐ **Every mechanism claim below was derived first-party in this checkout at HEAD `30cd8aaf8`.** The
foreign run supplied the question; the diagnosis and the evidence are local.

## Objective

**`status: fresh` means two materially different things, and the consumer branches on the token alone.**

| What actually happened | Returned |
|---|---|
| the ledger was scanned and a successful build is citable on both dimensions | `status: fresh` |
| **no scan occurred** — `build-decision` ruled a build unnecessary for this footprint | `status: fresh` |

`_cmd_pre_commit_verify_freshness.py:517` calls `_build_necessity_verdict()` **first**, and on
`decision == not_necessary` returns `fresh` with the message *"Gate permitted without a ledger scan."*
And `push.md:44` states the consumer contract: *"The contract is **fail-closed**: only `status: fresh`
permits the executor to proceed."* ⇒ **A push proceeds on a gate that never looked.**

⛔ **This is the epic's archetype in its purest form: *not looking* renders identically to *looked and
found nothing wrong*.**

### ⭐⭐⭐ The decisive argument: this gate was ALREADY fixed for this exact class — on the other side

`push.md:52` records the prior fix in its own words:

> *"The `stale` `reason` MUST be carried into `display_detail` — it is the only thing that tells the
> operator what to do next… A `display_detail` that reports only the sha and ledger path hands a
> `build_killed` refusal to the operator indistinguishable from a `worktree_mutated` one, **which is the
> same discarded-discriminator defect this gate was fixed to stop.**"*

⇒ `stale` carries **nine** distinct reasons precisely so its routes can be told apart. `undecidable`
carries two (`no_registry`, `head_unresolvable`). **Only `fresh` is undifferentiated at the point the
consumer reads it** — and it is the one status that permits the push.

⭐ **The payload already knows the difference; the TOKEN collapses it.** `manage-tasks/SKILL.md:80`
documents the scan path as carrying `notation_cross_check` and `scope_cross_check`, which *"say whether
each was audited or merely undetermined"*, while the exempt path forwards only the verdict's `reason`.
⇒ The discriminators exist in the envelope. **The defect is that `push` branches on `status` and nothing
obliges it to read further.**

### ⛔ What is NOT the defect — read before changing anything

- **The short-circuit reasoning is SOUND and must survive.** *"No `kind=build` entry could ever legally
  be stamped for this footprint, so demanding one is an impossible demand rather than a gate."* Removing
  the exemption would make the gate un-passable for a footprint that legitimately needs no build.
- **The fail-closed direction is CORRECT.** `_build_necessity_verdict` degrades to
  `{'decision': 'build'}` on any exception, routing into the ledger scan. Do not weaken it.
- **The two observed verdicts were probably NOT contradictory**, which is why the finding's *"both
  cannot be right"* understates the problem. `should_execute_build` is keyed on the plan's **live
  footprint**, and the footprint moves as the plan commits — so the two calls likely answered a *changed*
  question and each was locally correct. ⭐⭐ **The defect survives that explanation intact**, and stating
  it this way is what stops a fixer from chasing a non-determinism bug that is not there.

## Deliverables

Five deliverables. D0 is a gate.

---

**D0 — GATE: settle the token shape, and derive whether the exempt path has ever gated a real push.**

- *(a) The token decision, recorded before any code changes.* Two admissible shapes:
  1. **A distinct status** (e.g. `not_required`) alongside `fresh` / `stale` / `undecidable`, with
     `push` deciding explicitly what it does with it; or
  2. **`fresh` retained with a MANDATORY discriminator** the consumer is obliged to read and record,
     mirroring what `stale`'s `reason` already does.
  ⭐ Shape 1 is the stronger fail-closed posture — a consumer that has not been updated cannot mistake
  the new token for a pass — but it is a **contract change for every consumer**, and the consumer set is
  D0(b). ⛔ Record the choice and its rationale; do not let the scorer's convenience pick it.
- *(b) The consumer population.* Derive every reader of this gate's status. **First-party floor,
  explicitly not the population:** `phase-6-finalize/standards/push.md` is the fail-closed consumer;
  `manage-tasks/SKILL.md`, `phase-5-execute/SKILL.md`, `phase-6-finalize/SKILL.md`,
  `pre-push-quality-gate.md`, `manage-change-ledger/SKILL.md`, `manage-config/SKILL.md`,
  `extension-api/build-systems-common.md` and `plan-marshall/execution.md` all reference the gate.
  Publish which of them BRANCH on the status versus merely describe it — those are different obligations
  and only the first breaks under shape 1.
- *(c) Has the exempt path ever permitted a push?* ⛔ **Unknown, and n=1 foreign.** The reporting run
  states its own push was covered by a real verify. Sweep the change-ledger / plan records for pushes
  taken on a `not_necessary` verdict and **publish the count with the population swept.** ⭐ A clean
  result is a genuine finding: it makes the defect latent, which changes urgency but not correctness.

---

**D1 — the exempt path stops sharing a token with the verified path.** Apply D0(a)'s chosen shape. ⛔
**Whichever is chosen, a reader must not be able to obtain a pass without learning that no scan
occurred.**

---

**D2 — `push` records WHICH kind of pass it acted on.** Today `push.md:48` reads `fresh → Proceed` and
records nothing about how the verdict was reached. ⇒ The push's own outcome record must name whether the
tree was **verified against the ledger** or **exempted without a scan**.

⭐ This mirrors the discipline `push.md:52` already imposes on the failure side — the `stale` reason is
carried into `display_detail` *"because it is the only thing that tells the operator what to do next"*.
**The same argument applies to a pass that was never checked**, and it is the half the prior fix did not
reach.

---

**D3 — the documentation must stop asserting the collapsed contract.** `manage-tasks/SKILL.md:80`
documents `fresh` as covering both cases in one sentence, and `push.md:44` states *"only `status: fresh`
permits the executor to proceed"*. Both are accurate about today's behaviour and both become wrong under
D1. ⛔ **Update them in the SAME change as the code** — a doc that describes the pre-fix contract is
exactly the divergence class this epic records.

---

**D4 — the tests, and the matched control is the whole point.** ⛔ Population-derived per this epic's
standing rule; publish the population size.

1. **The exempt path and the verified path are DISTINGUISHABLE from the return alone.** Two fixtures —
   one where `build-decision` rules `not_necessary`, one with a citable successful build row — assert
   two different observable outcomes. ⛔ **Without the second fixture the test passes on a gate that
   returns the same thing for everything**, which is the present defect.
2. **A consumer cannot obtain a pass without the discriminator.** Assert at the `push` branch, not only
   at the gate's return — the defect lives in the consumer's freedom to ignore the payload.
3. **The fail-closed degradation still holds**: an unobtainable verdict routes into the ledger scan.
   ⛔ This is a **regression guard on behaviour that is currently correct**; D1 must not weaken it while
   changing the token.
4. **The `stale` reason table is unchanged** — nine routes, still carried. ⚠ Cheap insurance: D1 touches
   the return shape of the same function, and this is the neighbouring contract most easily broken in
   passing.

## Claim Labels

Derived first-party at HEAD `30cd8aaf8` on 2026-09-03 unless marked otherwise.

- **OBSERVED** — `_cmd_pre_commit_verify_freshness.py:517` calls `_build_necessity_verdict()` before any
  other work; on `decision == not_necessary` it returns `status: fresh` with the message *"Gate permitted
  without a ledger scan."*
- **OBSERVED** — `_build_necessity_verdict` returns `{'decision': 'build'}` on any exception and on a
  non-dict verdict, documented as *"an unobtainable verdict must fail closed"*.
- **OBSERVED** — the gate's status vocabulary is exactly three tokens: `fresh`, `stale`, `undecidable`
  (two emission sites each in that module).
- **OBSERVED** — `push.md:44` states the fail-closed contract (*"only `status: fresh` permits the
  executor to proceed"*) and `:48-50` is the branch table keyed on status alone.
- **OBSERVED** — `push.md:52` records the prior discarded-discriminator fix on the `stale` side and names
  it *"the same discarded-discriminator defect this gate was fixed to stop."* ⇒ the precedent for D1/D2
  is this gate's own history.
- **OBSERVED** — `manage-tasks/SKILL.md:80` documents `fresh` as covering BOTH the `not_necessary`
  verdict and a citable successful build, and documents `notation_cross_check` / `scope_cross_check` as
  saying *"whether each was audited or merely undetermined"* on the scan path. ⇒ the overload is
  documented, and the envelope already carries discriminators the consumer is not obliged to read.
- **OBSERVED** — `stale` carries nine reasons and `undecidable` two; `fresh` carries none that the
  consumer must read.
- **REPORTED, NOT CORROBORATED** — the two-verdicts-on-one-tree observation itself, and the claim that
  that run's push was covered by a real verify. ⛔ Foreign session, not read here. ⚠ The defect does not
  depend on it: the overload is visible in source without any run.
- **HYPOTHESIS** — that the two observed verdicts differed because the live footprint moved between
  calls (so both were locally correct about different questions). Confirm/refute against
  `should_execute_build`'s footprint derivation (verify-at-outline). ⛔ **Either outcome leaves D1
  unchanged** — this hypothesis exists to stop a fixer chasing a non-determinism bug, not to gate the
  fix.
- **Verify-first clause** — before D1 changes the return shape, confirm no consumer treats an unknown
  status as a pass. A consumer defaulting to proceed would make shape 1 (a new token) actively dangerous
  and would force shape 2; that is a re-scope, not a detail.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py`
  — the short-circuit and the return shape (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` —
  the reason vocabulary and the cross-check discriminators (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — the gate contract at `:80`
  and § "Pre-Commit Verify Freshness" at `:146` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — the
  fail-closed consumer contract and its branch table (D2, D3)
- OBSERVED: `test/plan-marshall/manage-tasks/` — the D4 gate tests
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — the D4 consumer-branch test
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`,
  `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` — touched only if D0(b) finds
  they BRANCH on the status rather than merely describing it (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **Seamed to `PLAN-TRUTH-124` D1** (the shared verdict vocabulary). ⛔ **Do not coin a project-wide
  status vocabulary here** — this plan settles ONE gate's token. If `-124` has landed, D1 adopts its
  vocabulary; if not, D1 picks a local token and records that it may be renamed. **A local fix must not
  become a second cross-cutting vocabulary**, which is the defect `-124` exists to end.
- ⚠ **`PLAN-TRUTH-126` D4 is adjacent, not overlapping**: that plan makes an un-runnable *quality* guard
  say so; this one makes an un-scanned *freshness* pass say so. Same archetype, different gates, no
  shared file. ⛔ Do not merge them.
- ⚠ **`push.md` is heavily contended** — `-097` and `-095` have both touched it historically. **Re-derive
  from `corpus cross-check` at emit time; do not trust this note.**
- Adjacent to: `PLAN-TRUTH-119` (*early-phase gates cannot be told apart from confident answers*) is the
  same archetype scoped to **phases 1-4**; this gate is a phase-5→6 boundary. ⛔ Deliberately NOT folded
  there — folding would stretch `-119`'s declared scope, the staging error this epic records.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-128-the-freshness-gate-says-fresh-for-a-tree-it-never-examined.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-05 — `review-apparatus` forward (1 message)

- **`review-apparatus-031`** — *the freshness gate refuses without naming what satisfies it.*

  ⭐⭐ **The COMPLEMENT of this spec's own finding, from the other side of the same gate, and it should
  be shipped in the same act.** This spec owns the FALSE-POSITIVE direction: `status: fresh` is returned
  for a tree the gate never examined, so *not looking* renders identically to *looked and found nothing*.
  The sibling's item is the FALSE-NEGATIVE direction: the gate REFUSES and its refusal **does not name
  the condition that would satisfy it**, so the caller cannot tell a recoverable refusal from a
  structural one and guesses at a remedy.

  ⛔ **One return shape carries both.** A verdict token that cannot distinguish *scanned-and-clean* from
  *never-scanned* is the same design error as a refusal that cannot state its own discharge condition —
  in both cases the consumer branches on a token that under-determines the state. ⇒ **D1's return-shape
  work must serve the refusal path too**; landing only the `fresh` split leaves the gate half-honest and
  guarantees a second visit. ⚠ **Memory of a live instance**: a `freshness: build_scope_narrow` refusal
  cost a real run its push barrier, and `module-tests` was tried and REFUTED as the discharge — exactly
  the guess an unnamed condition invites.
