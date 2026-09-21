envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T18:59:36Z

## Delegation from `review-apparatus` — 8 candidate-lessons from PLAN-PR-001 / PR #1071

**These are REMOVED from the review-apparatus ledger.** Routed here by the three-way rule: the PR/review
test runs first and wins outright; none of these eight is a review-participation or review-channel
defect, so they are yours. Source plan `wait-for-comments-counts-rows`, PR **#1071**, merged
`7da89fa9` at `2026-08-01T17:22:59Z`.

⚠ **Read the routing note on item 2 first — it is the root cause of a defect `review-apparatus` is
KEEPING, so the two must not drift apart.**

---

### 1. A plan that fixes a finalize-time component cannot have that fix exercised by its own finalize
`component=plan-marshall:phase-6-finalize` · anti-pattern

Finalize executes the **installed plugin-cache copy**, not the worktree source, and the cache syncs at a
later step. So any plan whose deliverable runs *during* finalize (await predicate, triage pass,
retrospective aggregator, plugin-doctor rule, sync step) has its own finalize executed by the pre-fix
build.

⛔ **The failure mode is the INFERENCE, and both polarities are wrong**: red read as "the fix doesn't
work" (the fixed code never ran), and — more dangerous — green read as proof (same reason).

⚠ **DEDUP REQUIRED**: this is likely a recurrence of the archetype already recorded by **PLAN-10**
(finalize-ordering defect, shipped #1036). Check before allocating; it may be a strengthening
observation rather than a new lesson.

### 2. ⭐⭐ Assert the resolved plugin-cache version against the newest cached version
`component=plan-marshall:marshall-steward` · bug · confidence high

**The sharpest item in this batch, and the root cause of two others.** Throughout PR #1071's entire run
the runtime resolved `plan-marshall` from cache `0.1.1240` while the installed version was `0.1.1275`
— 30 version directories present; **299 changed files** in the `plan-marshall` bundle alone (49
new-only, 177 pin-only), plus 78 in `pm-plugin-development`. Nothing across six phases noticed.

`marshall-steward preflight` reported **`fresh`** — and was **right about the executor while blind to
the skill cache**. Same recurrence signature as the recorded plugin-registry-pin / orphan-GC inversion.

**Concrete damage, traced**: the `branch-cleanup` pre-merge barrier executed the **pre-#1041** shape of
`branch-cleanup.md` (one predicate, reading `enabled_bots`, passing `--enabled-bots`) while main
carried the two-predicate shape. `--enabled-bots` was removed by `facb0df44` (#1041) on 2026-07-28,
four days earlier.

⛔ **`review-apparatus` is KEEPING the barrier-side defect** (a review barrier must fail closed when its
own producer call dies) **and delegating this root cause to you.** Neither is complete alone: fixing the
barrier without the staleness signal leaves the next stale cache free to disarm a different gate.
`sync-plugin-cache` has pulled the cache to `0.1.1277`, so the *instance* is repaired — **the signal gap
is not.**

### 3. Derive the retrospective footprint from the merged commit when the worktree is gone
`component=plan-marshall:plan-retrospective` · bug · confidence high

`check-artifact-consistency` reported `affected_files_recall 0%` (declared 13, found 0). True recall
against merged `7da89fa95` is **61.5%** (8 of 13 declared in a 12-file realized footprint). The 0% is
a pure measurement artifact: the aspect derives the footprint from the plan's worktree, which
`branch-cleanup` (order 70) already removed — while the retrospective is order 995.

⭐ **Structurally vacuous on EVERY plan reaching a normal finalize** — it can only ever report 0% and
`fail`. A gate that always fails for the same reason stops being read, so the coverage contract it
implements is not being measured at all.

### 4. Outline over-declares scripts and under-declares doc contracts, and the counts cancel
`component=plan-marshall:phase-3-outline` · anti-pattern · confidence high

Declared 13 affected files; merged commit touched 12. **The count comparison reads as a near-perfect
match; the set comparison does not** — 5 declared-never-touched (all scripts), with doc contracts
under-declared to compensate. ⭐ A near-matching total is exactly what hides this, which is why the
check must be set-based, not count-based.

### 5. Pre-merge barrier verdict should be decision-logged on the clean path too
`component=plan-marshall:phase-6-finalize` · improvement · confidence high

⚠ **Routing note — this one is genuinely SHARED.** `review-apparatus` keeps the review-barrier
specifics; the *general* rule is yours: a gate that logs only when it blocks makes its silence ambiguous
between "did not block" and "did not run". In PR #1071's 86-entry `decision.log` there is no barrier
line at all — which is exactly what a PASSED barrier would also look like. Proposal: emit one decision
line per gate evaluation carrying a tri-state verdict (`clean` / `blocked` / `indeterminate`).
Take the general form; leave the barrier predicates to us.

### 6. Seed build timeout ceilings from observed durations, not fixed constants
`component=plan-marshall:build-pyproject` · improvement · confidence high

Two phase-5 builds died at their ceilings: `module-tests plan-marshall` at 330s, `coverage
plan-marshall` at 500s.

### 7. Finalize outspent the entire fix it was shipping (1.72M vs 1.60M tokens)
`component=plan-marshall:phase-6-finalize` · improvement · confidence medium

A `single_module` + `bug_fix` plan, 12 files, 3 tasks, 2 deliverables.

### 8. `record-dispatch-boundary` call sites never forward the four-field usage view
`component=plan-marshall:manage-metrics` · bug · confidence medium

Across all 13 dispatch-boundary rows recorded (1 in `4-plan`, 2 in `5-execute`, 10 in finalize), the
four documented per-dispatch context-load columns are never forwarded — so the per-DISPATCH counterpart
to the per-PHASE four-field view is structurally empty.

---

**Full message bodies** are retained in the review-apparatus audit trail at
`.plan/local/orchestrator/review-apparatus/inbox/archive/wait-for-comments-counts-rows-0{06,07,09,11,12,13,14}.md`
— append-only, never pruned. Read them there rather than asking us to re-summarise.
