# Landing Analysis: PLAN-CIS-053 — Test-Suite Anti-Vacuity

epic: code-intelligence-substrate
workstream: WS-07
pr: 1443 — https://github.com/cuioss/plan-marshall/pull/1443

## Ground Truth Corroborated Before Any Ledger Write

The landing narrative is a lead. Each headline fact was checked against a first-party
source before this record was written:

| Claim | Checked against | Verdict |
|-------|-----------------|---------|
| PR #1443 merged | `ci pr view --pr-number 1443` → `state: merged` | corroborated |
| merge commit `33c8140f3` | `merge_commit_sha 33c8140f3c6bad…` == `git log main` HEAD | corroborated |
| supersedes #1442, #1430 | PR body states both closed unmerged, same branch | corroborated (PR body) |
| plan archived | archive dir `2026-09-07-test-suite-anti-vacuity` | reported, not re-read |

## Deliverable Fidelity vs Spec

The staged spec's own claim section was re-grounded at HEAD `28b578f1e` two days before
this landing (section verdict `corroborated`, 10 rows: 4 corroborated / 6 unverifiable /
0 refuted). The load-bearing row — the `conftest.py` bootstrap blind to a TOON-status
failure — is among the shipped fixes, so the plan closed the defect its own re-grounding
had just re-confirmed live.

| Deliverable | Verdict | Evidence |
|-------------|---------|----------|
| D1 self-referential oracles → independent producers | shipped-as-specified | PR body: `scan_dispatch_classes` derives the population from the call graph |
| D2 guarded populations derived from complete source | shipped-as-specified | exclusion tuple asserted EQUAL to its non-registering complement |
| D3 preconditions that discriminate | shipped-as-specified | `len(edges) > len(owners)`; declared `requires-python` floor read from `pyproject.toml` |
| D4 fixtures take the route their tests name | shipped-as-specified | seam-resolve detector reads `--workflow` off the resolve's own command block |
| D5 detector predicates bound to their scenario | shipped-as-specified | archived-write prohibition bound to the directory as write TARGET |
| D6 assertions bound to their mechanism | shipped-as-specified | executor-refresh phrase assertion section-bound; unimportable-sink test instruments the failed resolution |
| production fix (unplanned, in scope) | added-unplanned | bare `except Exception: return` in `_emit_skills_by_profile_staleness_warning` narrowed to the registry-dependent message |
| `max_iterations` 17 → 5 (unplanned) | added-unplanned | a per-run bot-retry budget had been written into project-wide tracked config; resulting file byte-identical to its pre-change blob |

## Metrics and Anomalies

- Tokens: **17.2M / 376M billing-weighted** against a 2.5M anchor — **6.5×**, and the
  landing calls it a floor.
- Duration: 11h57m worked. 22 tasks, 53 files, 25 230 tests green whole-tree.
- **Anomaly — 93% of the head-dependent re-fire cycle was uninformative.** Six
  head-bound steps fired 44 times; five of them (38 firings) produced zero findings for
  the whole run. Only `pre-submission-self-review` ever went red (4 findings, 3
  loop-backs). `pyproject_build` owns 50.3% of all script time, driven by steps that
  never turned red. ⇒ The entire detection surface was **two** gates.
- Anomaly — the plan's own defect archetype recurred **five times inside its own fixes
  for it**, each strictly narrower than the last.

## Routing and Merge Behavior

- Review: 25 actionable CodeRabbit findings across 5 rounds, 19 fixed, 72%
  resolved-as-fixed, zero rejected, zero style-lint noise. **Four of its rounds each
  found a defect in the fixes for the round before.**
- ⛔ Reviewer asymmetry: `cuioss-review-bot` participated repeatedly with **every
  artifact empty**; `sourcery` refused structurally on every pass (7 848-line diff
  against a 150 000-character cap). Neither is recordable as a measurement — filed as
  `1b0984`. Only **1 of 3** reviewers was measurable.
- CI/merge: CI green, 0 findings filed; merged via the merge queue as `33c8140f3`.
- Recovery path used: the branch was reopened twice (#1430, #1442 closed unmerged) to
  recover a CodeRabbit rate window.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-CIS-053 --status shipped`
- [x] row `pr` stamped — `1443`
- [x] row `landing` stamped — `landings/PLAN-CIS-053.md`
- [x] row `plan_marshall_plan_id` stamped — `test-suite-anti-vacuity`
- [x] landing message archived — `inbox archive --message test-suite-anti-vacuity-001.md`
- [x] Open Defect opened — incomplete landing payload (below)
- [x] resume_anchor updated; START-HERE and Ordered Queue regenerated via `compact`

## Open Defects Opened By This Landing

**D-L1 — the landing message carries no machine-readable facts block.**
`inbox landing-check` returns `complete: false` with `missing_keys` = the **whole**
required set of 8 (`schema`, `plan_id`, `pr`, `merge_state`, `deliverables_total`,
`deliverables_done`, `total_tokens`, `steps`). This is the pre-fix prose-only shape.
Every fact in this record was therefore recovered by hand from the PR and from git,
not drained. The verdict is not a fault and did not block reconciliation — but it means
a later paste from this plan may still surface something the inbox did not.

**D-L2 — the run's own routed-defect counts disagree three ways, and the landing
under-records.** Derived by enumerating every message this sender wrote across all
epics:

| Source | Defects claimed routed | Inbox writes claimed |
|--------|-----------------------|----------------------|
| PR #1443 body | 7 | — |
| landing message | 9 | 4 |
| operator report | 10 | 5 |
| **derived (filesystem)** | — | **5** |

Five finding messages exist: `review-apparatus` 001 (archived), 002, 003 (queued);
`truthful-signals` 001, 002 (both archived). The operator's 5 is correct; the landing
message's 4 is an under-count. ⛔ A `truthful-signals` `inbox list` reports `count: 0`
because that verb does not enumerate archived messages — reading that zero as "nothing
was written" is the error this row exists to prevent.

## Follow-Ups

- **Lesson `2026-09-07-21-001` — two-sided bracketing.** An arm placed *inside* an
  accepted region proves the region is at least that wide and is silent on it being too
  wide. Four such arms look thorough and are a one-sided proof; every one of the five
  recurrences entered through the side no arm watched. Proven by probe, not argued:
  widening the heading terminator's `{0,3}` to any indent left all four ADMIT arms, the
  level-4 control **and** the live-document assertion green. Rule: for a *bound*, require
  one arm that reddens on widening and one on narrowing, and state in the fix record
  which direction each arm pins.
- **Eight instructions passed down were refuted by measurement** — three in task
  descriptions, five premises supplied to dispatches, including "no further CodeRabbit
  round is obtainable" and calling a fix "structurally immune" when it wasn't. Each
  refutation is recorded in the commit or decision-log entry carrying it rather than
  quietly corrected. This is the same discipline the epic's re-grounding pass applies to
  staged specs, now observed applying to in-flight instructions.
- **Head-dependent re-fire waste is a measured, un-owned defect.** 93% uninformative,
  with `pyproject_build` at 50.3% of script time. It belongs with the epic's cost work
  (WS-04/WS-06) rather than with this plan. Not yet staged.
- **Owed by this plan, disclosed rather than hidden**: the production pending-worktree
  gate in `_resolve_declared_footprint` (declined twice with recorded reasons; its
  absence is disclosed in the shipped docstring).
