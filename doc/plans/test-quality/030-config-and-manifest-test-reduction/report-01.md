# Run report — 030-config-and-manifest-test-reduction (run 01)

**Date (UTC):** 2026-08-16    **Branch:** `claude/config-manifest-test-reduction-0eod0y`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) |
| `pm-dev-python:pytest-testing` | bundle path — `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` |
| `plan-marshall:persona-module-tester` | bundle path (module-budget section) |

## Gating derivations (run before D1)

### Plans `010` and `020` have landed — CONFIRMED

- `grep -n 'def parse_ns' test/conftest.py` → `569:def parse_ns(...)`. Present.
- Module budget: `persona-module-tester/standards/testing-methodology.md:75` → **400 lines**, enforced by
  `plugin-doctor`'s `test-module-line-budget`. Present.

### Partition check — DEFECT FOUND, dispositioned by the operator

Derived mechanically over every directory under `test/plan-marshall/*/` (69), every file at the root of
`test/plan-marshall/` (12), and every top-level `test/` entry other than `plan-marshall/` (23), each
checked against the Expected surface of `030`–`080`.

- **Duplicates (an entry in two lists): none.**
- **Unclaimed entries: three.**

| Entry | Status |
|---|---|
| `test/README.md` | Claimed by plan `020` (epic README § concurrency table). Not a `.py` file. Not a defect; the README's named-exclusion list is short by this entry. |
| `test/test_shared_harness.py` | Claimed by plan `020` (`020/plan.md:174`, D5 — created by that plan). Not a defect; a fourth de-facto exclusion the README's list does not name. |
| `test/pm-code-intelligence/` | **Claimed by no plan at all.** Added 2026-08-15 by `c86de8b` (PR #1243), *after* the test-quality plans were authored — exactly the failure mode the epic README predicts. One file, 260 lines. |

**Disposition:** the operator was asked and stated the `pm-code-intelligence` gap is handled by another
plan. The halting condition is therefore released by operator decision, not by this run's own judgement,
and this run claims nothing outside its six directories.

Line-sum check: corpus `test_*.py` total **387,521**; the six slices sum to **386,879**; the
**642**-line difference is exactly `test/pm-code-intelligence/` (260) + `test/test_shared_harness.py`
(382). No gap and no overlap beyond the three entries above.

### D1 family membership — re-derived, plan's OBSERVED claim CONFIRMED exactly

`grep -o '^def test_default_plan_finalize_includes_[a-z_0-9]*'` and the `get_default_config` sibling,
suffixes extracted separately and intersected:

- `test_default_plan_finalize_includes_*`: **7** functions.
- `test_get_default_config_includes_*`: **15** functions. Total **22**, matching the lead.
- **Intersection: exactly 3** — `admin_merge_on_stuck_state`, `auto_rebase_threshold`,
  `merge_queue_wait_budget_seconds`. Matches the plan's named three.

**The higher-risk HYPOTHESIS ("every pair asserts only the same thing") — read, and it is FALSE in the
run's favour.** All 22 bodies were read before any collapse. Findings:

1. Both prefixes reach the knob through the **same** accessor —
   `_params_for(config['plan']['phase-6-finalize']['steps'], 'default:branch-cleanup')`. The plan's
   "two accessors" framing does not hold at the code level; the prefix difference is historical.
2. All **7** `default_plan_finalize` members carry a third assertion the `get_default_config` members
   do not: the `'{knob}' not in DEFAULT_PLAN_FINALIZE` **negative**. It is uniform across all 7, so it
   survives as a body assertion of the collapsed table rather than as an extra column.
3. The 3 `get_default_config` members for the crossed knobs assert a strict **subset**. They are kept
   as their own 3-row table rather than dropped, so the collected count is preserved exactly (7 + 3
   functions → 7 + 3 parametrized cases).

## Baselines (before)

| Measure | Value | Command |
|---|---|---|
| Slice lines (`test_*.py`) | **54,616** | `wc -l $(find <six dirs> -name 'test_*.py')` |
| Collected tests | **2,711** | `uv run python -m pytest <six dirs> --collect-only -q -o addopts=""` |
| `@pytest.mark.parametrize` decorators | **67** | `grep -rn` over the six dirs |
| `def test_` declarations | **2,450** | `grep -rn '^def test_\|^    def test_'` |
| `monkeypatch.setattr` calls | **257** | `grep -rn` over the six dirs |
| `@pytest.fixture` declarations | **13** | `grep -rn` over the six dirs |
| setattr : fixture ratio | **19.8 : 1** | derived from the two rows above |

Per-directory lines: `manage-config` 22,648 · `manage-execution-manifest` 20,069 ·
`manage-run-config` 4,113 · `marshall-steward` 3,788 · `manage-solution-outline` 2,595 ·
`manage-references` 1,403.

Plugin-doctor `test-conventions` per-rule, before (finding rows only, summary count-lines excluded):

| Rule | m-config | m-exec-manifest | m-run-config | m-references | m-sol-outline | steward | **Total** |
|---|---|---|---|---|---|---|---|
| `test-docstring-historical-prose` | 9 | 13 | 0 | 1 | 1 | 0 | **24** |
| `test-module-line-budget` | 18 | 14 | 3 | 2 | 3 | 1 | **41** |
| `test-module-preamble-boilerplate` | 63 | 60 | 2 | 0 | 4 | 8 | **137** |
| `test-helper-module-misnamed` | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

## Deliverables

_in progress_

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
