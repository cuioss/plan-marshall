envelope_version=1
sender_type=plan
sender_id=retirement-verdict-cited-a-contradicting-example
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T14:26:03Z

# Retrospective candidate-lessons — PLAN-TRUTH-047

spec_id=PLAN-TRUTH-047
runtime_slug=retirement-verdict-cited-a-contradicting-example
pr=1085
merge_sha=4cf3a008f77cd5c1189f8bfc88e5194432391f6f
source=plan-marshall:plan-retrospective
report=.plan/local/plans/retirement-verdict-cited-a-contradicting-example/quality-verification-report.md
aspects_dispatched=16
sections_dropped=0

> **ID mapping is unchecked at drain.** Spec id `PLAN-TRUTH-047` and runtime slug
> `retirement-verdict-cited-a-contradicting-example` are BOTH recorded above because the
> orchestrator maps sender_id -> spec_id by hand at every drain.

## Headline

**The plan's central hypothesis was REFUTED, and that is the run's most valuable output.**
Deliverable 0/2 swept **359 distinct standards files** (6 pair-bearing, **34 GOOD/BAD pairs
adjudicated**) and found **ZERO** contradicting worked examples. The spec premised that the two
known defects were a *sample* of a wider population; they were not. The two motivating defects
were already fixed on main in `de00dca9b` before this plan started.

The published denominator is what makes that zero meaningful rather than vacuous. A zero without
a denominator is indistinguishable from an empty population — which is precisely the defect the
plan then reproduced in its own prose (see CL-9 below).

## Candidate lessons

### CL-1 — Assert the announced skill base directory matches the installed_plugins pin
- component: `plan-marshall:persona-plan-marshall-agent`
- category: `bug` · confidence: **high**
- **Incident 8, self-observed inside the retrospective dispatch itself.** The persona skill
  announced base directory `0.1.1240` while `installed_plugins.json` pinned `0.1.1288`.
- **Incident 7 occurred earlier in the SAME plan** (automatic-review, decision.log `24beaa`).
- ⛔ **Root-cause upgrade:** incident 7 was previously written off as a stale-read artifact whose
  doc-drift finding was withdrawn. That withdrawal was correct *about the doc* but **mis-scoped the
  damage**. The stale read produced the `--enabled-bots` flag that was then passed to a script
  which no longer accepts it — which is the direct cause of CL-2. A plugin-pin gap is not a
  documentation nuisance; it is an upstream producer of false merge-gate signals.

### CL-2 — (DELEGATED to review-apparatus) Pre-merge barrier reported clean from a rejected fetch
Routed to the `review-apparatus` epic inbox per the three-way routing rule. Recorded here as a
pointer only — **it is NOT in this epic's ledger.** See that epic's inbox for the full body.

### CL-3 — Absent `references.affected_files` silently under-scopes three finalize consumers
- component: `plan-marshall:manage-references` · category: `bug` · confidence: **high**
- `references.json` carries **no `affected_files` key at all** (verified first-party).
- Three independent consumers hit it: `plugin-doctor` → whole-tree fallback (logged, safe);
  `pre-push-quality-gate` → whole-tree fallback (logged, safe); `check-artifact-consistency` →
  **inconclusive** for both recall and exact-match.
- All three degraded safely **only because each happened to have a fallback branch**. A consumer
  without one under-scopes silently. This is the known `affected_files` under-recording defect.

### CL-4 — 6 of 17 execution-context envelopes emitted no `[DISPATCH]` line
- component: `plan-marshall:ref-workflow-architecture` · category: `bug` · confidence: **high**
- Full-file scan of **all 395** work.log lines (denominator published): **11** `[DISPATCH]`
  emissions against **≥17** envelopes that demonstrably ran, proven by their own
  `execution-context.*` STATUS/SKILL lines.
- Uninstrumented: `branch-cleanup` (3 iterations), both `phase-5-execute` re-entries,
  `self-review-fix`, `finalize-step-review-retrospective`, and **this retrospective dispatch**.
- ⛔ `branch-cleanup` is the highest-consequence gap — it holds the merge mutex, performs the
  merge, and prunes the branch, and it is **entirely absent from the dispatch trail**.
- Envelope discipline itself is CLEAN: all 11 emitted lines carry `target=execution-context-level-{3,5}`;
  zero envelope violations, zero `Task: general-purpose`. The failure is one-sided — the trail
  **under-reports** real dispatch by ≥35%.

### CL-5 — `architecture find` double-lists every path, so derived population counts are 2x
- component: `plan-marshall:manage-architecture` · category: `bug` · confidence: **high**
- `architecture find --pattern */standards/*.md` returned `count=718` as **two parallel 359-row
  blocks enumerating the identical path set**.
- Caught only because outline Step 9 hand-verified the boundary (decision.log `d9be53`).
- A population-derived detector that trusts the raw count publishes a denominator that is exactly
  **double** the truth — and a published-but-wrong denominator is *more* dangerous than none,
  because it reads as rigour.

