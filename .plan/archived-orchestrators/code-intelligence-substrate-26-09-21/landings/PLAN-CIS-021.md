# Landing Analysis: PLAN-CIS-021 — Self-Review Cannot See a Duplicate-Claimable Key

epic: code-intelligence-substrate
workstream: WS-05
pr: [#1107](https://github.com/cuioss/plan-marshall/pull/1107) (+ #1108, #1109)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims
> against ground truth — a pasted claim is a lead, never a fact.
>
> **Executed in the standalone cloud lane** (`doc/plans/code-intelligence-substrate/self-review-cannot-see-a-duplicate-claimable-key/`),
> not the plan-marshall lifecycle. Its run report is the primary source; every material claim
> below was re-verified first-party against `origin/main`, the merged diff, and the stored PR
> comment bodies.

## Deliverable Fidelity vs Spec

Corroborated against `git show --stat f070d746b` (9 files, +1279/−5) — not from the report's own
account.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 duplicate-claimable-key detector | shipped-modified | `_self_review_detectors.py` (+374), `_self_review_patterns.py` (+76). **Narrowed** by a *validated*-identity conjunct beyond a literal reading of the spec — the D3-forced narrowing the spec's main-risk clause authorizes. Consequence recorded: un-validated duplicate-claimable insertions are out of scope (recall traded for low noise). |
| D2 discard-without-report detector | shipped-as-specified | same files; narrowed to *bare* discards after D3 over-firing (15 → 3 hits). |
| D3 population gate, hits reported separately from files examined | shipped-as-specified | tree-wide sweep; D1=13→14 post-bot-fix, D2=3. Reproducible command + prune set recorded in the run report. |
| D4 tests, each verified to FAIL pre-fix | shipped-as-specified | `test_self_review_defect_regression.py` (+382), `test_self_review.py` (+312). Independently re-proven by the verification sub-agent, which re-extracted `14d4e3d`/`c6b501e` from real git history and diffed them against the fixtures verbatim. |
| D5 documentation | shipped-as-specified | `SKILL.md` (+28), incl. the false-positive posture disclosure. |
| — | added-unplanned | `test_self_review_reachability_regression.py` (±4): the two new keys registered in `_SIBLING_LISTS`. That test exists precisely to force this maintenance and it did its job. |

## Metrics and Anomalies

- Tokens / duration: not captured — the cloud lane persists no `metrics.toon`. ⛔ **A cloud-lane
  landing contributes nothing to the token corpus.** This is a structural gap in the lane, not an
  omission by this run, and it means corpus-wide token figures silently exclude cloud runs.
- Build gate: `./pw quality-gate` → `total_issues: 0`; `./pw module-tests` → **17767 passed, 14
  skipped, 0 failed** (skips pre-existing).
- Anomalies: one `verify / conclusion` failure on `9d2444f` that was **not a real failure** —
  rapid successive report commits superseded the in-flight run and GitHub concurrency cancelled
  it. The run on the latest SHA is authoritative.

## Routing and Merge Behavior

**Review coverage was 1 of 3 bots — verified from the stored comment bodies via `ci pr comments`,
not from a summary or a check state.**

- `cuioss-review-bot` — **the only substantive reviewer.** Filed a correct *False Negative Bug*
  against `_identity_deduped`: `\b{esc}\s+in\b` matched `for KEY in items:` loop headers and
  `\[{esc}\]` matched unrelated `data[key]` reads, both causing D1 to silently **suppress** real
  defects. Disposition: **fixed** in `a3bcd60`, replied on-thread. The fix un-hid exactly one
  genuinely-suppressed candidate (`_status_query.py:679`), moving D1 13 → 14 — no balloon. Three
  unit tests pin it.
- `coderabbitai` — **never reviewed.** "Review limit reached… next review available in 49
  minutes" (OSS rate limit), after its first attempt aborted on a mid-review head change.
- `sourcery-ai` — **never reviewed.** Weekly 500 000-diff-character rate limit. ⚠ The run report
  omits Sourcery entirely; it is an operator-retained reviewer and its silence was a rate limit,
  not a pass.
- `cla-assistant` — `not_signed` badge, non-required, stale.
- CI/merge: squash-merged as `f070d746b`. Report-finalization landed separately as #1108
  (`chore(cloud-plan-lane): finalize report before arming auto-merge`) and #1109. No rebase
  conflicts, no surface collision with any concurrent plan.

⭐ **Recurring pattern, second instance: rapid successive pushes produce single-bot coverage.**
The same mechanism (mid-review head change) that produced #1085's 1-of-3 coverage produced it
here — the pushes both abort in-flight reviews and burn the rate window. A green finalize is not
evidence the bots saw the diff.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-CIS-021 --status shipped`
- [x] row `pr` stamped — `1107`
- [x] row `landing` stamped — `landings/PLAN-CIS-021.md`
- [x] row `plan_marshall_plan_id` — **deliberately left empty**: the cloud lane creates no
      plan-marshall plan, so there is no id to stamp. Not an unstamped gap.
- [x] epic.md queue reconciled from status.json
- [x] cloud plan directory collected (the lane's "gone = collected" state)
- [x] resume_anchor updated

## Follow-Ups

1. **`/sync-plugin-cache` is OWED.** This run edited `marketplace/bundles/` from a cloud session,
   which cannot write `~/.claude/`. Until it runs, the local plugin cache does not carry these
   detectors. ⚠ This is now the **second** outstanding sync debt (the first from #1100).
2. **Consumer prose is stale, and CI structurally cannot catch it.**
   `plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` says "the twenty
   candidate sub-lists" / "sums the fifteen line-level heuristic lists"; the real figures are 22
   and 17. Functionally harmless (the consumer reads `counts.total` from the field, not the prose)
   but ⛔ **the `count_prose` self-review rule only scans skill dirs of files the diff modified, and
   this diff modified nothing in `phase-6-finalize`** — so a cross-bundle count drift is invisible
   to the rule by construction. That gap is itself worth owning.
3. **Consumer Step 3 has no cognitive check for the two new lists.** They surface in the TOON and
   count toward the gate, but no check 16/17 adjudicates them, so a fired D1/D2 candidate does not
   become a filed finding. Cross-bundle change, deliberately out of this plan's boundary.
4. **Lane contract gap already closed by this run** — the Step 8 ↔ Step 9 ordering defect
   (auto-merge armed before the report was finalized; the merge queue then made the finalizing
   push unlandable) was found, presented, approved, and shipped as **#1108**.


---

## ⛔ CORRECTION 2026-08-08 — the coverage figure in this record used the WRONG DENOMINATOR

This landing reports review coverage against the **enumerated roster** (`coderabbitai`,
`sourcery-ai`, `cuioss-review-bot`). That is not the quorum. Read first-party from
`.plan/marshal.json` (`plan.phase-6-finalize.steps.plan-marshall:automatic-review`):

    required_bots = 'pr-agent'          optional_bots = 'coderabbit,sourcery'
    bot_lists_provenance = 'answered'   # a deliberate operator answer, not an unset default

Per `automatic-review/standards/bot-participation-contract.md`, an **optional** bot's silence "never
blocks" and is "not a failure". ⇒ **`cuioss-review-bot` (pr-agent) reviewing is a satisfied quorum,
1 of 1.** The "N of 3" framing above overstates a shortfall that did not exist. The operator
confirmed the classification on 2026-08-08: *sourcery stays optional for this project.*

⭐ **What the error produced that is worth keeping:** `PLAN-TRUTH-061`'s shipped disclosure derives
its population from the registry **roster** and never reads `required_bots`/`optional_bots` — so the
mechanism computes shortfalls against this same wrong denominator. That defect is real, is routed to
`review-apparatus` (`truthful-signals-022.md`), and was only visible because the arithmetic was wrong
here first.
