# Landing Analysis — PLAN-CIS-028

**Plan**: `post-run-steps-ordered-before-their-evidence` (WS-04)
**PR**: [#1080](https://github.com/cuioss/plan-marshall/pull/1080) — `fix(phase-6-finalize): reorder post-run-review steps after the merge gate`
**Merged**: `e1ae38142` on `main` (corroborated first-party via `git log`, not from the message)
**Analyzed**: 2026-08-03, from inbox message `post-run-steps-ordered-before-their-evidence-001.md`

---

## 1. Corroboration — what was checked rather than accepted

Standing rule 1 (corroborate before any `shipped` transition) and standing rule 2 (probe the
objective live, never accept the plan's own success report) were both applied. The message is a
lead; every row below is a first-party read of `main` at `e1ae38142`.

| Claim in the message | Verdict | Evidence |
|---|---|---|
| PR #1080 merged | **corroborated** | `git log main` → `e1ae38142` |
| "24 affected files" | ⚠ **contradicted (minor)** | `git show --stat e1ae38142` = **26 files**, 3081 insertions, 292 deletions. A 2-file under-count in the plan's own footprint claim — noted because footprint fidelity is this plan's own subject. |
| New `post_run_review` frontmatter fact + post-merge band | **corroborated** | `phase-6-finalize/SKILL.md` § "POST-RUN REVIEW (post-merge, `order > 70`)"; the discriminator is DERIVED per-step, and `adr-propose` is documented as the deliberate near-miss (P1 holds, P2 fails). |
| `mutates_source: false` mandatory for band members, enforced at runtime | **corroborated** | `scripts/post_run_source_guard.py` present and registered; dispatcher item 5f sub-item (0) fires it only for `post_run_review: true` steps; advisory, always exits 0. |
| Unresolvable footprint reported as *unmeasurable*, never a confident zero | **corroborated** | `check-artifact-consistency.py` carries the stated `FOOTPRINT_UNRESOLVED` sentinel and the single named predicate `footprint_resolved`, with the docstring warning that `not footprint` is NOT equivalent. |

## 2. The three landing-verification obligations (folded into the spec at the CIS-027 drain)

These were the checklist this analysis owed. Two closed, **one did not**.

### Obligation 1 — the 0%-recall case is gone, `unmeasurable` is reachable ✅ CLOSED

`FOOTPRINT_UNRESOLVED` is a stated sentinel read through one named predicate, and an unresolvable
footprint yields `inconclusive`, never `fail — Recall 0%`. A resolved-but-empty footprint stays a
separate, reportable answer. The measured-vs-unmeasurable split is also carried into the severity
model rather than collapsed onto one bucket.

### Obligation 2 — `base..HEAD` is not in the fallback chain ✅ CLOSED, with a live residue ⚠

The shipped chain is three-tier and `base..HEAD` is absent:

1. **live worktree diff** — `compute_plan_branch_diff(worktree, base_ref)`, a three-dot
   `{base}...HEAD` ∪ porcelain, which excludes the sibling landings that produced the measured
   4.6× over-count on #1079;
2. **legacy key** — `references.modified_files` when PRESENT (present-but-empty is a resolved,
   genuinely-empty footprint);
3. **`FOOTPRINT_UNRESOLVED`** — and it never silently returns an empty set.

⛔ **The residue**: the obligation's recommended tier 2 — *the plan's own merge commit recorded at
`branch-cleanup`* — was **not** implemented. What shipped in that slot is the legacy key, which the
docstring itself scopes to *"archived plans created before the ledger was removed"*. ⇒ For every
NEW plan, the archived path resolves to `FOOTPRINT_UNRESOLVED` permanently. The verdict is now
**honest but permanently unmeasurable**, which is a strict improvement over a confident wrong
answer and is **not** the same as a working measurement. This is exactly `truthful-signals`' filer
framing — *the footprint is derived at read time from a mutable substrate rather than captured
while still true; **capture, don't derive*** — and it stays open. Recorded as an Open Defect.

### ⭐ Correction recorded against my own first reading — the stale-cache mechanism IS the ordering

My initial probe read `plan-retrospective: order 995` and `project:finalize-step-sync-plugin-cache:
order 85` on **post-merge `main`** and concluded that `995 > 85` refuted inbox `…-009`'s claim that
the cache syncs after the retrospective. **That refutation was wrong, and the operator's step list is
what settles it.** The run's actual step sequence was:

```text
branch-cleanup (70) → plan-retrospective → deploy-target (81) → sync-plugin-cache (85) → record-metrics
```

⇒ At runtime `plan-retrospective` sat **between 70 and 81**, not at 995. The 995 I read is the
value **#1080 itself installed**. So `…-009` is correct as observed, and the epic's own
manifest-frozen-at-outline rule is exactly why: the run executed the pre-change order.

⭐ **The useful consequence**: at `order: 995` the retrospective now sorts **after**
`sync-plugin-cache` (85), so #1080 appears to have closed this defect **as a side effect of the
reorder it was written for** — the fix was not aimed at the stale-cache path at all. ⛔ **This is a
derived expectation, not an observation**, and by this plan's own non-self-exercisability rule it
cannot be confirmed from #1080's own run. **Verify it on the next plan composed after this merge**
— the observable is that `check-artifact-consistency` reports `inconclusive` rather than
`fail — Recall 0%`. Recorded as a Watch.

### Obligation 3 — the metrics half ❌ NOT CLOSED

Probed live: `plan-retrospective` declares `order: 995`; `record-metrics` declares `order: 998`.
**995 < 998 ⇒ the retrospective still reads `metrics.md` before `record-metrics` has run.** The
branch's `record-metrics.md` change is a single line — the addition of `post_run_review: true` —
and does not close the accumulator first.

⇒ The #1079 shape survives: the largest phase of a run is read as zero at exactly the moment the
retrospective samples it, understating the Total (measured 2.17× there). The partiality machinery
still labels it correctly, so the number is an honest floor rather than a false total — but the
ordering defect this plan was named for is, in this one instance, **still present in the plan's own
component**. Recorded as an Open Defect.

## 3. The question `truthful-signals` asked explicitly — answered NO

`truthful-signals-029` § 2 asked: *"Please confirm CIS-028 models both [directions]. If #1080 only
relocates post-run steps downward, the `lessons-housekeeping` consumer is still reading an artifact
that does not exist yet."*

**Probed: their prediction is correct and the gap is live.**

| Step | `order` | `mutates_source` | `post_run_review` |
|---|---:|---|---|
| `project:finalize-step-lessons-housekeeping` | **4** | **true** | absent |
| `project:finalize-step-review-retrospective` | 990 | false | true |
| `default:lessons-capture` | 991 | false | true |
| `plan-marshall:plan-retrospective` | 995 | — | — |
| `default:record-metrics` | 998 | false | true |

`lessons-housekeeping` sits at `order: 4` — in the SETTLE band, 991 orders before the retrospective
whose `quality-verification-report.md` it consumes. #1080 relocated the post-run band **downward
only**; the upward-facing consumer was not modelled.

⭐ **And it cannot be fixed by the same mechanism**, which is the part worth recording: band
membership requires `mutates_source: false`, and `lessons-housekeeping` declares
`mutates_source: true`. Relocating it into the post-merge band would put a declared mutator after
the merge gate with no push path — the very defect `post_run_source_guard` was added to detect. ⇒
This is a structural tension, not a missed `order:` edit, and it needs its own remedy.

## 4. Deliverable fidelity vs the shipped surface

| # | Claimed | Verdict |
|---|---|---|
| 1 | `post_run_review` fact + reorder + derivation guard | shipped, corroborated |
| 2 | `head_dependent` declared on HEAD-resolving project-local steps | shipped |
| 3 | Unmeasurable-not-zero reporting; `inconclusive` vs `fail` split | shipped, corroborated |
| 4 | `finalize-step-preference-emitter` orchestration branch (third write site registered) | shipped |
| 5 | TASK-021 runtime tracked-file guard | shipped as `post_run_source_guard.py` |
| 6 | Step Dispatch Table derived from the manifest | shipped |

⭐ **TASK-021 exists because CodeRabbit rejected the plan's chosen remedy.** The plan's own three
rounds of self-review had rewritten three doc sites to *honestly describe* an unenforced property;
the external reviewer's position was that honesty is not the fix. **The correction to the
remediation CLASS came from outside the loop**, not from the loop — see § 6.

## 5. Anomalies and cost

- **10.06M tokens for a 26-file diff** at `scope_estimate=single_module` / `change_type=bug_fix` —
  **7.7× the error anchor** for that row, and past the error anchor for `complex+bug_fix` too.
  `6-finalize` outspent `5-execute`.
- **`pre-submission-self-review`: 13 dispatches, 2,979,307 tokens = 56% of all 6-finalize tokens
  and 30% of the whole plan.** ~157K tokens per finding; **4 of 13 rounds found nothing**
  (~800K tokens spent proving termination). Findings-per-round: `1,1,0 | 3,3,1,1,0 | 4,2,3,0`.
- **17 of 19 self-review findings were prose/contract-consistency; 2 were structural.** Self-review
  filed **zero** of the two CodeRabbit Majors. On a doc-heavy diff the loop converges by exhausting
  prose drift — presented as *"214 candidates surfaced"*, which is **volume, not coverage**.
- **42% of findings (8 of 19) were rework** — three rounds produced prose that TASK-021 invalidated
  within two hours, then three more rounds cleaned up after the fix that invalidated it.
- ⭐ **Rounds 10–11 were worth the whole budget anyway**: they caught two guards whose `clean:
  false` arm was structurally unreachable, on a green suite. Without them #1080 merges a fix that
  can never fire. **The loop is not wasteful; it is unscoped.** Staged as `PLAN-CIS-031`.
- **20 non-zero-exit script calls, 14 unique argparse-rejection signatures** in one run, in a repo
  whose own domain is these scripts. `manage-solution-outline get-deliverable` without
  `--deliverable-number` alone accounted for 5. Staged as `PLAN-CIS-032`.
- `scope_estimate=single_module` was **two bands low**, and it feeds `scope_gated_finalize`, which
  **attempted to drop `plan-marshall:plan-retrospective` from this plan's own manifest** — on the
  run that produced 19 self-review findings and two near-miss vacuous guards. It survived only on
  declared-lane immunity.

## 6. Review behaviour

- **CodeRabbit**: two **Major** findings, both dispositioned FIX-HERE by the operator, 5 tasks
  traceable. **pr-agent (the *required* reviewer)**: *"No major issues detected"*, **0** tasks
  traceable. **Sourcery**: hard-quota throughout — absent.
- ⛔ **After a loop-back CodeRabbit declined to re-review** (*"does not re-review already reviewed
  commits"*), so the PR's **final 8 commits carry no bot review at all** — while the participation
  quorum still read green. The gate asserted *the bots reviewed this PR*; the truthful statement was
  *the bots reviewed an earlier state of it*.
- All three are review-participation concerns and were **forwarded to `review-apparatus`**, not
  tracked here, per the standing three-way routing rule. **Post-merge PR revisit is owed on #1080.**

## 7. Parallelization consequences

**CIS-027 ‖ CIS-028 completed with no collision** — recorded at the CIS-027 landing as a successful
disjointness call and now confirmed through both landings. The feared `extension-api/standards/`
adjacency never materialised.

**CIS-028 ‖ CIS-001 is still running** and remains disjoint (finalize/retrospective vs the content
lookup seam).

⭐ **The WS-04 serialization bar now lifts.** CIS-028 was the plan occupying the `plan-retrospective`
serialization class, which is why `PLAN-CIS-030` was held at the queue head rather than emitted.
With CIS-028 shipped, CIS-030 is admissible.

## 8. Reconciliation actions

- `PLAN-CIS-028` → `shipped`, stamped `pr=1080`, `landing=landings/PLAN-CIS-028.md`,
  `plan_marshall_plan_id=post-run-steps-ordered-before-their-evidence`.
- **3 lessons promoted** to the global corpus; **1 folded** as a recurrence onto an existing lesson.
- **3 new specs staged**: `PLAN-CIS-031` (self-review round scoping), `PLAN-CIS-032` (executor
  pre-spawn invocation validation), `PLAN-CIS-033` (empty-vs-deliberately-minimal skill resolution).
- **4 folds** into existing specs: CIS-016, CIS-013, CIS-011, CIS-030.
- **3 messages forwarded** to `review-apparatus`; **1 reply** to `truthful-signals`.
- **Open Defects added**: the un-captured footprint residue (§ 2, obligation 2), the
  record-metrics/retrospective ordering (§ 2, obligation 3), and the `lessons-housekeeping`
  upward-facing sandwich (§ 3).
