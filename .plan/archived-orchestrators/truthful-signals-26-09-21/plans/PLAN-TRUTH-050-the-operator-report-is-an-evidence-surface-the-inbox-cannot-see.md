# PLAN-TRUTH-050: the plan's terminal report — one emission, at the end, in a slot that exists

epic: truthful-signals
workstream: WS-01

⭐⭐ **CONSOLIDATED 2026-08-03 AT OPERATOR DIRECTION — "no split".** This plan absorbs and supersedes
`PLAN-TRUTH-051` (the emission must be terminal, in an orchestrator-only step) and `PLAN-TRUTH-052`
(the step-order space is saturated, collides, and has no allocation contract). Both rows are
`superseded`; their specs retain pointers here.

⛔ **The scope-bloat guard is OVERRIDDEN by explicit operator decision, and the rationale is recorded
here rather than assumed** — as the standing correction requires. ⭐ **The argument for the override is
strong and is the epic's own thesis**: these three were one seam described from three ends, and
**splitting a seam is precisely how this codebase produces half-fixes.** #1080 fixed write-before-merge
and left write-before-terminus. A renumber without a contract would re-accrete. A landing carrying more
facts, emitted at the same wrong time, still cannot carry the ones produced after it. ⚠ **The honest
risk of one plan is a long run with many loop-backs** — the very cost `PLAN-TRUTH-048` measures. **Sized
deliberately, not overlooked.**

## Objective

A plan reports its outcome to two audiences over two channels, at a moment when neither channel can
yet carry the truth, into an ordering space with no room to fix it. The inbox receives narrative
while the operator report receives per-step outcomes, totals and repo state — **not the same facts**;
the landing is emitted at `order: 991`, three steps and two producers before the run ends; and
`998 → 999 → 1000` is contiguous, so there is no slot for a genuinely terminal step. This plan makes
the terminal report one emission, at the end, in a slot that exists. Consolidated at operator
direction ("no split") from the former `-051` and `-052`.

⛔ Internal deliverable order is load-bearing: **D3 must FIRE on the live order-9 collision BEFORE
D2 fixes it.**
## The one defect, stated once

> **A plan reports its outcome to two audiences over two channels, at a time when neither channel can
> yet carry the truth, into an ordering space with no room to fix it.**

| End | Symptom |
|---|---|
| **What** (was 050) | The inbox gets narrative; the operator report gets per-step outcomes, totals, repo state. **They are not the same facts.** |
| **When** (was 051) | The landing is emitted at `order: 991` — **3 steps and 2 producers before the run ends.** |
| **Where** (was 052) | `998 → 999 → 1000` is contiguous. **There is no slot for a terminal step.** |

## OBSERVED — all first-party unless labelled

### A. The channel gap is systematic, and cross-repo

**Seven findings across two of OUR runs existed only in the operator report**: the fourth token total
(10.4M vs 10.06M — **3.4% apart, the magnitude that gets quoted rather than investigated**);
`lessons-housekeeping`'s `0 removed, 0 promoted, 0 adapted, 180 retained` on a run whose own log declared
its input unavailable; the **runtime** step order (not the order the merged tree shows); `ci pr merge`
returning `merged: true` on an unmerged branch; the 6.2M total that exposed the three-way disagreement;
the split guard never evaluated; the pr-agent withdrawal.

⭐ **Operator, first-party**: *"After the last plans I started again pasting the result and **always** the
result has additional infos."* ⇒ **Not an incident. Every run.**

⭐⭐ **CROSS-REPO CORROBORATION** (relayed by the operator from an `api-sheriff` orchestrator, its
`PLAN-37` at `36508b2`): that epic **drained and reconciled correctly from its inbox** — shipped, landing
written, rows stamped, spec archived — **and the paste still carried three things the inbox lacked**: two
pre-merge-fixed security regressions, a **version-cut deadline** on two standing public elements, and the
routing decision for that residue. ⇒ ⛔ **The gap is a property of the CHANNEL, not of drain
discipline.** Population: **two epics, two repositories.**

⚠ **Claim label**: second-hand to us and unverifiable from this checkout. ⭐ **But the fact this plan
needs — that a paste carried what the inbox did not — is established by the act of pasting**,
independently of that epic's technical claims.

### B. The emission is not terminal

`DEFAULT_PHASE_6_STEPS`, read from `_manifest_core.py`:

| Step | `order` | Produces what the landing cannot see |
|---|---:|---|
| `branch-cleanup` | **70** | merge SHA, merge outcome |
| **`lessons-capture`** | **991** | ← **the `kind: landing` emission is HERE** |
| `record-metrics` | **998** | the run's token totals |
| `archive-plan` | **1000** | the archive path |

