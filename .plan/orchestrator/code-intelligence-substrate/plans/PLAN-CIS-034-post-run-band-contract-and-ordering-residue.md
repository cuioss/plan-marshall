# PLAN-CIS-034: The Post-Run Band Contract Cannot Express The Steps That Need It

epic: code-intelligence-substrate
workstream: WS-04

> Staged 2026-08-03 from the PLAN-CIS-028 landing analysis plus `truthful-signals-029/-030/-031`.
> **This spec is the agreed answer to a cross-epic ownership split** — see § "Ownership boundary".
> `PLAN-TRUTH-044` D3 is **gated on this plan existing** and must not implement against the band
> contract. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer, no brief.

## Objective

PR #1080 introduced the `post_run_review` band — every step declaring the fact runs after the merge
gate — and **mandated `mutates_source: false` for membership**. That closed the downward-facing half
of the finalize-ordering defect and left three things open, all live in merged `main`:

1. A step that needs post-merge evidence **and** mutates source **cannot be in the band at all.**
2. `record-metrics` (998) still runs **after** `plan-retrospective` (995), so the retrospective reads
   an accumulator that has not closed.
3. The footprint is still **derived at read time from a mutable substrate** rather than captured
   while true.

⭐ **These are one plan, not three, because they share a single root**: a step's `order:` determines
what it can *see*, and nothing declares the producer→consumer edges that ordering is supposed to
satisfy. **Make the dependency explicit rather than continuing to hand-tune integers.**

## The three residues (all OBSERVED first-party on merged `main`, 2026-08-03)

### R1 — `mutates_source: true` and post-run-review are mutually exclusive, and one real step needs both

| Step | `order` | `mutates_source` | `post_run_review` |
|---|---:|---|---|
| `project:finalize-step-lessons-housekeeping` | **4** | **true** | absent |
| `project:finalize-step-review-retrospective` | 990 | false | true |
| `default:lessons-capture` | 991 | false | true |
| `plan-marshall:plan-retrospective` | 995 | — | — |
| `default:record-metrics` | 998 | false | true |

`lessons-housekeeping` consumes `quality-verification-report.md`, produced by the retrospective **991
orders later**. Its own log records the consequence: *"quality-verification-report.md unavailable
(retrospective runs at order 995, after this settle-band step) and references field modified_files
absent — proceeded on request.md plus the branch diff."*

⛔ **It cannot simply move.** Band membership requires `mutates_source: false`; this step declares
`true`. Relocating it past the merge gate would land a declared mutator with **no push path** — the
`#990` defect that `post_run_source_guard` was added in the same PR to detect.

⭐ **The one candidate that survives the constraint** (converged on independently by both epics):
**split the step** — a main-anchored *classify* pass early, and a pushable *apply* pass in the settle
band. ⚠ Recorded as the leading candidate, **not as a decision**; D2 settles it.

### R2 — the retrospective still reads an unclosed accumulator

`plan-retrospective` = 995, `record-metrics` = 998. #1080's change to `record-metrics.md` is the
single added line `post_run_review: true`. ⇒ The largest phase of a run is read as zero at exactly the
moment the retrospective samples it (**2.17× understatement measured on #1079**).

⭐ **The partiality machinery works correctly** — the row is marked unrecorded and the Total stamped
partial — so this produces an **honest floor**, not a falsehood. That is why it is a defect and not
an emergency, and why the fix is the ordering, **not** the partiality reporting. **Do not "fix" the
labelling; it is the only thing currently telling the truth.**

⛔ **Downstream consequence, first-party from `truthful-signals` on #1082**: three producers reported
**three different totals for one run** — published `metrics.md` 2,782,409; a reconstruction from the
on-disk accumulator ≈5,468,970; `record-metrics` 6.2M. ⭐ **They scoped their remedy as "label each
artifact with its population" and then credited this ordering finding as the reason that is
_necessary and not sufficient_: the three producers sample at three points in a sequence nobody
declared.** The labelling half is theirs (`PLAN-TRUTH-035`, running); **the sampling-point half is
this plan's.**

### R3 — capture, don't derive

#1080 correctly removed `base..HEAD` from the footprint fallback chain (measured on #1079: 39 files
against a true 8, a **4.6× over-count**, because three sibling PRs landed in between). The shipped
chain is live worktree diff → legacy `references.modified_files` → `FOOTPRINT_UNRESOLVED`, and it
never silently returns an empty set.

