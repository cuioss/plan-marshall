# D1 — the population of footprint reads

The derived population of sites that obtain a plan's file footprint and then **grade** or **decide**
on it, with each site's answer to the D1 question: *can its source be absent at its call time?*

Derived from source by sweeping every call to the three derivation primitives — `compute_plan_branch_diff`,
a read of `references.realized_footprint` / `references.modified_files`, and the shared
`_footprint_resolver.resolve_footprint` — then classifying each caller as provider, grading reader, or
deciding composer. It is not the set of sites the plan named: the plan named three surfaces, and the
sweep found **eleven** grading/deciding sites across **seven** skills — `plan-retrospective`,
`phase-5-execute`, `manage-execution-manifest`, `script-shared`, `manage-config`, `build-pyproject`,
and `manage-tasks` — all within the single `plan-marshall` bundle.

## Counts

| Count | Population |
|---|---|
| **13** | files containing a footprint derivation (providers and consumers together) |
| **5** | providers — derive a footprint, grade nothing |
| **11** | **grading/deciding read sites — the D1 population** |
| **4** | of those 11 that collapsed "unmeasurable" into "measured empty" when this plan started |
| **2** | of those 4 still collapsing when this run began (the other 2 were fixed by sibling plans) |

The affected count and the examined count are separate numbers on purpose: 11 sites were examined, 4
carried the defect.

## Providers — derive, never grade

These answer "what is the footprint"; they take no verdict, so the collapse cannot occur in them.
Each already distinguishes the two states it can return.

| Site | State model |
|---|---|
| `manage-references/scripts/_references_core.py` → `compute_plan_branch_diff` | raises `CalledProcessError` on failure — never silently empty |
| `plan-retrospective/scripts/_footprint_resolver.py` → `resolve_footprint` | `FOOTPRINT_UNRESOLVED` sentinel + `footprint_resolved()` predicate |
| `manage-references/scripts/_cmd_compute_footprint.py` | the producer — writes `references.realized_footprint` while the worktree still exists |
| `manage-references/scripts/manage-references.py` | CLI wiring for the producer |
| `script-shared/scripts/extension/extension_base.py` → `_resolve_plan_footprint` | `None` (unresolvable) vs `[]` (resolvably empty) |

## The D1 population — 11 sites that grade or decide

`Source absent?` answers whether the footprint's source can be missing at that site's call time.

| # | Site | Kind | Source absent? | State when this run began |
|---|---|---|---|---|
| 1 | `check-artifact-consistency.py` → `check_affected_files_recall` | reader / grades | **Yes** — worktree removal is ordered before the retrospective | Sentinel ✅, denominator ❌ |
| 2 | `check-artifact-consistency.py` → `check_affected_files_exact_match` | reader / grades | **Yes** — same call site | Sentinel ✅, denominator ❌ |
| 3 | `check-routing-decisions.py` → mis-prune check | reader / grades | **Yes** — same call site | ✅ reads via `footprint_resolved` |
| 4 | `analyze-logs.py` → ARTIFACT-coverage floor | reader / grades | **Yes** — same call site | ❌ **collapsed** |
| 5 | `verify_failure_scope.py` → `classify_failure_scope` | reader / decides | **Yes** — archived plan, or any git failure | ❌ **collapsed** |
| 6 | `manage-execution-manifest.py` → `_apply_canonical_verify_inactive` | composer / decides | **Yes** — composes at phase-4-plan, before the worktree exists | ✅ fails closed, keeps every step |
| 7 | `manage-execution-manifest.py` → `_apply_security_class_inactive` | composer / decides | **Yes** — same call time | ✅ `None` is no evidence, keeps the step |
| 8 | `extension_base.py` → `should_execute_build` | decider | **Yes** — same call time | ✅ three-valued `unknown` / `not_necessary` / `build` |
| 9 | `manage-config/_cmd_build_map.py` → `build-decision` | decider | **Yes** — delegates to #8 | ✅ surfaces `decision: unknown` with a reason |
| 10 | `build-pyproject/pyproject_build.py` → `cmd_resolve_test_scope` | decider | **Yes** — whole-plan path before materialisation | ✅ `footprint_resolvable` gates the answer, fails closed |
| 11 | `manage-tasks/_cmd_pre_commit_verify_freshness.py` | decider (second-order) | **Yes** — consumes #9's verdict | ✅ consumes the three-valued verdict |

## Adjacent, deliberately excluded

| Site | Why it is not in the population |
|---|---|
| `phase-6-finalize/derive_gate_bundles.py` | Receives the footprint as `--files`; derives nothing. Its caller owns the resolution state. |
| `script-shared/scripts/build/_test_scope_divergence.py` | Pure function over a caller-supplied footprint; documents empty as the one benign verdict. |
| `ext-self-review-plan-marshall/_self_review_diff.py` + `self_review.py` | Collapses unresolvable into empty, but the collapse is **benign by direction**: both states yield "do not filter", which surfaces *more* diff to the reviewer rather than grading anything. Recorded, not fixed — no verdict is derived from it. |
| `automatic-review/review_completeness.py` | Mentions footprint only as prose about reviewer diff-size ceilings. |