⭐ `archive-plan` is the hard boundary and the source says why: *"It runs last because it moves the plan
directory out from under every later reader."*

⛔⛔ **`PLAN-TRUTH-037`'s retirement was OVER-BROAD, and it was mine.** 037 D1 said exactly this
(*"the landing becomes a terminal action, anchored on the plan's terminal state"*). I marked it
`superseded` because #1080 moved `lessons-capture` into a post-merge band at 991. **That closed
write-before-MERGE and left write-before-TERMINUS open — post-merge is not terminal.**
⭐⭐ **And I held the disproving fact**: in the *same drain* I recorded `plan-retrospective 995 <
record-metrics 998` for `PLAN-TRUTH-035`, then never ran the identical arithmetic on the step I was
retiring. ⇒ **A retirement justified by a sibling's evidence still needs the retiring epic's own
arithmetic.** 037 stays `superseded`; this plan is its live residue.

### C. The order space is saturated, collides, and has no contract

**Whole population — 27 `order:` declarations across `marketplace/` and `.claude/`:**

```text
  3 sync-baseline        20 create-pr        990 review-retrospective [project]
  4 lessons-housekeeping [project]   21 era-stamp-fill [project]
  5 pre-push-quality-gate 22 ci-verify       991 lessons-capture
  6 plugin-doctor [project]  30 automatic-review  992 preference-emitter
  7 pre-submission-self-review  40 sonar-roundtrip  995 plan-retrospective
  8 simplify              62 adr-propose     998 record-metrics
  9 architecture-refresh  70 branch-cleanup  999 print-phase-breakdown
  9 security-audit        80 extension-api  1000 archive-plan
 10 push                  81 deploy-target [project]
                          85 sync-plugin-cache [project]
```

1. ⛔ **Terminal region SATURATED** — `998 → 999 → 1000` contiguous. **No slot exists.**
2. ⛔ **Real same-phase COLLISION at `order: 9`** — `architecture-refresh` and
   `finalize-step-security-audit`. ⚠ `order: 10` appears twice too but is **cross-phase** (`push` ph-6 /
   `canonical_verify` ph-5) — **NOT a collision, do not "fix" it.** ⭐ It is also the *only* evidence the
   space is per-phase, which is **stated nowhere.**
3. ⛔ **No allocation contract** — **6 of 27** declarations are project-local `.claude/` steps (4, 6, 21,
   81, 85, 990) interleaved with ours: third parties allocate into one flat integer space with no
   reserved band and no collision check. ⭐ **The live collision is between two of OUR OWN steps**, so
   the mechanism needs no third party to fail.

⭐ Shape: dense `3..10`, sparse `20..85`, jump to `990..1000`. **Accreted, not designed** — the late band
means "late" with no room reserved inside it.

⭐⭐ **OPERATOR: *"we are still pre 1.0"*** — renumbering breaks consumer projects that pin an order, and
it is free **only until the cut**. ⛔ *Leaving it is not neutral; it is a choice with an expiry date.*

## The rules this makes concrete

> **A terminal report must be a terminal action.** Emitting it earlier does not make it early — it makes
> it a **forecast presented as a record**.

> **An ordering key that third parties write into needs an allocation contract, not just a comparison
> operator.** Sparse-by-convention is not sparse-by-guarantee; a band with no reserved gaps is full the
> first time someone needs to insert.

## ⛔⛔ 2026-08-03 — THE SHARPEST EVIDENCE YET, from PLAN-TRUTH-035 / #1083 (`-008`, `-011`)

### 1. A plan about measurement truth audited itself against a stale, un-enriched store

`phase_6.steps` for that plan: `branch-cleanup` **16** → `plan-retrospective` **17** → `record-metrics`
**20**. ⇒ **`enrich` runs three positions AFTER the retrospective that consumes its output.**

Observable in that plan's own artifacts:

- `metrics.md` was **~3 hours stale at read time** (`Generated: 09:22:33Z`; finalize ran to 12:39), and
  rendered `Closes: 2` for `5-execute` while `work/metrics.toon` recorded `close_count: 3`.
- **`6-finalize` understated by ~1.03M tokens**: `dispatch_boundary_total: 1,345,299` on record vs
  **2,372,638** across the 13 rows on disk.
- ⛔⛔ **Every `enrich`-produced field absent from every phase row** — no `subagent_samples`, no
  four-field usage, **no `billing_weighted_total`.**

