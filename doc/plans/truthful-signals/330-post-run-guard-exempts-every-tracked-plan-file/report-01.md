# Run report — 330-post-run-guard-exempts-every-tracked-plan-file (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/post-run-guard-exempts-plans-q4if33` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `plan-marshall:ref-code-quality` (via bundle path)
- `pm-plugin-development:plugin-script-architecture` (via bundle path)
- `plan-marshall:persona-implementer` (via bundle path — production-code work identity)
- `pm-dev-python:python-core` (via bundle path — Python production code)
- `pm-dev-python:pytest-testing` (via bundle path — Python tests)
- `pm-plugin-development:plugin-architecture` — to be loaded before SKILL.md prose edits

## Deliverables

_Filled in as the run proceeds._

### D0 — GATE: classify exemption population + re-derive tracked-file set under `.plan/`

**Verify-first clause (the plan's re-scope gate).** `git ls-files .plan/` at HEAD returned **13 tracked
files** — `.plan/marshal.json` (the project config) plus `.plan/project-architecture/_project.json`
and eleven `.plan/project-architecture/{module}/enriched.json` architecture descriptors. The set is
**non-empty**, so the premise is **CONFIRMED, not refuted** — the plan proceeds unchanged. (Claim-label
row "Files under `.plan/` are git-tracked, including the config and the architecture descriptors":
HYPOTHESIS → **confirmed**.)

**Exemption-population classification** (published with the population it was derived from: a
`.plan`-literal sweep of `marketplace/bundles/**/*.py`, then reading each hit). The classification
criterion: a site is **same-defect** iff it (a) observes **working-tree dirtiness** to decide whether a
step left **unpushable tracked source** behind, and (b) a `.plan/`-prefix drop excludes a git-**tracked**
`.plan/` file from that verdict — a false-clean signal about an unpushable tracked edit.

| # | Site (by symbol) | Classification | Evidence |
|---|---|---|---|
| 1 | `post_run_source_guard.py` — `_PLAN_STATE_PREFIX` const (L91), `filter_tracked_source` (L138) | **same-defect (CONFIRMED)** | porcelain runs `--untracked-files=no` (L179) → input tracked-only; `filter_tracked_source` then drops `.plan/` (L148), so every dropped path is known-tracked. A dirty tracked `.plan/marshal.json` post-gate → reported `clean:true`. |
| 2 | `_invariants.py` — `_filter_main_dirty_paths` (L458–474) | **same-defect (CONFIRMED)** | `return [p for p in paths if not p.startswith('.plan/')]` — per-site copy of the same prefix drop, on the "normal bookkeeping" rationale (docstring L466–469). Input = `git_dirty_files` = `git status --porcelain` **including untracked** (`_git_helpers.py` L71–78), so here the drop hides *tracked* `.plan/` drift. |
| 3 | `_path_attribution_merge.py` (extension-api) | **different-purpose (not a defect)** | The `.plan` strings at L92 / L359 are **illustrative docstring examples** of the generic path normalizer (`_normalize_spelling`/`lookup_claim`). There is **no `.plan/` prefix exemption in executable code**; the module maps path→module ownership, not dirty-source detection. |
| 4 | `check-manifest-consistency.py` — `_BOOKKEEPING_PREFIXES` (L49), `filter_bookkeeping` (L194) | **different-purpose (not a defect)** | Operates on a **committed diff** (`git diff {base}...HEAD --name-only`, L172) — every path already committed and pushable. Dropping tracked `.plan/`+`.claude/` bookkeeping from *footprint classification* (docs-only/tests-only) is correct; a trackedness predicate would *introduce* false positives (committed `.plan/marshal.json` is tracked → would wrongly count as implementation footprint). |
| 5 | `check-routing-decisions.py` — `_BOOKKEEPING_PREFIXES` (L66), `_is_bookkeeping`→`footprint_has_production` (L276–294) | **different-purpose (not a defect)** | Same as #4: operates on the **realized/committed footprint** (`resolve_footprint`/`--diff-file`); the `.plan/`+`.claude/` drop correctly excludes bookkeeping from a *production-code* check. Trackedness predicate would wrongly count committed `.plan/marshal.json` as production code. |
| 6 | `gitignore_setup.py` — `.plan/` constants (L66–93) | **negative-control (EXPECTED)** | Its job *is* `.plan/` gitignoring — the matched negative control. Not touched (plan Out-of-scope). |

**D0 verdict: exactly TWO confirmed same-defect sites** (#1, #2). These are the sites D1 fixes with one
shared predicate and D5 tests against. The three previously-unclassified rows (#3–#5) are **different-purpose**
— the "floor of six" was a literal-string-sweep floor; on reading, four of the six are not the defect
(three different-purpose + one negative control). D0 mutates nothing.

_Verification state: complete. Committed as the D0 GATE checkpoint._

### D1 — Shared trackedness predicate

_pending_

### D2 — Publish examined population

_pending_

### D3 — Fix declared footprint at freeze point

_pending_

### D4 — Disposition for legitimately-dirty tracked `.plan/` file

_pending_

### D5 — Tests (each seen RED pre-fix)

_pending_

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