## The two independent causes, and how each is discharged

The plan's ⛔⛔ section binds this document to address **both** causes of the coverage failure, or to
split them and say so. Neither is split out; both are discharged, by different means.

**Cause 1 — ordering: the measurement runs after the worktree it derives from is deleted.**
The ordering is **structurally unchanged and was not changed here**. `default:branch-cleanup` is the
merge gate at order **70** and declares `destroys: [worktree]`; the retrospective is a
`post_run_review` step in the **900–999** band (existing members cluster at 990–999). The worktree is
therefore destroyed roughly 900 order-units before the step that reads it.

The plan's ⚠ asks whether that **order** is the DEFAULT or per-plan, because a per-plan order would
narrow the claim and shrink D5. The order is the **DEFAULT**, and structurally so: the bands are a
fixed contract in `extension-api/standards/finalize-step-order-bands.md`, and the merge gate's slot is
"Shared bundle (fixed)", "not a member of any insertable band". The band contract even names this
shape as a defect — *"a step that `reads: [worktree]` is mis-ordered if it runs after the gate"* —
though note that rule keys on a **declaration** the retrospective does not make: it reads the worktree
via `resolve_live_worktree` while declaring no `reads: [worktree]`, so the checkable-fact machinery
would not currently catch this ordering. The substance holds; the enforcement does not reach it.

**But the "fires on every plan" claim IS narrowed, on a different axis than the plan anticipated.**
The ordering is universal; the *step* is not. `plan-retrospective` declares `default_on: false`,
`presets: [full]`, and `lane.class: prunable`, so it runs only where the preset or lane selects it.
D5's affected population is therefore bounded by the plans that actually ran the retrospective, not by
all archived plans — a bound this run cannot quantify, because the corpus is unreachable (D5). Recorded
here rather than left implicit: the plan's polarity note assumed the defect "fires identically on
every plan", and that is true of the *ordering*, not of the *step*.

What discharges cause 1 is not a re-ordering but two remedies already landed on `main` by sibling
plans, which this run verified rather than rebuilt:

1. A **capture-while-true** producer. `branch-cleanup` now calls
   `manage-references capture-footprint` in the step immediately BEFORE removing the worktree —
   "the last moment the plan's realized changes exist on disk as a worktree diff" — persisting
   `references.realized_footprint`. The retrospective then resolves from a recorded fact instead of
   re-deriving from a substrate that has since changed. This also closes the plan's "neither
   documented footprint state" gap: a plan between worktree removal and archival now resolves at
   tier 2.
2. The **`FOOTPRINT_UNRESOLVED` sentinel** at the reader (`_footprint_resolver`), so that when even
   the capture is absent the verdict is `inconclusive` rather than a confident 0%.

**Cause 2 — vacuity: the recall denominator counts read-intent files as expected modifications.**
Discharged by this run (D3). It was **confirmed first-party before being fixed**, and the confirmation
is the point: a fixture of two realized modification-intent files plus three read-intent declarations
scored *"Recall 40% below 70% threshold"* — unpassable by construction, on a perfectly-executed plan.

**Why the trap was real.** Cause 1 was already fixed when this run began. A run that read the plan as
an ordering fix would have found the ordering remedies in place, reported success, and shipped
nothing — while cause 2 stayed live. The green from cause 1 is exactly what would have destroyed the
evidence for cause 2.

**What is and is not established about cause 2's population.** `manage-solution-outline` Check 3b
(`manage-solution-outline.py`) *requires* a valid intent marker on every declared path, so every
**validated** outline carries markers. That establishes the mechanism is reachable — it does **not**
establish how many plans are affected, because the affected set is outlines declaring at least one
`(read)`, which this run did not measure and cannot measure here (the corpus is D5-blocked). Two
further caveats cut against assuming the population is large: the graded corpus is not confined to
validated outlines (this tree's own archived fixture,
`test/plan-marshall/plan-retrospective/fixtures/archived-plan/solution_outline.md`, carries no intent
markers at all), and the retrospective is opt-in (above). **No count is claimed.** The defect is
established by construction — a read-intent declaration cannot appear in a diff — not by a frequency
argument.

## The one line, repeated

The mechanism the plan predicted holds at every defective site: the predicate is a truthiness test —
`if not footprint`, `if footprint and …`, or a `return set()` / `return []` on the failure path — so
*"I could not measure this"* and *"I measured this and it is empty"* select the same branch, and the
branch that wins is the confident one. The remedy is uniform in shape (a third state plus a named
predicate) and **opposite in direction** by side:

- **Readers** (#1–#5) fail **open** to an explicit unknown: an inconclusive verdict is the correct
  answer when the input was never measured.
- **Composers** (#6–#11) fail **closed**: they keep the gate. Keeping a step is recoverable; dropping
  one removes a gate from the run and cannot be recovered after the fact.

That asymmetry is why the two sides cannot share one fix.
