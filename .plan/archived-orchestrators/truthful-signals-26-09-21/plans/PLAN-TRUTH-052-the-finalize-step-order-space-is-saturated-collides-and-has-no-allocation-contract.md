# PLAN-TRUTH-052: the finalize step-order space is saturated, collides, and has no allocation contract

## ⛔⛔ SUPERSEDED 2026-08-03 — ABSORBED INTO `PLAN-TRUTH-050`. DO NOT EMIT.

**Operator decision: "no split".** The what/when/where of the plan's terminal report are one seam, and
splitting a seam is how this codebase produces half-fixes (#1080 closed write-before-merge and left
write-before-terminus; a renumber without a contract would re-accrete).

⇒ **All content below is retained as the evidence record and is live inside**
`PLAN-TRUTH-050-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see.md`
(**D0-D3, Phase 1**). ⚠ **Read 050, not this file, before implementing.**

---

epic: truthful-signals
workstream: WS-01

⭐⭐ **OPERATOR DIRECTIVE, 2026-08-03**: *"Eventually we should adapt numbering as well. We are still
pre 1.0."* ⇒ **The pre-1.0 window is the justification: renumbering is breaking for consumer projects
that declare their own step orders, and it is free only until the cut.** ⛔ *Leaving it is not neutral —
it is a choice with an expiry date* (framing borrowed from the `api-sheriff` report, cited not
re-derived).

## OBSERVED — the complete space, enumerated first-party 2026-08-03

Every `order:` declaration across `marketplace/` and `.claude/` — **27 declarations, and this is the
population, not a sample**:

```text
  3  finalize-step-sync-baseline      20  create-pr            990  finalize-step-review-retrospective [project]
  4  finalize-step-lessons-housekeeping [project]   21  finalize-step-era-stamp-fill [project]
  5  pre-push-quality-gate            22  ci-verify            991  lessons-capture
  6  finalize-step-plugin-doctor [project]   30  automatic-review     992  finalize-step-preference-emitter
  7  pre-submission-self-review       40  sonar-roundtrip      995  plan-retrospective
  8  finalize-step-simplify           62  adr-propose          998  record-metrics
  9  architecture-refresh             70  branch-cleanup       999  finalize-step-print-phase-breakdown
  9  finalize-step-security-audit     80  extension-api        1000 archive-plan
 10  push                             81  finalize-step-deploy-target [project]
                                      85  finalize-step-sync-plugin-cache [project]
```

### ⛔ Three distinct defects, not one tidiness complaint

**1. The terminal region is SATURATED.** `998 → 999 → 1000` is contiguous. ⇒ **`PLAN-TRUTH-051`'s
terminal emission step — an operator directive — cannot be inserted at all** without displacing an
existing step. **This is what turns "eventually" into "blocking".**

**2. A REAL COLLISION at order 9.** `architecture-refresh` and `finalize-step-security-audit` are both
phase-6 and both declare **`order: 9`**. ⇒ **Their relative order is undefined** — it falls out of
whatever the composer's tie-break happens to be, which no document states. ⚠ **`order: 10` also appears
twice** (`push`, and `canonical_verify` in **phase-5**) — ⭐ **that one is NOT a collision**, different
phase, and the distinction matters: it means the space is **per-phase**, which is itself nowhere stated.
⛔ **Do not "fix" the 10 pair.**

**3. No allocation contract, and third parties share the space.** Six of the 27 declarations come from
**project-local `.claude/skills/`** steps (4, 6, 21, 81, 85, 990) interleaved with ours. ⇒ **Consumer
projects allocate into the same flat integer space with no reserved band, no documented convention, and
no collision check.** The order-9 collision is the predictable result, and it is between **two of our
own** steps — so the mechanism does not even need a third party to fail.

⭐ **The shape of the space tells the story**: a dense `3..10` cluster, sparse `20..85`, then a jump to
`990..1000`. **Nobody designed this; it accreted**, and the `990+` band was clearly chosen to mean
"late" without anyone reserving room *inside* it.

## The rule this makes concrete

> **An ordering key that third parties write into needs an allocation contract, not just a comparison
> operator.** Sparse-by-convention is not sparse-by-guarantee, and a band with no reserved gaps is full
> the first time someone needs to insert.

## Deliverables

1. **D0 — GATE: derive the population and the semantics, both directions.** Every `order:` declaration
   (the 27 above are the current answer — **re-derive, do not inherit**), plus: **is the space per-phase
   or global?** (the 10 pair says per-phase; nothing states it), and **what is the tie-break for equal
   orders?** ⛔ **Read the composer, do not infer from output.** ⚠ Also enumerate consumer repos'
   declarations — ours is not the only tree that writes this key.
2. **D1 — a banded allocation contract with RESERVED gaps.** State the bands, what each means, and which
   ranges are **reserved for project-local / third-party steps** versus **owned by plan-marshall**.
   ⭐ **Leave documented insertion room inside every band** — the current defect is precisely a band with
   none. ⛔ **The contract is the deliverable; the renumbering is its consequence.** A renumbering
   without a stated contract re-creates the same accretion one generation later.