⭐⭐ **The consequence names this plan's thesis exactly**: that plan's **D4 (declare partiality) and D5
(surface billing as a first-class cost figure) shipped, passed verification, and are OPERATIONALLY INERT
IN THEIR OWN OUTPUT.** Every phase renders *"coverage undecidable"*; the `Billing (cost)` column is `-`
for all six phases.

> **The plan was raised because the operator asked "why did this cost so much?" The report now has a
> cost column, and it is empty.**

⚠ **And the operator's own report says the deliverable IS working (29.5M billing).** ⭐ **Both are true
at different sampling points** — `record-metrics` (20) populates what `plan-retrospective` (17) could not
see. **That is this plan's subject stated by the machinery itself.**

### 2. ⛔ A SECOND, INDEPENDENT defect at the same seam: the retrospective REBINDS the session it measures

`plan-retrospective` Step 1 **unconditionally** runs `platform_runtime session capture --plan-id {id}`,
which stores the **currently running** session into `status.metadata.session_id`. Observed live:

| when | `status.metadata.session_id` |
|---|---|
| before Step 1 | `39786697-…` (ran phases 1-5 and most of finalize) |
| after Step 1 | `43c13d58-…` (**the retrospective dispatch's own session**) |

⇒ `manage-metrics enrich --session-id {id}` — **the only producer** of `subagent_samples`, the four-field
view and `billing_weighted_total` — is invoked by `record-metrics` at position 20 and **resolves the
session from that rebound value.** On this plan it was armed to enrich against a session containing
**none of phases 1-5**.

⛔ **Conditional on cross-session resume, which is why it has not been universally visible** — and this
epic's runs are routinely multi-session (18h53m wall against 3h17m worked).

⇒ ⭐ **This is NOT fixed by re-ordering.** Moving the retrospective later still leaves an unconditional
rebind of a field a later step reads. **D4/D5 must carry a deliverable for it**: the retrospective must
not overwrite a binding it does not own, or must capture into a field of its own.

### 3. What this changes about scope

⛔ **The ordering half and the rebinding half must be fixed together** — fixing the order alone leaves a
mis-attributed enrichment; fixing the rebind alone leaves the retrospective reading a store that has not
been enriched. ⭐ **Neither is sufficient, which is the operator's "no split" argument arriving again on
its own.**

## Deliverables

⚠ **Nine deliverables — far past the guard, by operator decision. Sequenced so the gate work lands
first.**

### Phase 1 — the space (was 052)

1. **D0 — GATE: derive the population and the semantics, both directions.** Every `order:` declaration
   (**re-derive; the 27 above is today's answer, not an inheritance**), plus: **is the space per-phase or
   global?** and **what is the tie-break for equal orders?** ⛔ **Read the composer — do not infer from
   output.** ⚠ Enumerate consumer repos' declarations too; ours is not the only tree writing this key.
2. **D1 — a banded allocation contract with RESERVED gaps.** State the bands, their meaning, and which
   ranges are **reserved for project-local/third-party** vs **owned by plan-marshall**. ⭐ **Documented
   insertion room inside every band** — the defect is a band with none. ⛔ **The contract is the
   deliverable; the renumbering is its consequence.**
3. **D2 — resolve the `order: 9` collision deliberately.** ⚠ **Establish the intended order first** —
   today's behaviour may already depend on the accidental tie-break. ⛔ **Do not renumber them apart and
   assume the observed order was correct.**
4. **D3 — a collision check that FAILS.** No two same-phase steps may share an order. ⛔ **Verify it
   fires on the live `order: 9` pair BEFORE D2 fixes it** — sequencing is load-bearing; fixing D2 first
   destroys D3's fixture. ⭐ **Extend `TestDefaultPhase6StepsMatchesDiscovery`**, never add a competing
   checker — that would be a fifth restatement of the pipeline order.

### Phase 2 — the emission (was 051)

5. **D4 — a dedicated terminal step, in a slot D1 created.** ⛔ **`archive-plan` stays last.** ⚠ **Do NOT
   relocate `lessons-capture` wholesale** — its lesson work is legitimately mid-band; **only the
   emission moves.** ⭐ Separating the two is the point: relocating a whole step past what it needed is
   how the read-direction defect was created.
6. **D5 — the step exists ONLY under an orchestrator.** ⭐ **`orchestrator inbox detect --source-id` is
   the single sanctioned seam.** ⛔ **No second detector, no new persisted field** — that skill's
   contract says so, and a second producer over one field is `PLAN-TRUTH-049`. A non-orchestrated plan
   composes the step **out**, and that must be an **observable compose-time decision**, never a silent
   runtime no-op. ⚠ **Confirm at D0 that `source_id` is available at COMPOSE time** — if it is only
   available at runtime, D5's shape changes and observability gets harder, not easier.

### Phase 3 — the payload (was 050)

7. **D6 — derive the report↔inbox DELTA, both directions.** ⛔ **The set difference IS the payload
   specification.** **Population-derived over ≥3 archived plans** — one run's delta is a sample.
   ⭐ **The seven findings above are the known-non-empty control**: if D6's delta lacks them, D6 is wrong.
   ⛔ **Classify each item MECHANISABLE vs NARRATIVE-ONLY** — the `ci pr merge` false green arrived as
   operator narrative, not a step fact, so **at least one known item may not be mechanisable at all.**
8. **D7 — the terminal emission carries the facts, machine-readable.** Consume `PLAN-TRUTH-031`'s
   (#1076) typed `facts` map — ⭐ **the schema already exists with both-direction guards; this is a
   ROUTING gap, not a modelling problem.** ⛔ **Do not re-narrate facts into prose** — 031's own finding
   was that prose step records are not facts. ⚠ **Verify the report actually renders from that map**; if
   it renders from something else, D7's source changes.
9. **D8 — a drain-completeness check, and retire the workaround.** After a drain reports `count: 0`, the
   orchestrator must be able to establish nothing material is outstanding. ⛔ **Verify it FAILS on a
   pre-fix archived plan** where the delta is known non-empty — *a completeness check that passes on a
   known-incomplete input is the vacuous guard this epic counts at n≥5.* ⭐ **Then state explicitly
   whether anchor standing check #7 and the operator's manual paste are retired — and name any residue
   that is irreducibly narrative and therefore correctly keeps them.** ⭐⭐ **The operator is the oracle:
   done when a paste stops yielding anything new.**

## Claim Labels

- **OBSERVED (first-party, this orchestrator)**: all 27 order declarations and the collisions; the four
  step orders and the stated reason `archive-plan` runs last; the seven report-only findings; that
  `inbox list` returned `count: 0` for runs whose reports still yielded findings; `PLAN-TRUTH-031`'s
  shipped `facts` map (#1076).
- **OBSERVED (operator, first-party to them)**: that **every** pasted report has carried additional
  information; the pre-1.0 window; the "no split" decision.
- **REPORTED (sibling, second-hand)**: the `api-sheriff` PLAN-37 corroboration.
- ⛔ **NOT ESTABLISHED — deliberately not claimed**: **the composer's tie-break for equal orders.** I did
  not read it. The `order: 9` pair may be deterministic (discovery order, name) or not. ⚠ **Do not report
  "undefined order" as an impact until the composer is read** — this epic has been burned twice this
  week by refutations scoped narrower than the behaviour.
- ⛔ **NOT ESTABLISHED**: whether any consumer project actually pins an order that D1 would break. The
  six `.claude/` declarations are **this** repo's. **Consumer repos were not read.**
- **HYPOTHESIS**: the space is per-phase. Strongly suggested by the `order: 10` pair, **stated nowhere**.
  ⛔ If it is global, that pair *is* a collision and D2 grows.
- **HYPOTHESIS**: `inbox detect` suffices to gate composition — see D5's compose-time caveat.

## ⛔ How the 052 half was produced — recorded, because it is the third instance this session

I asserted the terminal slot was *"between 998 and 1000"* from the **four** steps I had read. **A full
sweep refuted it within the hour: `999` is occupied.**

⇒ **Third instance this session of *a list produced by looking is a SAMPLE, not an enumeration*** — in
the same drain where I folded two fresh instances of that archetype into `PLAN-TRUTH-012`.
⭐ **Knowing an archetype does not protect against it; only running the enumeration does.**

## Two transferable classes carried from the `api-sheriff` report — recorded, NOT staged

- **A javadoc explaining WHY a guard exists is load-bearing.** A deliverable deleted a latch while
  keeping the comment justifying it, leaving an unbounded per-request WARN on an unauthenticated path.
  ⭐ **The mirror of our vacuous-guard counter**: that tracks guards that never fire; this is a guard
  removed because its rationale read as documentation.
- **An anchor that appears to bound and does not.** `$` also matches **before a final line terminator**,
  so a `$`-anchored pattern under `find` semantics still admits the trailing CR/LF that is the
  response-header-injection vector. Fixed with `(?![\s\S])`. ⭐ **A validator that looks total and is
  not** — this epic's theme in a regex.

⛔ Neither is ours to fix (Java, another repository). ⭐ Their *"leaving them isn't neutral; it's a choice
with an expiry date"* framing is **`PLAN-TRUTH-003`** (migration shims have no expiry) stated better than
our own spec states it — **cite it there; do not re-derive.**

## Expected Surface

- **OBSERVED**: every `phase-6-finalize/{workflow,standards}/*.md` frontmatter; `plan-retrospective`,
  `automatic-review`, `extension-api` SKILL.md; the six project-local `.claude/skills/*/SKILL.md`
- **OBSERVED**: `manage-execution-manifest/scripts/_manifest_core.py` — `DEFAULT_PHASE_6_STEPS`
- **OBSERVED**: `marshall-orchestrator/scripts/orchestrator.py` — `inbox detect`, `inbox write`
- **OBSERVED**: `manage-status` — `mark-step-done --fact` / the `facts` map (#1076)
- **HYPOTHESIS**: a new `phase-6-finalize` step doc + the SKILL.md dispatch table;
  `workflow/lessons-capture.md` (where the emission is today); `standards/inbox-envelope.md`;
  `marshall-orchestrator/workflow/analyze.md` (D8); `extension-api` (where `order` is documented for
  third-party authors); `test/plan-marshall/phase-6-finalize/test_finalize_orchestration_routing.py`

## Dependencies and Sequencing

- ⛔ **INTERNAL ORDER IS LOAD-BEARING**: D3 must be shown to fire **before** D2 fixes the collision;
  D4 cannot land before D1 creates a slot; D7 depends on D6's delta.
- ⚠ **Cross-epic: `PLAN-CIS-034` owns the post-run band contract** (whether a `mutates_source: true` step
  may be post-run). ⛔ **A banded allocation contract must not contradict it — notify and align before
  implementing D1.**
- ⚠ **`PLAN-TRUTH-035` is RUNNING** and owns the totals' sampling point. ⭐ **This plan removes the reason
  for 035's partiality at the landing**, but does not fix the sampling defect itself. **Surface-adjacent.
  SERIALIZE.**
- ⚠ `PLAN-TRUTH-032` (inbox protocol / quiescence) — ⭐ **a terminal emission IS a termination signal by
  construction.** **Evaluate absorption at outline.**
- ⚠ `PLAN-TRUTH-038` (no amend/supersede verb) — **a terminal emission substantially reduces the need for
  one.** Re-evaluate its priority after this lands.
- ⚠ Adjacent: `PLAN-TRUTH-003` (pre-1.0 expiry logic), `PLAN-TRUTH-012` (declared-vs-derived divergence,
  shares the lock-step pin).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-050-the-operator-report-is-an-evidence-surface-the-inbox-cannot-see.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — ⭐ which
this plan is, by its own subject matter, the step that emits. Qualifiers are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 1 message (absorbed-TRUTH-052 surface)

**`provider-...-004` (L4).** *`plan-retrospective` is ordered **after the steps that destroy its two
primary inputs**.*

⇒ **Independent confirmation of the ordering defect this spec absorbed from TRUTH-052**, and it names
**two** destroyed inputs rather than the one already recorded (`plan-retrospective` at 995 reading
`metrics.md` before `record-metrics` at 998 writes it). ⛔ **A step whose inputs are destroyed before it
runs cannot be fixed by renumbering alone if the destroying step is also order-constrained** — the
ordering contract this spec builds must be able to express *"reads X"* and *"destroys X"* as distinct
facts, not merely a slot number.

⭐ Note the compounding with the already-recorded pair: `lessons-housekeeping` (order 4,
`mutates_source: true`) still reads an artifact produced at 990 and **cannot be relocated**, because
band membership requires `mutates_source: false`. ⇒ **Two steps, both mis-ordered, and one of them is
structurally immovable under the current band rule.** The contract has to handle that case explicitly
rather than assuming every mis-ordered step can simply move.


---

## ⭐ FOLDED FROM THE 2026-08-09 (EVENING) DRAIN — the ordering defect is now n=2 with a step number

**`metrics-017` (finding).** *`plan-retrospective` runs at finalize **step 17** while `branch-cleanup`
removes the worktree at an earlier step.*

⇒ **Second independent report of the ordering defect this spec absorbed from TRUTH-052** (the first was
`provider-…-004`), and this one supplies the **step number**, which the first did not. ⛔ The ordering
contract this spec builds must therefore be able to express *"reads the worktree"* as a declared
dependency — a slot number alone cannot prevent it, because **step 17 is a perfectly legal slot; the
worktree's absence is what makes it wrong.**