### CL-6 — `metrics.md` headlines a 4-of-6-phase subtotal in a row labelled "Total"
- component: `plan-marshall:manage-metrics` · category: `bug` · confidence: **high**
- Total row reads **2,693,646 (n=4/6)**; reconstructed whole is **~3,548,699**. Phase 6-finalize
  alone contributed **855,053** and is absent. Every ratio from the headline understates by ~32%.
- ⚠ **SUSPECTED DUPLICATE of PLAN-TRUTH-035** (`token-total-is-a-partition-labelled-a-whole`,
  implemented and awaiting finalize). **Orchestrator MUST dedup before filing.**

### CL-7 — Declared-but-not-granted `Grep` leaves a leaf with no content-search primitive
- component: `plan-marshall:execution-context` · category: `improvement` · confidence: **high**
- TASK-002 needed a content sweep over 359 files. `Grep`/`Glob` declared in `allowed-tools` but
  **not granted at runtime**; Bash `grep`/`find`/`ls` hook-blocked; `architecture find` path-only.
- The leaf **correctly logged `[BLOCKED]` and refused to degrade to a spot-check** rather than
  publishing an unsubstantiated sweep. That refusal is the behaviour to preserve.
- ✅ Resolved by **RE-SEQUENCING** (deliverable 3 built the detector first; deliverable 2 then ran
  it as a script), making the population count a reproducible artifact instead of a hand count —
  strictly better than the planned order.
- **RECURRED in this retrospective dispatch** (`Grep` denied again).
- CLAUDE.md has since gained `architecture search --content`; the execution-context "Runtime tool
  availability" section should name it as the declared fallback.

### CL-8 — Worked-example detector adjudicates 4 of 34 pairs
- component: `pm-plugin-development:ext-self-review-plan-marshall` · category: `improvement` · confidence: **high**
- The new detector reached **4 of 34** pairs; **30 were adjudicated by hand**.
- The two unreachable relational cases — a clause with no fenced BAD/GOOD pair, and a GOOD half
  with no recoverable branch predicate — are exactly the residue that lessons-housekeeping
  **refused to retire** lesson `2026-07-18-14-001` over (decision.log `dd478d`). That refusal was
  correct; this is its script-shaped successor.

### CL-9 — The plan reproduced its own target archetype
- component: `plan-marshall:phase-6-finalize` · category: `anti-pattern` · confidence: **high**
- ⭐⭐ Its own new **rule-19 prose** claimed an empty `worked_example_pairs` list proves "every
  adjudicable pair agrees" — while a line **26 lines later in the SAME file** correctly said a zero
  without a published denominator is indistinguishable from an empty population.
- **Measured:** the surface returned **0** while **30 of 34 pairs were UNADJUDICATED**.
- Caught ONLY by `pre-submission-self-review`; fixed in-branch as `16974c7aa`.
- **Third recorded instance of a plan reproducing its own target defect.**

### CL-10 — branch-cleanup doc assumes inline-orchestrator cwd
- component: `plan-marshall:phase-6-finalize` · category: `improvement` · confidence: **medium**
- `branch-cleanup.md` is written against an inline-orchestrator cwd; a dispatched leaf's
  post-move-back calls all fail `plan_resolution_failed`.
- `prune-local-and-remote-ref` is documented to abort before pruning the remote ref when
  worktree-remove already deleted the local branch. **The live run RECOVERED** — work.log 380 logs
  "continuing" and `git branch -a` verifies the refs are clean. So this is a
  **doc-vs-implementation divergence, not a live ref leak.**

## Operational notes for the drain

1. **Merge mutex was force-released under operator authorization.** Held by `content-search-seam`
   (PLAN-CIS-001, paused mid-finalize) with `staleness=fresh` — NOT auto-reclaimable, and it would
   **never have released on its own**. `content-search-seam` remains paused and re-acquires
   normally on its next finalize entry. (decision.log `e192a3`)
2. **Merge verification was done from `git log origin/main`, NOT from the merge call's return.**
   The enqueue return said `enqueued:true` while `pr view` still said open — the return value would
   have been a false-green oracle.
3. **Task-invalidation was under-enumerated at plan time**: 4 tests enumerated, **6 actually
   invalidated across 3 files**, all from the identical `--coverage-verdict` cause. In-scope, so
   not a regression — but boundary condition 3 held only partially. (decision.log `bc65c2`)
4. **Deliverable 2's zero mutations is a CORRECT, pre-authorised outcome**, not a missed
   deliverable. Recorded as a Step 9a file-change-invariant divergence (decision.log `5d788a`).
5. **declared=18 / realized=18 is a COINCIDENTAL count match** over two sets that differ by 5
   members in each direction. A count-only check would have scored this a perfect match.

## Still owed

- `kind=landing` for this plan — **not written by this dispatch.** `lessons-capture` runs next in
  the manifest and already resolved orchestration context (decision.log `ae01bc`); it owns the
  landing. Flagged here so the obligation is visible rather than assumed.
