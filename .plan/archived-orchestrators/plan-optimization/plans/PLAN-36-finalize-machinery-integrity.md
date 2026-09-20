# PLAN-36: Finalize Machinery Does Not Match What Actually Runs

epic: plan-optimization
workstream: WS-10

> Staged 2026-07-21 from three defects surfaced by PLAN-29 (#969). **Combined deliberately** —
> see "Why one plan" below.
>
> ⚠ **This spec applies the new binding practice from lesson `2026-07-21-22-001`** (filed against
> `marshall-orchestrator` after verify-before-implement hit n=3): every mechanism below is
> explicitly labelled **OBSERVED** or **HYPOTHESIS**, and each hypothesis names the artifact that
> would confirm or refute it. Do not treat a hypothesis as a finding.

## Why one plan

Three defects, one theme: **phase-6-finalize's own machinery disagrees with what actually runs.**
The roster claims fewer steps than execute, a gate hard-fails on a clean tree, and steps can
report success without recording completion.

They are combined for a **surface** reason as much as a thematic one: all three live in
`phase-6-finalize` (its `SKILL.md` and `standards/`). Three separate plans would collide in the
same skill directory and have to be sequenced anyway — the disjointness model would force
serialization with none of the benefit of shared context.

## D1 — `pre-push-quality-gate` bundle-derivation invents a non-existent bundle

**Mechanism: OBSERVED** (orchestrator read the rule directly — not a hypothesis).

`standards/pre-push-quality-gate.md:56-63` "Derive unique bundle set", rule 3:

> *Otherwise, if the entry begins with `test/`, take path segment 1 as the bundle
> (e.g., `test/plan-marshall/.../test_foo.py` → `plan-marshall`).*

For `test/marketplace/targets/test_frontmatter.py` that yields segment 1 = **`marketplace`**,
which is **not a bundle** — it is the multi-target generator's own test tree. The gate then
invokes `quality-gate` against a bundle that does not exist and **hard-fails on a clean tree**.

Hit live in #969 (lesson `2026-07-21-21-002`). The plan worked **around** it — ran whole-tree
`quality-gate`, a strict superset, which passed. **The gate as written would halt any future plan
touching `test/marketplace/**`**, and PLAN-29 shipped changes to exactly those files, so the next
such plan hits it immediately.

**Acceptance**: `test/marketplace/**` derives no phantom bundle; an unresolvable derivation is
**diagnosable rather than a hard fail on a clean tree** (ADR-009 fail-closed still applies to real
failures — the objection is to failing on a *healthy* tree). Regression covering the exact path
shape.

## D2 — the dispatch roster is not authoritative over the steps that run

**Mechanism: PARTLY OBSERVED, PARTLY HYPOTHESIS.**

- **OBSERVED**: `phase-6-finalize/SKILL.md:127` states *"Of the **17** default + project finalize
  steps, **6 dispatch** and **11 run inline**"*, and names
  `standards/dispatch-inline-split.md` as *"the single source of truth the Execute Step Pipeline
  dispatch branch consumes."*
- **OBSERVED**: recent real runs executed **22** steps (#969), 21 (#963, #968), 20 (#964, #967).
- **HYPOTHESIS**: that the shortfall leaves ~5 steps with no dispatched/inline classification and
  therefore invisible to the roster's own coverage check (lesson `2026-07-21-22-002`).
  **Confirm/refute artifact**: read `standards/dispatch-inline-split.md` and enumerate its roster
  against a real composed `execution.toon` from an archived plan (#969's is at
  `.plan/local/archived-plans/2026-07-21-platform-agnostic-waiting-standard/`). Name the missing
  steps explicitly, or refute the shortfall.

**Acceptance**: the roster is either complete against a real manifest, or **derives** from the
manifest rather than restating a hand-maintained count. A hardcoded total in prose is the
stale-count class this epic has hit repeatedly — prefer derivation over a corrected constant.

## D3 — a step can report success without recording completion

**Mechanism: HYPOTHESIS — cause entirely unknown.**

- **OBSERVED (reported, not orchestrator-verified)**: in #969, `pre-submission-self-review`
  returned successfully **with a real finding** but never called `mark-step-done`. Correctly
  recorded `failed` per contract; finding fixed inline; retried once and recorded cleanly.
- **OBSERVED**: this is the **7th recurrence** of the family.
- **HYPOTHESIS**: the completion guard is evadable by a step that returns a success-shaped
  payload without the recording call — i.e. the contract is enforced by convention at the step,
  not structurally at the dispatcher.
  **Confirm/refute artifact**: the completion-guard implementation plus the `mark-step-done`
  call-path for dispatched steps; and the prior six recurrences in the lessons corpus — if they
  share one root cause, the family has an owner; if they are six different causes wearing one
  label, **say so and re-scope**, because "7 recurrences" would then be a taxonomy artifact
  rather than one defect.

**Acceptance**: either a structural enforcement point that a returning step cannot bypass, or —
if D3's investigation shows the seven are unrelated — a corrected taxonomy and a narrower fix.
**Seven recurrences means this family needs an owner, not another tally increment.** Do not ship
a seventh point-fix.

## Deliverables

1. **D1** — fix bundle derivation for `test/marketplace/**`; make unresolvable derivation
   diagnosable, not a clean-tree hard fail; regression.
2. **D2** — settle the roster hypothesis, then make the roster complete-or-derived; regression
   pinning roster-vs-manifest agreement.
3. **D3** — settle the completion-guard hypothesis (one root cause vs seven labels), then either
   enforce structurally or re-scope with the corrected taxonomy.

Three deliverables, comfortably under the split guard. D1 is independent and shippable alone;
D2 and D3 each gate on their own confirm/refute artifact.

## Expected Surface

- `phase-6-finalize/standards/pre-push-quality-gate.md` (**`:56-63`** — D1)
- `phase-6-finalize/SKILL.md` (**`:127`** — the 17-step claim — D2)
- `phase-6-finalize/standards/dispatch-inline-split.md` (D2)
- the completion-guard / `mark-step-done` enforcement path (locate at D3 — do NOT assume a file)
- `.plan/local/archived-plans/2026-07-21-platform-agnostic-waiting-standard/` (read-only evidence)
- tests under the phase-6-finalize / manifest suites

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **ADJACENT to PLAN-35** — **same file**: PLAN-35's surface includes
  `pre-push-quality-gate.md:34` (freshness-gate contract prose) while D1 edits `:56-63`
  (bundle derivation). Different sections, same document. **Sequence — do not run concurrently.**
  Suggested order: **PLAN-36 first** (three bounded fixes) then PLAN-35 (a five-deliverable
  consolidation), so the consolidation lands on a tree whose finalize machinery is already honest.
- Disjoint from PLAN-23/27 (build-maven / script-shared), PLAN-33 (session store), PLAN-34
  (steward + plugin cache).
- Related: PLAN-02 (#927) shipped finalize-step integrity work and PLAN-19 (#944) the
  queue-enforced enqueue — re-ground against both at outline rather than assuming virgin ground.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-36-finalize-machinery-integrity.md"

BINDING PRACTICE (lesson 2026-07-21-22-001, filed against marshall-orchestrator after verify-before-implement reached n=3 across PLAN-24/#963, PLAN-26/#964, PLAN-29/#969): every mechanism in this spec is labelled OBSERVED or HYPOTHESIS, and each hypothesis names its confirm/refute artifact. Honour those labels. Do not implement against a HYPOTHESIS before reading its named artifact, and if an artifact refutes the hypothesis, say so and re-scope rather than proceeding — three consecutive plans in this epic had a correct symptom and a falsified orchestrator-inferred mechanism, and in #969 an ADR's own claim was falsified at execute.

D1 mechanism is OBSERVED, not inferred: pre-push-quality-gate.md:56-63 rule 3 says "if the entry begins with test/, take path segment 1 as the bundle", so test/marketplace/targets/test_frontmatter.py yields segment 1 = "marketplace", which is not a bundle but the multi-target generator's own test tree; the gate then invokes quality-gate against a non-existent bundle and HARD-FAILS ON A CLEAN TREE. This is lesson 2026-07-21-21-002, hit live in #969 and worked around with a whole-tree quality-gate run (a strict superset, which passed). PLAN-29 shipped changes to exactly those files, so the next plan touching test/marketplace/** hits it immediately. Fail-closed per ADR-009 still applies to REAL failures — the objection is specifically to failing on a healthy tree.

D2 is PARTLY OBSERVED: phase-6-finalize/SKILL.md:127 states "Of the 17 default + project finalize steps, 6 dispatch and 11 run inline" and names standards/dispatch-inline-split.md as the single source of truth the dispatch branch consumes; real runs executed 22 steps (#969), 21 (#963, #968), 20 (#964, #967). The HYPOTHESIS is that ~5 steps therefore carry no dispatched/inline classification and are invisible to the roster's own coverage check (lesson 2026-07-21-22-002). CONFIRM/REFUTE ARTIFACT: read dispatch-inline-split.md and enumerate its roster against a real composed execution.toon from .plan/local/archived-plans/2026-07-21-platform-agnostic-waiting-standard/. Name the missing steps or refute the shortfall. Prefer DERIVING the roster from the manifest over correcting a hardcoded constant — a hardcoded total in prose is the stale-count class this epic keeps hitting.

D3 is a HYPOTHESIS with cause entirely unknown. OBSERVED (reported, not orchestrator-verified): in #969 pre-submission-self-review returned successfully WITH a real finding but never called mark-step-done; it was correctly recorded failed per contract, the finding fixed inline, and a single retry recorded cleanly. OBSERVED: this is the 7th recurrence of the family. HYPOTHESIS: the completion guard is evadable because the contract is enforced by convention at the step rather than structurally at the dispatcher. CONFIRM/REFUTE ARTIFACT: the completion-guard implementation and the mark-step-done call path for dispatched steps, PLUS the prior six recurrences in the lessons corpus — if they share one root cause the family has an owner; if they are six different causes wearing one label, SAY SO AND RE-SCOPE, because "7 recurrences" would then be a taxonomy artifact rather than one defect. Seven recurrences means this needs an owner, not another point-fix; do not ship a seventh.

SEQUENCING: this plan is ADJACENT to PLAN-35 in the SAME FILE — PLAN-35 touches pre-push-quality-gate.md:34 (freshness-gate contract prose), D1 edits :56-63 (bundle derivation). Do not run them concurrently.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-36.md is recorded}