3. **D2 — resolve the order-9 collision deliberately.** ⚠ **Establish the intended order first** —
   `architecture-refresh` before or after `finalize-step-security-audit` is a real question with a real
   answer, and today's behaviour may already depend on the accidental tie-break. ⛔ **Do not simply
   renumber them apart and assume the current observed order was correct.**
4. **D3 — a duplicate/collision check that FAILS.** No two same-phase steps may declare the same order.
   ⛔ **Verify it fires on the live order-9 pair before the fix** — a guard never observed to fire is
   not a guard (archetype **n≥5**, one instance introduced BY a fix for it). ⭐ **Extend the existing
   `TestDefaultPhase6StepsMatchesDiscovery` lock-step pin rather than adding a competing checker** —
   that test already asserts the tuple ascends by frontmatter order, and a second, separate checker
   would be a fifth restatement of the same source.
5. **D4 — migrate, and state the breakage.** Renumber to the D1 contract. ⛔ **This breaks any consumer
   project pinning an order**, which is exactly why it happens **pre-1.0**. **Enumerate the known
   consumer repos and say which were checked** — ⚠ *a consumer list produced by looking is a sample*;
   derive it. ⭐ **Publish the old→new mapping**; a silent renumber is indistinguishable from a step
   quietly changing position.

⚠ Five deliverables. **D2 is the split point** (a specific bug that merely shares the file). Kept because
D3's control assertion needs the live collision as its fixture, and fixing D2 first would destroy it.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, whole population of both trees)**: all 27 declarations,
  the saturated `998/999/1000` tail, the order-9 same-phase collision, the order-10 cross-phase pair,
  and the six project-local declarations interleaved with ours.
- ⛔ **NOT ESTABLISHED — deliberately not claimed**: what the composer does with equal orders. **I did
  not read the tie-break.** The order-9 pair may be deterministic (by discovery order, by name) or may
  not. ⚠ **Do not report "undefined order" as an impact until the composer is read** — it is a
  *possible* behaviour, and this epic has just been burned twice by refutations scoped narrower than the
  behaviour.
- ⛔ **NOT ESTABLISHED**: whether any consumer project actually pins an order that D4 would break. The
  six `.claude/` declarations are **this** repo's project-local steps. **Consumer repos were not read.**
- **HYPOTHESIS**: the space is per-phase. **Strongly suggested by the 10 pair, stated nowhere.**
  Confirm at D0 — if it is global, the 10 pair *is* a collision and D2 grows.

## ⛔ How this finding was produced — recorded because it is the third instance this session

I asserted in `PLAN-TRUTH-051` that the terminal slot *"is between 998 and 1000"*, from the **four**
steps I had read. **A full sweep refuted it within the hour: 999 is occupied.**

⇒ **Third instance this session of *a list produced by looking is a sample, not an enumeration*** — and
it happened in the same drain where I folded two fresh instances of that archetype into
`PLAN-TRUTH-012`. ⭐ **Knowing an archetype does not protect against it; only running the enumeration
does.** The counter moves and the remedy stays the same: derive the population.

## Expected Surface

- **OBSERVED**: every `phase-6-finalize/{workflow,standards}/*.md` frontmatter, `plan-retrospective/SKILL.md`,
  `automatic-review/SKILL.md`, `extension-api/SKILL.md`, and the six `.claude/skills/*/SKILL.md`
- **OBSERVED**: `manage-execution-manifest/scripts/_manifest_core.py` — `DEFAULT_PHASE_6_STEPS`
- **HYPOTHESIS**: `extension-api` — where `order` is documented for third-party step authors
- **HYPOTHESIS**: `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py` — the pin to extend

## Dependencies and Sequencing

- ⛔⛔ **`PLAN-TRUTH-051` IS BLOCKED ON THIS** — its terminal step has nowhere to go until D1 lands.
  ⭐ **This inverts the natural priority**: renumbering reads like cleanup and is in fact the gate on an
  operator directive. ⚠ **A narrower alternative exists and should be weighed at outline**: displace
  `finalize-step-print-phase-breakdown` from 999 and ship 051 now, deferring the full contract. **State
  the choice; do not let 051 stall silently behind a large plan.**
- ⚠ **Cross-epic: `PLAN-CIS-034` owns the post-run band contract** (whether a `mutates_source: true`
  step may be post-run). **A banded allocation contract must not contradict it — notify and align.**
- ⚠ Adjacent to `PLAN-TRUTH-003` (migration shims have no expiry) — ⭐ **same pre-1.0 expiry logic.**
- ⚠ Adjacent to `PLAN-TRUTH-012` (declared-vs-derived divergence) — the lock-step pin is shared surface.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-052-the-finalize-step-order-space-is-saturated-collides-and-has-no-allocation-contract.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