⛔ **But the recommended tier 2 — the plan's own merge commit recorded at `branch-cleanup` — was not
implemented**, and the shipped legacy key is scoped by its own docstring to *"archived plans created
before the ledger was removed"*. ⇒ **For every NEW plan the archived path resolves to UNRESOLVED
permanently.**

⭐ **Honest-but-unmeasurable is a strict improvement over confidently-wrong and is NOT the same as
measured.** The remedy both epics agree on: have `branch-cleanup` (or `push`) persist the realized
footprint as a deterministic side-effect — `references.json: realized_files`, or
`work/footprint.toon`. **Capture it while it is still true.**

## ✅ What #1080 ALREADY closed — do not re-scope it

`truthful-signals-030` § 1 asks for *"a post-run step whose input is unreadable emits `indeterminate`,
never a graded value"*, citing #1082 where `check-artifact-consistency` reported
`fail, Recall 0%, declared 18, found 0` on a plan whose **real recall was 100%** (all 18 files in
`b713fe4b9`).

⛔ **That obligation is already discharged, and their instance predates the fix.** #1082 merged as
`b713fe4b9`, **before** #1080's `e1ae38142`, so it ran the pre-fix reader. On merged `main` today the
reader carries a stated `FOOTPRINT_UNRESOLVED` sentinel and one named predicate `footprint_resolved`,
and an unresolvable footprint yields `inconclusive` — **not** a graded `fail`. ⭐ **Their framing is
still worth keeping**: a graded `fail` on an absent input is *the exact inversion of a false green and
just as bad*, because a reader chases a gap that does not exist. **What survives from § 1 is their
concrete fallback, and that is R3 — not a second reader obligation.**

### ⭐ R2 and R3 both gained a MEASURED instance from PR #1086 (folded 2026-08-03)

**R2 — `6-finalize` never closes, and the size is now known.** From `…-002`: the phase's accumulator
never folds into the phase row, so **~1.16M tokens are absent from `metrics.toon` — a ~34%
under-report on that plan.** ⇒ R2 is no longer just an ordering argument; **the omission has a
magnitude**, and it is the same phase this epic keeps finding is the largest consumer. ⛔ **D3 must
close the accumulator, not merely re-order the reader** — a reader moved after an accumulator that
never closes still reads a short number.

**R3 — the filing plan independently proposed our own remedy.** From `…-006`: *resolve the plan
footprint from the merge commit after `branch-cleanup`.* ⭐ **That is D4's capture-side arriving from
a second, unprompted source**, which raises it from a proposal to a converged one. ⚠ **It does not
change D4's scope** — still `realized_files` capture only; the *declared* side stays with
`truthful-signals`' `PLAN-TRUTH-057`, and the two keys must not drift toward one name.

## Deliverables

1. **D1 — GATE: derive the producer→consumer edges, do not enumerate them (mutates nothing).** For
   every finalize step, determine which artifacts it reads and which it writes, and report the pairs
   whose `order:` values violate the implied dependency. ⛔ **The three residues above are a SAMPLE**
   — they surfaced because someone happened to read a log. **Report the derived cardinality**
   (lesson `2026-08-03-06-002`). ⚠ A `[STEP]`-marker-derived population is a **FLOOR, not a count**
   (9 of 16 steps carry markers) — settle the enumeration mechanism before asserting coverage.
2. **D2 — settle the band contract for a step that needs post-merge evidence AND mutates source.**
   Either the `mutates_source: false` requirement gains a sanctioned exception with a push path, or
   such a step must be split, or the case is declared unrepresentable and `post_run_source_guard`
   says so explicitly. ⛔ **All three are acceptable outcomes; silently leaving it unrepresentable is
   not.** Record the reasoning.
3. **D3 — R2: the retrospective reads a closed accumulator.** Fix the ordering, not the partiality
   labelling. ⛔ **The labelling is the only component currently telling the truth — leave it intact**
   so a future omission still surfaces.
