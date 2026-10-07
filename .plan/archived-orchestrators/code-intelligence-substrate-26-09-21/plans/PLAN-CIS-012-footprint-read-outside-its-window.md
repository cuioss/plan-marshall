# PLAN-CIS-012: A footprint read outside the window in which the footprint exists reports 0 as a finding

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from the PLAN-94 landing (#1040), inbox message 006.

## Objective

Two independent sites derive a plan's file footprint at a moment when the footprint's **source does
not exist**, and render the resulting emptiness as a measured `0` — one as a failing metric, one as a
build-skip decision. Make a footprint read distinguish *"the footprint is empty"* from *"the footprint
source is unavailable"*, and never render the second as the first.

## ⭐ The self-referential sting

**The tool whose job is to detect false signals emitted one, about itself, in its own report.** And
because the failure is **ordering-driven rather than data-driven, it fires identically on every
plan** — so the archived-plan retrospective corpus this epic mines is likely carrying a systematically
false recall column.

## Instance 1 — the retrospective's own recall check (OBSERVED, PR #1040)

`check-artifact-consistency` reported:

```text
affected_files_recall,fail,Recall 0% below 70% threshold
  declared: 7   found: 0   recall_pct: 0.0
  missing[7]: <every one of the seven declared files>
```

**The truth is the exact opposite.** The merged squash commit `8b143643` touches **precisely those
seven files** — 7/7, no extras, no omissions. *Perfect recall reported as total failure*
(orchestrator-verified against the commit, not taken from the message).

The cause is **lifecycle ordering, not data**. The aspect derives the footprint live from the plan's
worktree (`{base}...HEAD` ∪ porcelain). The composed manifest orders `branch-cleanup` — which
**removes the worktree** — at index 15, and `plan-marshall:plan-retrospective` at index 16. ⛔ **The
worktree is always gone by the time the aspect runs.** This is not a fluke of one plan: it is
structural for every plan whose manifest carries both steps in the default order.

## Instance 2 — the composer's build decision (OBSERVED, PR #1040)

At `17:13:08Z`, during **4-plan**, `manage-execution-manifest compose` logged:

```text
pre-push-quality-gate omitted — plan footprint is empty — no changed files to build
```

Phase 5 did not write its first file until `17:20`. **At compose time no footprint could exist yet.**
The step survived only because an *independent* rule (`ceremony_finalize selection —
finalize.qgate=always`) re-added it four log lines later. ⛔ **Had that ceremony knob been `auto`, this
plan would have pushed seven changed files with the pre-push quality gate omitted on the stated
grounds that it had changed nothing.**

## Deliverables

1. **D1 — GATE (mutates nothing): derive the population of footprint reads.** Enumerate every site
   that derives a footprint and grade on it. ⚠ **Population-derived, not the two sites this spec
   names** — the two were found by one run, and a set-guarding fix built on a sample repeats the
   archetype. Establish for each site whether its source can be absent at its call time.
2. **D2 — a third state at the read seam.** When the derivation source is absent — no worktree on
   disk, no commits yet on the branch, compose running before phase 5 — the output is `unknown` /
   `skipped` **with a reason token**, never `0` and never `fail`. ⭐ This is the same discipline
   already recorded for merge-lock staleness (*an empty worktree-scoped store means "unknown", never
   "stale"*); **the rule generalizes beyond locks to every footprint read.**
3. ~~**D3 — `plan-retrospective` gets a footprint that outlives `branch-cleanup`.**~~ ⛔ **STRUCK
   2026-08-08 — DUPLICATE OF `PLAN-CIS-034` D4. This plan no longer owns the footprint-capture fix.**
   The two deliverables were the same work with two different mechanisms, in two different plans, both
   WS-04: this D3 proposed *"capture before `branch-cleanup` and persist into the plan directory, or
   resolve post-merge from the merge commit"*; CIS-034 D4 proposes *"persist the realized footprint as a
   deterministic side-effect of `branch-cleanup` or `push`, and make the resolver prefer it."*
   ⛔ **Shipping both would produce two writers for one key** — the exact naming-drift hazard this epic
   agreed with `truthful-signals` to guard (`realized_files` vs `affected_files`, two keys with one
   writer each). **CIS-034 owns it**, because it owns the ordering defects R1/R2/R3 as a set and the
   capture is R3.
   - ⭐ **One contribution carried ACROSS to CIS-034 D4 rather than lost**: the **merge-commit fallback
     is known-available and verified correct — it is how the CIS-012 landing established ground truth by
     hand.** CIS-034 D4 must consider it as a resolution tier; ⛔ it is NOT `base..HEAD` (which D4
     rightly forbids at 4.6× sibling contamination) — a merge commit names its own two parents, so the
     range is exact.
   - ⚠ **This plan still owns the CONSUMER side**: D2's third state at the read seam, and D5's blast
     radius on the archived corpus, both remain here. The split is *producer* (CIS-034) vs *how a
     reader behaves when the producer gave it nothing* (here).
4. **D4 — `compose`'s build/no-build decision stops being a constant.** A decision taken at plan time
   against a footprint that cannot exist yet is not a decision. Either defer the omission to a point
   where the footprint is real, or state the predicate's precondition and **skip (not omit)** when it
   is unmet.
5. **D5 — assess the blast radius on the archived corpus.** Determine whether archived plans' recall
   figures are affected the same way, and report the count. ⚠ **Report the affected count separately
   from the number of plans examined** — a volume is not a coverage number. No corpus rewrite is in
   scope; the deliverable is the honest assessment, because this epic draws cross-plan conclusions
   from that column.
6. **D6 — tests, each verified to FAIL pre-fix.** (a) A retrospective run with the worktree removed
   yields `unknown`, not `recall 0%`. (b) A compose run before any phase-5 write does not emit a
   footprint-empty omission. (c) The merge-commit fallback reproduces 7/7 on a known plan.

Six deliverables — **at the split guard.** Proceeding unsplit is deliberate: D1 is a gate that D2–D4
all consume, and D5/D6 are small. ⚠ If D1 finds the population is materially larger than the two named
sites, **split D3/D4 out and re-stage** rather than growing this plan.

## Claim Labels

- OBSERVED (orchestrator-verified against `8b143643`): the 7/7 true footprint; the `recall 0%` report.
- OBSERVED (first-party, PR #1040 logs): the compose-time omission at `17:13:08Z`; the first phase-5
  write at `17:20`; the ceremony rule re-adding the step.
- HYPOTHESIS: the manifest indices (`branch-cleanup` 15, `plan-retrospective` 16) are the DEFAULT
  order rather than this plan's composition — confirm/refute at the manifest composer's default step
  ordering (verify-at-outline). **This is load-bearing**: if the order is per-plan, the "fires on every
  plan" claim narrows and D5's blast radius shrinks.
- HYPOTHESIS: archived plans carry the same false recall column — confirm/refute by sampling the
  archived corpus's `check-artifact-consistency` output (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — `check-artifact-consistency`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**` — `compose`
- HYPOTHESIS: the shared footprint-derivation helper, if one exists (verify-at-outline)

## ⛔⛔ RECONCILED 2026-08-09 — BLOCKER STRUCK, OWNERSHIP CONFIRMED, SCOPE UNCHANGED

⛔ **THE D5 BLOCKER IS STRUCK.** ~~BLOCKED BY PLAN-10: D5 must not run until end-phase
replace-not-accumulate is fixed~~ — **`PLAN-10` SHIPPED as PR #1059** and is a `shipped` row in this
epic's own queue. **D5 is unblocked**, subject only to the two named exclusions its own text already
records. ⚠ Every other `PLAN-NN` id in this spec (PLAN-54, PLAN-81, PLAN-89, PLAN-92, PLAN-99,
PLAN-103) belongs to the **retired `plan-optimization` epic** and is historical — see `epic.md`
§ Queue Reconciliation 2026-08-09, finding R1.

✅ **OWNERSHIP CONFIRMED AND WIDENED IN THIS PLAN'S FAVOUR.** `PLAN-CIS-013` carried the same
recall-0% defect as its items (b) and (e); **those are now STRUCK there.** This plan is the sole
owner of the footprint/recall defect on the **consumer** side. The producer side stays with
`PLAN-CIS-034` D4 (per the 08-08 split, reinforced 08-09 by a third sighting with recall 58% and a
verified merge-commit recipe). ⛔ **The split is producer vs consumer and it is settled twice —
do not re-litigate it.**

⚠ **Scope is UNCHANGED and the plan stays at its six-deliverable guard.** Nothing was added here;
D3 remains struck. ⛔ **If the D1 gate finds the population is materially larger than the named
sites, SPLIT rather than grow** — that instruction was already in the spec and it now has a second
reason: this plan is one of the three longest in the queue, and its own length is the doc-residency
cost `WS-06` exists to attack.

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⛔ **PLAN-CIS-011 and PLAN-CIS-010** — both touch `manage-execution-manifest` /
  `phase-6-finalize`. **Sequence, never pair.** PLAN-CIS-010 runs first among that group per the existing
  split decision.
- Adjacent to: PLAN-CIS-013 (`chat-signal-provenance-filter-under-inclusive`) also edits
  `plan-retrospective` — ⛔ **same bundle, do not pair.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-012-footprint-read-outside-its-window.md"
```

## Inherited Inbox Evidence (folded 2026-07-29 from `truthful-signals-001`)

⚠ **Leads, not facts** — re-verify before scoping. Forwarded under the inbound routing rule.

**The archetype is now at n>=5 and is STRUCTURAL for every plan carrying both steps in the default
order — not incidental.** Four independent plans hit the same root in one window:

| Source | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-008` | PLAN-99 / #1043 | A coverage check reported **0%** because its input was unavailable |
| `one-coherent-automated-review-contract-009` | PLAN-92 / #1041 | Retrospective after `branch-cleanup` makes **every footprint-derived aspect** report a confident wrong answer |
| `runnable-slice-keys-...-016` | PLAN-89 / #1044 | Retrospective measures a footprint **after** `branch-cleanup` deletes the worktree |
| `self-review-cannot-see-an-unreachable-guard-006` | PLAN-81 / #1042 | Retrospective diff-derived checks **return empty** post-cleanup |

**OBSERVED (orchestrator-verified against merge commits, not message-supplied):**
- **#1040** — retrospective reported `recall 0%, all 7 declared files missing`; squash commit
  `8b143643b` touches **exactly those 7 files**. Perfect recall reported as total failure.
- **#1042** — same report shape; real footprint was **11 files**.

⭐ **What this ADDS to D5 (blast-radius assessment):** the corruption is no longer hypothetical.
Four confirmations in one window means the archived-plan recall column is **almost certainly
systematically false**, and any cross-plan conclusion drawn from it is unsafe until D5 reports.
⛔ **Report the affected count SEPARATELY from the number of plans examined** — volume-read-as-coverage
is a recorded recurring archetype and this is exactly where it would recur.

⛔ **BLOCKED BY PLAN-10.** D5 must not run until `end-phase` replace-not-accumulate is fixed,
or D5 measures a corpus that is still being actively corrupted.

## Second Evidence Fold (2026-07-29 — `truthful-signals-008`, `-010`, and PLAN-10's own assessment)

⭐ **D3's REMEDY IS NOW KNOWN, not to be searched for.** `wrong-store-...-008`: fall back
`check-artifact-consistency`'s footprint to the **MERGE DIFF**. Its live-mode derivation uses the
worktree (`{base}...HEAD` ∪ porcelain) and falls back to the legacy record — but **the worktree is
always gone**, since `branch-cleanup` precedes `plan-retrospective` in the default order.
⭐ **The merge-diff fallback is not speculative: it is the exact method this orchestrator used BY HAND
to establish ground truth on #1040 (7/7 files) and #1042 (11 files) when recall reported 0%.**

**RECURRENCE — third independent observation** (API-Sheriff #7 via `truthful-signals-010`): `compose`
evaluates `build-decision` against an **empty footprint at phase-4 time**. Same archetype, different
consumer: a footprint read outside the window in which it exists.

✅ **D5's BLOCKER IS DOWNGRADED — read this before scoping D5.** PLAN-10's own damage assessment
(read-only, nothing repaired) examined **27 archived plans, all 27 carrying `work/metrics.toon`** and
found **only 2 affected**, 2 suspect rows, both `5-execute`. **25 of 27 show no loop-back at all — the
damage is narrow, NOT corpus-wide**, which contradicts the earlier "understated by construction"
framing recorded in this epic. Affected: `executor-version-split-resolvers` (~12.8x under-count) and
`exploration-share-is-unmeasured` (~4.3x).
⚠ **But the count is a FLOOR, not a ceiling** — the predicate is timestamp-derived because pre-fix
rows carry no `close_count`, so a loop-back that re-closed *before* the later phase's `start_time`
is invisible to it.
⇒ **D5 may proceed once PLAN-10 lands, excluding the 2 named plans, rather than waiting for a
corpus-wide repair.** `total_tokens` is recoverable on both rows and the *rendered* report already
self-heals via same-population max; `agent_duration_ms` and `tool_uses` are **unrecoverable**.

⚠ **UNOWNED SIDE-FINDING from the same assessment**: `idle_duration_ms` was zeroed by the
monotonicity guard on the **flagged** (`6-finalize`) row rather than on the genuinely re-entered
`5-execute` row — **the guard protected the wrong row on both plans.** Same inverse attribution as the
warning itself. This is a live gap in the *timestamp detector*, independent of the write-side fix, and
no plan owns it.

## Evidence Fold — 2026-07-29, from the PLAN-01 landing (#1056) and `truthful-signals-012`

⚠ **Leads, not facts** — re-verify at outline. Four messages fold here; all four are the same
archetype (a measurement read outside the window in which its measurand exists), which is why they
fold rather than stand alone. The archetype count moves from **n=3 to n=6**.

**(a) `inventory-blind-spot-008` — the 0%-recall instance, now with a MEASURED true value.**
`check-artifact-consistency` emitted `affected_files_recall,fail,Recall 0% below 70% threshold`
(`declared: 10, found: 0`) with no hedge. True recall is **10/10 = 100%**, derived independently from
the recorded SHAs: `git diff --name-only ef80c1c8...69f22701` returns exactly the 10 declared files.
`branch-cleanup` is manifest step **16**, `plan-retrospective` step **17**, so the worktree the aspect
derives its footprint from is already gone. ⛔ The documented fallback (`references.modified_files`)
is scoped to "archived plans created before the ledger was removed" and **does not engage** for a live
plan whose worktree merely no longer exists. ⭐ Independently corroborated the same day by
`truthful-signals-012` item 2, which adds a second defect on the same surface: **the documented escape
hatch defers to a check that does not exist**, so the false FAIL has no sanctioned route to dismissal.

**(b) `inventory-blind-spot-007` — the probe-staleness half, and it is BROADER than this plan's title.**
`plan-retrospective` is step 17; `finalize-step-deploy-target` (18) and
`finalize-step-sync-plugin-cache` (19) run after it. The executor resolves scripts from the plugin
cache, so **every behavioural probe any finalize step at position < 19 makes about its own plan's
change reads pre-fix code.** Observed live on #1056: the retrospective's own probes returned
`count: 0` for both of that plan's headline deliverables, and reading the merged source showed both
were correct. ⛔ **A retrospective that had trusted its own probe would have filed two fabricated
"live defect in merged main" findings against a correct change.** This is not weak evidence, it is
*inverted* evidence — full-confidence reporting of pre-change behaviour. Also affects
`pre-submission-self-review` and `finalize-step-simplify`.

**(c) `inventory-blind-spot-009` — a compose-time footprint predicate that is vacuous BY
CONSTRUCTION.** `decision.log` at phase-4-plan, two lines one second apart: `pre-push-quality-gate
omitted -- plan footprint is empty -- no changed files to build`, immediately followed by
`ceremony_finalize selection -- finalize.qgate=always, added pre-push-quality-gate`. The plan went on
to change **19 files**. `compose` runs in phase 4; files change in phase 5 — so the footprint is
**structurally empty for every plan ever composed**, not empty in this case. It is harmless today only
because `finalize.qgate=always` re-adds the step; under any conditional qgate this omits the pre-push
build gate from **every plan**. This is vacuous-guard occurrence **n=6+** in the repository.

**Fold consequence for the deliverable set.** (a) and (c) are both "absent input reported as a
measured zero/empty"; (b) is "the observing step runs before the state it observes is current". ⛔ **Do
not patch the three sites.** The plan already carries a 6D shape at the guard; scope the fix as one
rule — *a measurement whose input is unavailable reports `skip` with a named reason, never a
floor-graded value* — plus the ordering correction, and derive the affected step population rather
than naming these three. ⚠ **Split guard**: if folding all four pushes the deliverable count past six,
split the ORDERING arm (b) out as its own plan and record the split, rather than absorbing silently.

## Third Evidence Fold — 2026-07-29, from the PLAN-10 landing (#1059)

⚠ **Leads, not facts** — re-verify at outline. **Both items below are SECOND INDEPENDENT OBSERVATIONS
of signals already folded above, from a different plan on the same day.** Recurrence is the information:
neither is a new defect, both raise the confidence that the population is systematic rather than
incidental.

**(a) `end-phase-...-006` — the recall-0% defect again, with a SECOND measured true value.** Reported
`declared: 6, found: 0, recall_pct: 0.0`; true recall **100 %**, all 6 declared files present in the
squash-merge commit `dfe7fde0b`. The plan had zero scope creep and perfect declared-vs-realized
agreement, **and was graded a total coverage miss.**

⭐ **Three things this adds that the first observation did not:**

1. **The precise state that falls through.** A plan between `branch-cleanup` (16) and `archive-plan`
   (22) is in **neither** documented footprint state — the worktree is gone AND the plan is still live —
   so the resolver's two documented sources (live worktree; `references.modified_files` **for archived
   plans only**) both miss, and it silently resolves to the empty set.
2. **The blast radius is three aspects, not one.** `check-artifact-consistency`,
   `check-manifest-consistency` and `check-routing-decisions` all consume the same footprint and all
   silently degrade. This run had to reconstruct the footprint **by hand from the merge commit** to make
   aspects 12 and 13 meaningful at all.
3. **A concrete remedy shape**: give the resolver a third tier — worktree on disk → derive live;
   worktree absent AND a PR number resolvable from `references.json` / `status.metadata.pr_number` →
   **derive from the merged squash commit**; archived → legacy key. ⛔ **When none resolves, report a
   `skipped` check with an explicit reason token — never a numeric `recall_pct` over an empty set.**

⇒ **Corpus consequence, now stated by two independent runs**: every archived retrospective produced
since this ordering carries the same false zero, so the corpus-level *scope-estimate accuracy* and
*declared-vs-achieved coverage* checks are reading a **systematically zeroed input**. D-scoping should
treat corpus repair as a question to answer, not assume it.

**(b) `end-phase-...-011` — the vacuous compose predicate again, verbatim.** The same two
`decision.log` lines (`c409ae` omit / `660085` re-add), this time at the **same timestamp**, on a plan
that went on to change 6 files. It adds the sharpest statement of the latency: **under any
`finalize.qgate` other than `always`, the same always-true predicate would silently drop the pre-push
quality gate from every plan's manifest, with the log explaining the drop by a rationale that is never
false — a false-green generator.** It also names a **second instance of the same shape** to sweep for:
`routing-decisions` reported `mis_prune:sonar-roundtrip` as `skip` because the step was removed by
`posture_cutoff` **before its prune predicate was ever evaluated** — a decision recorded without its
predicate having run.

⇒ **Deliverable sharpener**: the fix is not "delete the predicate" but *"a predicate evaluated at a
fixed lifecycle point must be checked for whether its condition can vary at that point"* — pinned by a
test asserting **no compose-time predicate reads the realized footprint**. If the intent was to skip the
gate for a no-op plan, derive it from the **declared** deliverable footprint (`solution_outline.md`
Affected files), which IS available at compose time.

⚠ **Cross-note, not folded**: `end-phase-...-014` reports that `plan-retrospective`'s invariant aspect
carries **three different names** ("Invariant outcomes" in the SKILL table, `invariant-check-summary.md`
as the reference file, `invariant-summary` as the only key the registry accepts) and that registering by
the *documented* label **failed live**. That is this plan's bundle but a different seam; pick it up only
if this plan's outline finds it in the same file it is already editing.

## ⛔⛔ Fourth Evidence Fold — 2026-07-29, `truthful-signals-014` + `-015`: THE RECALL DEFECT IS TWO DEFECTS

⛔ **READ THIS BEFORE SCOPING ANY ORDERING FIX. It changes the deliverable set, not just the evidence.**

`truthful-signals` forwarded the ordering diagnosis (`-014`), then **sent a correction (`-015`)
retracting its own completeness**: the `Recall 0%` red has **two independent causes, either of which
alone produces it**.

1. **Ordering** (already folded above, n=3 now): the measurement runs after `branch-cleanup` deleted
   the worktree it derives from. A third instance: `declared: 12, found: 0`, real footprint **8 files**
   (merge commit `c259f5c7`), write-intent recall **6/6 = 100 %**.
2. ⭐ **VACUITY — NEW, and independently fatal: the threshold is unreachable by construction.**
   First-party from PR #1061's retrospective: **8 of the 12 declared paths are `intent: read`**, and
   the recall denominator counts **read-intent files as expected modifications**. That caps achievable
   recall at **33 % against a 70 % threshold** — ⛔ **no execution of that plan could have passed.** A
   plan that declares files it intends to *read* is penalised for not *modifying* them.

⛔⛔ **THE PARTIAL-FIX TRAP, stated by the sender and adopted here as a scoping constraint.** Fix the
ordering alone and the check goes from *failing for a demonstrably wrong reason* to *failing for a
differently wrong reason* — **while looking like it was addressed.** Worse, a green ordering fix would
**destroy the evidence that (2) exists**. ⇒ **This plan MUST fix both, or explicitly split them into
two sequenced plans and say so. Shipping (1) alone is a defect of this plan.**

⚠ **Check whether any other derived metric shares that denominator.** The intent-classified path list
is likely consumed by more than this one check; derive the consumer set rather than assuming it is one.

**The load-bearing rule, now stated twice from two epics — adopt it verbatim as the deliverable's
success criterion:**

> **An unmeasurable quantity must not be reported as a measured zero.** A zero that means *"could not
> measure"* and a zero that means *"measured nothing"* must not share a representation.

Remedies for the ordering half, cheapest first: snapshot the realized footprint at the push barrier (or
at `branch-cleanup`) so consumers read the snapshot; or derive from the merged PR's commit range when
no worktree exists; or **return `skip` with `footprint_underivable`, never `fail` with
`recall_pct: 0.0`**. ⭐ The third is load-bearing regardless of which mechanism is chosen — and after
`-015`, it is **necessary but NOT sufficient**.

⚠ **Polarity note worth keeping**: this is a confident **RED manufactured by step ordering**, where
this programme's usual case is a confident green hiding a caveat. Same defect class, opposite sign —
which is why it survived so long: a red gets explained away as "the plan's fault", a green does not get
questioned at all.

⚠ **The legacy fallback is GONE, not merely inapplicable.** `references.modified_files` was removed and
is retained only for archived plans, so a live post-cleanup plan has **no fallback at all**. Do not
scope a fix that assumes the fallback can be re-pointed.

## Fifth Evidence Fold — 2026-07-30, from the PLAN-11 landing (#1063), `audit-report-path-ignores-plan-dir-006`

⚠ **Leads, not facts** — re-verify at outline. ⛔ **This fold adds NO deliverable.** The plan is at the
six-deliverable split guard; this is a *recurrence record* on the existing D1/D2/D4 shape, which is
exactly what the dedup discipline requires. Do not grow the plan on the strength of it.

**Three consumers converted an unmeasurable footprint into a confident wrong verdict inside ONE plan** —
the tightest co-occurrence observed so far:

1. `check-artifact-consistency` — `affected_files_recall, fail, Recall 0%`, `found: 0`, all **11**
   declared files listed missing. True recall **100 %**: an exact set match with the declared
   `affected_files`. Fourth independently-measured true value (after 7/7, 11 files, 10/10, 6/6).
2. ⭐ **`manage-config build-decision` — a NEW consumer not previously in this spec's population.**
   Returned `decision: not_necessary, reason: plan footprint is empty — no changed files to build`.
   ⛔ **D1's population derivation must reach `manage-config`, not just `plan-retrospective` and
   `manage-execution-manifest`.** Two named sites became three by observation alone, which is the
   standing rule 4 warning ("a reported instance is a SAMPLE") firing against this very spec.
3. The `phase-4-plan` manifest composer — the vacuous compose predicate again, verbatim, on an
   **11-file** plan. Rescued once more only by `finalize.qgate=always`.

⭐ **The sharpest statement yet of the mechanism, adopt it as D2's acceptance wording:** the predicate
is `if not footprint:` in all three, so *"I could not measure this"* and *"I measured this and it is
empty"* collapse into one branch — **and the branch that wins is the confident one.** There is no third
state to lose, because none was ever built.

⛔ **The near-miss is the finding, not the recall number.** Case (3) means the only thing standing
between this plan and shipping with **no pre-push quality gate** was an unrelated config setting. A
consumer project without `finalize.qgate=always` ships the gate pruned, on the stated grounds that
nothing changed, measured before anything could have.

✅ **D3's merge-commit fallback is now confirmed a fourth time as the working reconstruction**, with the
exact two commands the retrospective used:

```text
git merge-base origin/main origin/feature/{branch}
git diff --name-only <base> origin/feature/{branch}
```

⇒ **Fold the fallback into the SHARED footprint resolver** so all three (now four) consumers inherit
it, rather than each degrading independently — this is D2 + D3 as already written, reinforced, not
extended.

## ⭐⭐ Fold 2026-08-03 — the COMPOSER prunes on a footprint it declared unavailable IN THE SAME SECOND

From lesson `2026-08-03-14-005`, first-party on PLAN-CIS-001 / #1084.

`manage-execution-manifest compose` logged **"footprint unresolvable"** and, **in the same second**,
dropped `sonar-roundtrip` on a **`no_code_delta`** predicate. ⛔ **The realized footprint touched four
production `.py` files.**

⇒ ⭐ **This is the epic's flagship archetype at the COMPOSITION layer, and it is a step further than
the reader-side instances**: a reader that grades an absent input emits a wrong number; **a composer
that prunes on an absent input removes a gate from the run.** The consequence is not a misleading
report — it is a production-touching change shipping without its security/quality lane.

⛔ **Distinct from `PLAN-CIS-016` item D — do not merge them.** CIS-016 D is the *checker*
mis-attributing a posture-cutoff drop to a prune predicate. **This is the composer actually
performing a predicate drop against an input it had just declared unresolvable.** One is a
mis-report; this is a mis-action.

**Deliverable**: an unresolvable footprint must make every footprint-dependent prune predicate
**inadmissible**, not false. ⛔ **Fail-closed is the only safe direction here** — keeping the step is
recoverable, dropping it is not — which is the inverse of the reader-side remedy where
`inconclusive` is correct. **State that asymmetry explicitly; it is why the two cannot share one fix.**

### ⛔ SECOND SIGHTING, 2026-08-03 — the same mis-prune recurred on PR #1086

Rescued from that plan's **withheld medium-confidence proposals** so it is not lost with the plan
directory: `sonar-roundtrip` was mis-pruned for `execution_profile=standard` **even though the
realized footprint touched 4 production `.py` files**, so **Sonar new-code analysis never ran on that
change either.**

⇒ ⭐ **Two consecutive plans, same defect, same consequence** — that settles it as systematic rather
than incidental and makes the fail-closed remedy above non-optional. ⚠ **Note this is a different
plan from the #1084 sighting and both shipped production Python**, so the exposure is not theoretical:
**two merged changes touching production code went without their security/quality lane.**

⛔ **Do NOT confuse this with the operator's standing decision** that `standard` prunes `lane: full`
steps by design (recorded in the epic's Open Defects). **That decision is about a posture-cutoff
drop; this is a PREDICATE drop evaluated against an unresolvable footprint.** Different mechanism,
and only one of them is the operator's call.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
