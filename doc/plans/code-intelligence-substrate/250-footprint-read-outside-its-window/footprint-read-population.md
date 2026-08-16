# D1 — the population of footprint reads

The derived population of sites that obtain a plan's file footprint and then **grade** or **decide**
on it, with each site's answer to the D1 question: *can its source be absent at its call time?*

Derived from source by sweeping every call to the three derivation primitives — `compute_plan_branch_diff`,
a read of `references.realized_footprint` / `references.modified_files`, and the shared
`_footprint_resolver.resolve_footprint` — then classifying each caller as provider, grading reader, or
deciding composer. It is not the set of sites the plan named: the plan named three surfaces, and the
sweep found **eleven** grading/deciding sites across **six** bundles' skills.

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
| `script-shared/scripts/build/_references_core.py` → `compute_plan_branch_diff` | raises `CalledProcessError` on failure — never silently empty |
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
| 6 | `manage-execution-manifest.py` → `_apply_footprint_gated_canonical_prefilter` | composer / decides | **Yes** — composes at phase-4-plan, before the worktree exists | ✅ fails closed, keeps every step |
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