4. **D4 — R3: capture the footprint while it is true.** Persist the realized footprint as a
   deterministic side-effect of `branch-cleanup` or `push`, and make the resolver prefer it. ⛔ **Never
   reintroduce `base..HEAD`** — sibling landings contaminate any such range, measured at 4.6×.
   - ⭐ **CONSOLIDATED 2026-08-08 — D4 is now the SOLE owner of footprint capture.** `PLAN-CIS-012`'s
     D3 proposed the same fix by a different mechanism and has been **struck**; shipping both would
     have produced **two writers for one key**. The producer/consumer split is now clean: **CIS-034
     produces the footprint, CIS-012 owns how a reader behaves when it was given nothing** (its D2
     third state, its D5 archived-corpus blast radius).
   - ⭐ **Carried over from the struck D3 — evaluate the MERGE-COMMIT fallback as a resolution tier.**
     It is **known-available and verified**: it is how the CIS-012 landing established ground truth by
     hand. ⛔ **It is NOT `base..HEAD`** and the prohibition above does not reach it — a merge commit
     names its own two parents, so the range is exact and carries no sibling contamination. ⚠ It only
     resolves POST-merge, so it cannot serve a consumer that runs before the merge; that is precisely
     why the deterministic side-effect capture remains D4's primary mechanism and the merge commit is a
     fallback tier, not a replacement.
5. **D5 — the change is NOT self-exercising; say so and name the observation point.** This plan
   modifies finalize ordering, so its own manifest — frozen at outline time — will run the OLD order,
   and its script-backed steps resolve from a plugin cache synced later in the same run. ⛔ **Its own
   green finalize is NOT evidence the fix works** (lesson `2026-08-03-06-004`). Prefer a
   derivation-level test over the composed manifest — the shape #1080 shipped and the only one
   observable from inside the plan.

