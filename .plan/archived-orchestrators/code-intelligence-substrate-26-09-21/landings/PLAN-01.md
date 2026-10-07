# Landing: PLAN-01 — inventory-blind-spot

plan: PLAN-01
workstream: WS-01
plan_marshall_plan_id: inventory-blind-spot
pr: 1056
merge_commit: 0f60aaba6
landed: 2026-07-29

## What landed

`fix(inventory): index workflow/references/examples markdown`. Two independent inventories were blind
to the same markdown corpus, and both answered a query about an invisible file with a confident
`count: 0` rather than an honest "not indexed".

Four deliverables, all shipped:

1. `_classify_marketplace` residual rule — name-free AND extension-free: any remaining file under
   `skills/<skill>/**` classifies as `skill_doc`, placed after the build-file and README tests.
2. `FILE_CATEGORIES` vocabulary constant in `_architecture_core.py` — unknown-category now returns
   `status: error`, discriminated by declared vocabulary rather than by the derived files-block keyset.
3. `_classify_generic` peer fix — the same defect in the non-marketplace classifier's own idiom.
4. Doc contract — `standards/client-api.md` category enumeration corrected (adds `skill_doc`, removes
   the phantom `config` category neither classifier could emit).

Deliberately NOT done: `SKILL_SUBDOC_DIRS` in `pm-plugin-development`'s `_dep_index.py` was not
widened (it would have shifted the plugin-doctor lint population by ~14 files). The edge scan got its
own name-free walk plus a guard test pinning `SKILL_SUBDOC_DIRS` at its four current kinds.

## Orchestrator corroboration (ground truth, not the paste)

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1056 merged | **corroborated** | `origin/main` carries `0f60aaba6 fix(inventory): index workflow/references/examples markdown (#1056)` |
| `architecture find --pattern '*light-lane*'` now returns results (was 0) | **corroborated** | Live probe post-cache-sync: `count: 2`, rows carry the new `skill_doc` category |
| Unknown category returns an error listing the valid vocabulary | **corroborated** | Live probe: `status: error`, `error: unknown_category`, `valid_categories[11]` |
| Measured population 6 kinds / 138 markdown (+4 non-markdown) vs the 3 the request named | **accepted as first-party measurement**, not independently re-measured | Plan's own deep-lane discovery; consistent with the shipped name-free rule |

⚠ **New observation the plan did not report, found during corroboration.** The `*light-lane*` probe
returns `count: 2` for **one physical file** — the same path is indexed twice, once as
`default` / `doc` and once as `plan-marshall` / `skill_doc`. The count is a row count, not a file
count. A consumer reading "2 files match" gets a wrong answer, and this is precisely the epic's theme
(a confident count over a substrate whose shape the caller cannot see). Recorded as an Open Defect.

## Deliverable fidelity vs spec

Full fidelity, with one spec-level correction the plan made and recorded: deliverable D2 was **not
implementable as written** (its two rules were the same condition on identical input, because the
files block is built by `setdefault(...).append(...)` so an in-taxonomy-but-empty category is simply
absent). The plan introduced the vocabulary constant to make the discrimination possible rather than
implementing the contradiction. Caught by Q-Gate at `3-outline` as a `severity: error` finding.

## Routing and gate record

- Lane: **init-time operator deep-lane override** (`lane_escalated: true`,
  `escalation_trigger: premise`). Decisive — all three refine-time fix-location hypotheses were wrong,
  including the premise that the two inventories share one enumeration seam.
- Q-Gate 6 findings, all resolved (5 at `3-outline`, 1 at `4-plan`); 2 at `severity: error`.
- `pre-submission-self-review` clean over 39 candidates; `plugin-doctor` clean; `pre-push-quality-gate`
  green; `ci-verify` green.
- ⛔ **Merged with CodeRabbit having never reviewed the diff** (rate-limited; operator merge-anyway).
  pr-agent reviewed clean; sourcery on hard weekly quota. Recorded at WARNING in the plan's own
  decision log. Post-merge revisit is owed per the standing rule.
- Metrics: 3h1m worked / ~3M tokens for a 10-file change. No absolute budget anchor was ever
  applicable — see the `multi_module` vocabulary gap below.

## Reconciliation actions

- `PLAN-01` transitioned `running` → `shipped`; row stamped `pr=1056`,
  `landing=landings/PLAN-01.md`, `plan_marshall_plan_id=inventory-blind-spot`.
- WS-01 remains active — `PLAN-CIS-001 content-search-seam` is still staged in it.
- The `manage-architecture` and `tools-marketplace-inventory` serialization classes are released:
  PLAN-02, PLAN-CIS-001, PLAN-CIS-002 (manage-architecture) and PLAN-CIS-003, PLAN-CIS-006
  (tools-marketplace-inventory) are unblocked by this landing.
- Twelve inbox messages from this plan drained in the same pass (1 landing, 11 candidate-lessons).

## Signals this landing produced for the epic

1. **Review-bot participation re-credit defect** (`fetch_findings` reports a proven reviewer as
   `absent` on loop-back) — forwarded to `truthful-signals`, its theme.
2. **Retrospective runs at step 17, cache sync at 19** — every behavioural probe a finalize step makes
   about its own plan's change reads pre-fix code. Folded into PLAN-CIS-012.
3. **Artifact-consistency reported `Recall 0%` against an already-deleted worktree** where true recall
   is 10/10. Folded into PLAN-CIS-012 as measured evidence.
4. **Compose-time footprint predicate is vacuous** — at phase-4 the footprint is structurally empty for
   every plan. Folded into PLAN-CIS-012.
5. **`multi_module` has no row in the plan-efficiency budget anchors** — no absolute token budget was
   enforceable on a ~3M-token run. Staged as PLAN-CIS-008.
6. **Two done-marked finalize steps (`push`, `ci-verify`) emitted no work-log line**, and a dispatched
   `lessons-capture` emitted no `[DISPATCH]`. Folded into PLAN-CIS-010.
7. **The duplicate-row count** described above. Open Defect, unowned.

## Parallelization note

No collision occurred. PLAN-01 and PLAN-10 ran concurrently on disjoint surfaces
(`manage-architecture`/`tools-marketplace-inventory` vs `manage-metrics`) exactly as staged, and
neither reported a rebase conflict or a re-verify signal. The disjointness call was correct.
