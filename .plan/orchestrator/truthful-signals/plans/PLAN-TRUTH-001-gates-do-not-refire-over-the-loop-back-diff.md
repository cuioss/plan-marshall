# PLAN-TRUTH-001: Finalize gates do not re-fire over the loop-back diff that introduced the defects

> Renamed from **PLAN-113** on 2026-07-30 (see `plan-id-rename-map.md`). ⛔ `code-intelligence-substrate`'s
> **PLAN-CIS-011** (ex-PLAN-121) carries a hard constraint that THIS plan lands first — the id moved on
> both sides, the constraint did not.

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-29 from inbox `self-review-cannot-see-an-unreachable-guard-005` (PLAN-81 / #1042),
> corroborated by `runnable-slice-keys-…-015` (PLAN-89 / #1044).

## Objective

`pre-submission-self-review` is **not in `HEAD_DEPENDENT_STEPS`**, so it does not re-fire over a
loop-back diff. On #1042 that diff introduced **three defects**, none of which the gate ever saw —
and the gate still reported **"clean: 101 candidates examined, no check matched"**. Make the
head-dependent step set **derived from what a step actually reads**, so a gate whose verdict depends
on HEAD cannot silently certify a diff it never examined.

## The defect, and why the reported verdict was honest but useless

⚠ **The plan followed the documented rule correctly.** The rule says skip; it skipped. **This is a
contract defect, not an execution defect** — and the operator flagged it as such.

The consequence is the sharp part: the loop-back diff on #1042 carried **all three** escaped defects
(a mis-scoped guard inside the guard-detector, a fifth hand-maintained registry mirror, and a
terminal-width-conditional vacuous test guard). `pre-submission-self-review`'s *"clean, 101
candidates examined"* was **literally true of the pre-loop-back diff and silent about the one that
mattered.** ⭐ **A verdict scoped to a stale input is not a weaker signal — it is a confident signal
about the wrong thing**, which is this epic's exact theme.

**Second, independent instance:** `runnable-slice-…-015` — *"a recorded `ci-verify` green survives
the force-push that invalidates it."* Same shape: an assertion about a HEAD that no longer exists.

⇒ **The population is almost certainly larger than these two steps.** D1 must derive it.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the head-dependent population.** ⛔ **Do not patch the two
   steps this spec names — they are a SAMPLE.** For every finalize step, establish whether its
   verdict depends on the diff/HEAD it was computed against. The discriminator is *"would this
   verdict change if HEAD changed?"*, not whether the step happens to be listed today.
2. **D2 — reconcile `HEAD_DEPENDENT_STEPS` against D1's derived set**, and make the membership
   **derived or asserted-with-a-guard**, not a hand-maintained list. ⚠ A hand-maintained mirror of a
   derived set is the archetype this epic has now recorded **five times** — do not create a sixth.
3. **D3 — a stale verdict is INVALIDATED, not silently retained.** When a step's input HEAD is
   superseded (loop-back, force-push, rebase), its recorded outcome must be marked stale and either
   re-run or reported as unverified. ⛔ **Never let a green computed against an old HEAD stand as a
   green for the new one.**
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A loop-back commit re-fires
   `pre-submission-self-review`. (b) A force-push invalidates a recorded `ci-verify` green.
   (c) The head-dependent set is derived and its derivation is asserted non-empty **and** contains
   both known members — the positive-population guard.
5. **D5 — FOLDED IN 2026-07-29 (operator decision): the finalize classification SSOT is WRONG, and
   its guard cannot see it.** Same document as D1–D4 (`phase-6-finalize`), so it ships here rather
   than as its own plan.
   - **D5a — correct the classification.** `standards/dispatch-inline-split.md:23` classifies
     `default:architecture-refresh` **dispatched**; it must be **inline**. The step doc
     (`standards/architecture-refresh.md:26`) carries the binding mechanism: Tier-1 `prompt` mode
     requires `AskUserQuestion`, which **a dispatched leaf cannot fire** (leaf-cannot-prompt
     invariant). ⛔ **Delete the `:23` rationale, do not reword it** — "the dispatching tier governs
     the classification" conflates *a sub-dispatch an inline step makes* with *the step being
     dispatched*, and under that rule every inline step that spawns anything reclassifies.
   - ~~**D5b — derive the mismatch population**~~ and ~~**D5c — close the roster-test blind spot**~~
     — ⛔ **REMOVED 2026-07-29. Owned by `code-intelligence-substrate` PLAN-121
     (`finalize-dispatch-manifest-observability`).** This is an **authoritative** answer, not an
     inference: that epic's orchestrator read both specs directly and replied via
     `code-intelligence-substrate-002.md`. Its § (c) already carries the dual classification *and*
     the finding that the closure test is vacuous ("opens the file but never asserts
     classification"), with the instruction to verify the new assertion FAILS against the divergent
     state first; its § (g) already requires the divergent set be derived population-wise.
     ⚠ **PLAN-120 is NOT the owner** — it owns the adjacent evidence seam. My earlier slug-inference
     named PLAN-120 and was **wrong**; do not reintroduce it.
     ⛔ **Do not rebuild D5b/D5c here. Two plans against one defect is the duplicate-work failure the
     disjointness rule exists to prevent.**
   - **D5d — reconcile the five `SKILL.md` inline-only enumerations** (`:607`, `:667`, `:889`,
     `:992`, `:1016`) so all sites and the SSOT agree. ⭐ **Preferred fix direction, from an
     independent second observation** (`end-phase-replace-not-accumulate-004`, self-review finding
     `dc2c77`): the defect is `SKILL.md` **duplicating a fact whose SSOT it itself designates**, so
     `SKILL.md` should hold **at most a link**, not a copy. Removing the duplication beats
     synchronising it.
   - ⚠ **D5 is now D5a + D5d + D5e only.** It is a doc-correctness fix, not a detector build — the
     detector half moved to the sibling. Re-check this plan's deliverable count and surface after the
     removal: it may no longer widen into the roster test at all.
   - ⭐ **OBSERVATION COUNT IS NOW SIX** (folded 2026-07-29 from inbox
     `build-tests-do-not-neutralize-daemon-routing-009/010`, the fifth and sixth independent sightings
     after the test-suite-quality handover, #1040, the live finalize run, and PLAN-110's in-passing
     find). **Stop treating this as a doc-tidiness item.**
   - ⛔ **NEW — the contradiction has a RUNTIME consequence, not just a documentation one.** One of
     the folded messages reports that the roster contradiction *"produces a live dispatch-audit
     violation"*: the audit classifies the step against the roster while the step actually runs
     inline, so the audit records a violation for correct behaviour. **This upgrades D5a from a prose
     correction to a fix with an observable downstream effect** — and it means a reader who "fixes"
     the audit to match the roster would be hard-coding the wrong answer. **Establish the audit's
     reading at D5a before editing either side.**
   - ⭐ **CORROBORATED 2026-07-29 by a named audit code.** PLAN-110's retrospective independently
     logged it as **`dispatch_coverage_violation`**, after that plan **ran `architecture-refresh`
     inline against the dispatched roster** — because *a leaf structurally cannot fire its
     `AskUserQuestion`*. That is the mechanism in `architecture-refresh.md:26` observed executing, not
     merely documented. ⛔ **The roster is the side that is wrong, and there is now an audit code
     naming the disagreement** — search for that code when scoping D5a; it is the cheapest handle on
     every affected site.
   - **D5e — test, verified to FAIL pre-fix:** the cross-document consistency assertion goes red on
     the current `:23` classification.
   - ➡ **CROSS-EPIC (2026-07-29):** forwarded to `code-intelligence-substrate` as
     `truthful-signals-011.md`. **D5b and D5c are the overlap** — if that epic confirms PLAN-120 or
     PLAN-121 already owns the derived cross-document detector, **drop D5b/D5c from this plan and
     ship D5a/D5d only**. ⛔ **Do NOT block on the reply.** Absent a confirmed "yes", D5b/D5c stay
     here — an unanswered forward is not a transfer of ownership.

## Claim Labels

- OBSERVED (message-supplied + operator paste, #1042): `pre-submission-self-review` is absent from
  `HEAD_DEPENDENT_STEPS`; it did not re-fire; the loop-back diff carried all three escaped defects;
  the gate reported clean over 101 candidates.
- OBSERVED (message-supplied, #1044): a recorded `ci-verify` green survived an invalidating
  force-push.
- HYPOTHESIS: the head-dependent population is larger than these two — confirm/refute at D1's
  derivation (verify-at-outline). **An asserted ABSENCE of further members is verified exactly like
  an asserted presence.**
- Verify-first clause: re-read `HEAD_DEPENDENT_STEPS` and its consumers at HEAD before scoping —
  #1042 and #1044 both landed in this surface. **Verify by SYMBOL, not line number.**
- OBSERVED (orchestrator-verified 2026-07-29, D5): `dispatch-inline-split.md:3` declares itself SSOT;
  `:23` classifies `architecture-refresh` **dispatched**; `architecture-refresh.md:26` says
  **inline** and gives the `AskUserQuestion` mechanism; `SKILL.md` says inline-only at `:607`,
  `:667`, `:889`, `:992`, `:1016`. All five sites read directly from the marketplace source.
- OBSERVED (orchestrator-verified 2026-07-29, D5c): `test_dispatch_roster_closure.py` asserts roster
  coverage vs the `marshal.json` registry, roster disjointness, absence of count claims, and the
  `SKILL.md` Step 3 dispatch branches — and passes today.
- HYPOTHESIS (D5b, verify-at-outline): `architecture-refresh` is the ONLY step whose roster
  classification contradicts its own standards doc. **Confirm/refute artifact:** the derived
  per-step comparison in D5b over `marshal.json` → `plan.phase-6-finalize.steps`. ⛔ Treat the
  single named step as a sample until that derivation says otherwise.
- ⚠ Line numbers above are OBSERVED at 2026-07-29 HEAD and `phase-6-finalize` is a hot surface
  (PLAN-112 is LAUNCHED into it). **Re-ground by SYMBOL at outline.**

## Expected Surface

- HYPOTHESIS: `HEAD_DEPENDENT_STEPS` and its consumer in `phase-6-finalize` (verify-at-outline)
- HYPOTHESIS: the `ci-verify` outcome record (verify-at-outline)
- OBSERVED: the corresponding finalize test modules
- OBSERVED (D5): `phase-6-finalize/standards/dispatch-inline-split.md`
- OBSERVED (D5): `phase-6-finalize/SKILL.md` (the five inline-only enumeration sites)
- OBSERVED (D5): `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`
- HYPOTHESIS (D5b): further steps whose roster row contradicts their standards doc (verify-at-outline)
- ⛔ **Surface note:** D5 widens this plan's footprint into `dispatch-inline-split.md` and the roster
  test. **PLAN-112 is LAUNCHED into `phase-6-finalize`** — the pre-existing "sequence, never pair"
  rule against PLAN-112/PLAN-111 now covers strictly more shared surface. Re-check at emit.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⛔ **PLAN-112** (finalize ceremony pre-filter) and **PLAN-111** (finalize comment
  barrier) — all three touch `phase-6-finalize`. **Sequence, never pair.** PLAN-111 is LAUNCHED.
- Adjacent to: `code-intelligence-substrate` owns the finalize *evidence* and *step-contract* seams
  — **different epic, check across the boundary before emitting.** ⛔ **ID CORRECTION
  (2026-07-29):** this line previously cited that epic's **PLAN-104/64**. Those IDs exist in
  **neither** epic's `status.json` (verified against both queues), and the attribution to the
  sibling is **itself unverified** — this epic's own stale generated START-HERE block still listed
  PLAN-64/104 as ITS OWN queue rows. Candidate successors by slug are **PLAN-120**
  (`finalize-dispatch-evidence-is-missing`) and **PLAN-121**
  (`finalize-dispatch-manifest-observability`). ⚠ **Both the successor identity AND the cross-epic
  attribution are inferred, not confirmed** (the carve-out bars reading another epic's specs).
  **Re-resolve against the sibling queue by SLUG before emitting** — do not trust these numbers.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-001-gates-do-not-refire-over-the-loop-back-diff.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