Five deliverables — at the ~6 split guard but under it. Proceeding unsplit is deliberate and the
rationale is recorded here as the standard requires: **D2/D3/D4 are three instances of the single
root D1 derives** (a step's `order:` decides what it can see, with no declared dependency edges), and
splitting them would produce three plans that must each re-derive the same edge set and would race
each other on the same `order:` frontmatter — the collision shape this epic has already paid for.
D5 is a documentation obligation, not an independent workstream.

## Ownership boundary — AGREED with `truthful-signals`, do not re-litigate

Their `-031` § 2 proposed a split, and **it is accepted as proposed**:

- **OURS (this plan)** — the **band contract**: whether a `mutates_source: true` step can ever be
  post-run, what `post_run_source_guard` should say about it, and the finalize ordering that follows.
  Band membership is our surface.
- **THEIRS (`PLAN-TRUTH-044` D3)** — the **corpus-resolution half**: decoupling the store handle from
  cwd so a step's *order* stops determining what it can *see*. Same root cause as their
  `restore-from-plan` fail-open and must be sized with it.

⛔ **What must not happen is both epics editing the band contract.** Their D3 carries an explicit gate
to that effect. ⭐ **Their D3 was staged four hours before our answer and already owned the
housekeeping conflict** — the `mutates_source: true` finding is the part they did not have, and they
recorded that it upgrades their D3 from *"no order satisfies both"* to *"no order CAN satisfy both
under the current band contract"*. **Read their D3 before scoping D2; the two must agree.**

## Claim Labels

- **OBSERVED (first-party, merged `main` 2026-08-03)**: every `order:` / `mutates_source` /
  `post_run_review` value in the R1 table; the shipped three-tier footprint chain; the
  `FOOTPRINT_UNRESOLVED` sentinel and `footprint_resolved` predicate.
- **OBSERVED (first-party, #1079)**: the 2.17× Total understatement; the 4.6× `base..HEAD` over-count.
- **HYPOTHESIS (second-hand, `truthful-signals`, first-party to them)**: the three-totals-for-one-run
  measurement on #1082. Corroborate before quoting (verify-at-outline).
- ⛔ **REFUTED, recorded so it is not re-derived**: that #1080 left the *reader* grading absent inputs.
  It does not — see § "What #1080 ALREADY closed". The citing instance ran pre-fix code.

## Expected Surface

- **OBSERVED**: `phase-6-finalize/SKILL.md` (the band narrative and the item-5f guard hook);
  `extension-api/standards/ext-point-finalize-step.md` (the P1 ∧ P2 discriminator and the
  `mutates_source` requirement); `phase-6-finalize/scripts/post_run_source_guard.py`.
- **OBSERVED**: `standards/record-metrics.md`, `plan-retrospective/SKILL.md`,
  `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — the `order:` frontmatter.
- **HYPOTHESIS**: `_manifest_validation._sort_steps_by_frontmatter_order` and the derivation guard
  #1080 added (verify-at-outline).
- **HYPOTHESIS**: the `branch-cleanup` / `push` step bodies, for D4's capture side-effect
  (verify-at-outline).

## Dependencies and Sequencing

- **Depends on**: nothing. `PLAN-CIS-028` (#1080) is its predecessor and has landed.
- ⛔ **Never pair with `PLAN-CIS-030`** — CIS-030 measures the very accumulator D3 re-orders.
- ⛔ **Never pair with `PLAN-CIS-011` or `PLAN-CIS-031`** — the whole WS-04 `plan-retrospective` /
  finalize serialization class. **WS-04 is effectively serial; this plan is in it.**
- **Cross-epic gate**: `PLAN-TRUTH-044` D3 does not implement until this exists. It now does.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-034-post-run-band-contract-and-ordering-residue.md"
```

## ⭐ D4's MERGE-COMMIT FALLBACK IS NOW CORROBORATED AND HAS A VERIFIED RECIPE (folded 2026-08-09 from inbox `self-review-resweeps-full-surface-every-round-011`)

**Second independent sighting, first-party on PR #1126.** `check-artifact-consistency` on the
merged PR reported **both** coverage checks unavailable:

```toon
  affected_files_recall,inconclusive,"Plan footprint could not be resolved (no live worktree diff and no modified_files key) - recall is unmeasurable, not 0%"
  affected_files_exact_match,inconclusive,"...the comparison substantiates no verdict"
```

**Root cause, restated in its sharpest form**: the footprint resolver assumes it runs *before*
`branch-cleanup`. The retrospective runs at **order 995 — after it.** ⇒ ⛔ **Every orchestrated
finalize runs `plan-retrospective` after `branch-cleanup`, so EVERY post-merge retrospective
loses both coverage checks.** This is not incidental to one plan; it is the standing state.

⭐ **The recipe is verified, not proposed**: `git show --name-only --pretty=format: {merge_sha}`
against a squash merge yields the exact set — **confirmed to return the 19 paths for
`72982d3d4`**. The SHA is recoverable from the `branch-cleanup` step record or the PR.

⭐⭐ **And the recovered numbers are exactly what the check exists to produce**: recovering the
footprint by hand gave **19 realized paths against 14 declared in `references.affected_files`** —
a 5-path under-declaration whose three non-architecture members are real test modules the plan's
own change forced. **The `affected_files` under-declaration archetype, fifth sighting.**
⇒ Today the check reports `inconclusive` **on precisely the runs where the answer is knowable
and useful.**

⚠ **Feed the same resolved list to `check-routing-decisions --diff-file` so both aspects recover
together** — that check has the identical hole from the other side, and `PLAN-CIS-019` now owns
its plan-relative-path defect. **Coordinate: one footprint resolution, two consumers.**

⚠ **Filed `medium` by its author, and the reason is worth keeping**: the fix direction is clear
and verified, but **the SHA-recovery seam has not been designed** — which step record carries the
landing SHA, and what happens on a non-squash merge. ⛔ **Design that seam in D4 rather than
assuming the squash case.**

### ⛔⛔ THIRD SIGHTING, 2026-08-09 — and this one shows the CONSEQUENCE, not just the gap

From PR #1127 (inbox `executor-rejects-invalid-invocations-before-spawn-004`): both
`affected_files` checks returned `inconclusive` post-merge for the same structural reason, and the
hand computation from the merge SHA gave **declared 17, realized 26 — recall 58%, precision 88%**.

⭐⭐ **The new information is what the under-declaration COST**: **two of the eleven undeclared
files were the subject of three review findings.** ⇒ **The under-declaration under-scoped a
remediation sweep, and an external reviewer caught what the sweep missed.** That converts this from
a reporting gap into a **correctness** gap: every finalize step that scopes itself from
`affected_files` — self-review's delta scoping now among them — inherits the miss.

⇒ ⛔ **D4 must state that consequence in the deliverable**, so the fix is understood as restoring a
scoping input rather than as improving a retrospective statistic. ⚠ **Sixth sighting overall** of
the `affected_files` under-declaration archetype (#1126 was 14-vs-19).

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
