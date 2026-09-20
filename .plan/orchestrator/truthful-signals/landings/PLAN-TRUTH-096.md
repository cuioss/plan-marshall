# Landing Analysis: PLAN-TRUTH-096 — orchestrator-inbox-and-landing-residue

epic: truthful-signals
workstream: WS-01
pr: 1338 (https://github.com/cuioss/plan-marshall/pull/1338), merged as `77db1a0d3`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying every
> material claim against ground truth. The operator paste and the plan's own inbox landing
> message were both treated as leads, never as facts.

## Deliverable Fidelity vs Spec

**The paste reports "9 deliverables"; the staged spec declares seven (D0–D6).** The two numbers
partition different sets: the solution outline renumbered D0–D6 into a finer D1–D9, splitting the
spec's D1 across three shipped items and D6 across two. This was checked because a 9-vs-7 count is
exactly the shape this epic exists to catch — the verdict is that no deliverable was dropped.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — re-derive the landing-completeness key classification | shipped-as-specified | `landing-payload-spec.md` +36; the per-key table is live — `landing-check` on message 012 now returns `missing_keys: [pr]` rather than accepting the degraded value |
| D1 — an unreadable `merge_state` is not a supplied fact | shipped-as-specified | `_orchestrator_inbox.py` +131 / `test_landing_completeness.py` +610; producer surfaces reconciled in `branch-cleanup.md`, `emit-landing.md`, `landing-payload-spec.md` |
| D2 — one in-place-edit count, stated once | shipped-as-specified | `inbox-envelope.md` (1 line, the deferring clause) |
| D3 — pin `--workflow` at the three dispatch doc sites | shipped-as-specified | `test_orchestrator_dispatch_workflow_pin.py` +265 (new); `effort-roles.md`, `ext-point-finalize-step.md`, `marshal-json-reference.md`, `analyze.md` |
| D4 — derive the collateral and survivor lists at report time | shipped-as-specified | **Verified specifically**, because no paste item names it: it landed as the "derived-figure timing rule" in `emit-landing.md`'s Ordering-rationale section (+55). Closes 520/G1, G2, G3, G5 by their shared cause rather than per-figure |
| D5 — per-sender archive migration for the two sibling epics | shipped-as-specified | Recorded per the deliverable's own terms (have it run and its counts recorded); the write stays outside this epic's boundary |
| D6 — correct the `_marker_indices` docstring return contract | shipped-as-specified | `orchestrator.py`: the two-shape return `(-1,-1)` / `(begin,-1)` is now stated, replacing a contract that described a case the code cannot produce |
| *(added, unplanned)* — settle why `emit-landing` did not fire, port the activation predicate | added-unplanned | `manifest-schema.md` +32: an activation predicate read from a persisted list freezes the capability set, so "never seen" and "explicitly declined" render identically; plus the relocation corollary |

Diff scope: 16 files, +1330 / −78, `9999f4d87..77db1a0d3`.

**One correction to the sibling epic's report of this landing.** `code-intelligence-substrate`'s
inbox message 026 quotes the `re.IGNORECASE` fix as a one-line diff on `CLAIM_LABELS_HEADING_RE`.
The commit applies it to **both** addressed headings — `EXPECTED_SURFACE_HEADING_RE` took the same
flag in the same hunk. Their conclusion is unaffected; the scope of the fix is one line wider than
reported.

## Metrics and Anomalies

- Tokens: **6,854,098** total (landing-facts `total_tokens`); the plan's own efficiency aspect
  measured **6,443,862** dispatched against an anchor that warns at 800K and errors at 1.3M for
  `scope_estimate=single_module` / `change_type=bug_fix` — **roughly 5× the error anchor**, and that
  figure is a floor (`1-init` carries no token record and `6-finalize` was never closed by `end-phase`).
- Duration: 114,906 s wall (**31h55m**).
- Concentration: finalize. Self-review alone burned **7 firings, 6 of them failed** (message 007).
- Anomalies:
  - `billing_weighted_total` is **structurally unmeasured** at retrospective `order: 995` —
    `population_count: 0`, every `Billing (cost)` cell rendered `-`. Nothing calls `manage-metrics
    enrich` before the reader (message 008).
  - All four per-dispatch context-load columns are `unmeasured` across **19 of 19** rows in three
    phases — the recorder honours the contract, no call site populates it (message 006).
  - `[ARTIFACT]` emission fired for **1 of 18** completed tasks, and the rule that would size the
    other 17 could not run because the footprint was unresolvable (message 004).

## Routing and Merge Behavior

- Review: 21 comments on the PR — **coderabbitai 10, sourcery-ai 2, cuioss-review-bot 2**, and the
  plan's own 7 responses. **`pr-agent` — the bot `marshal.json` declares as `required_bots` —
  contributed zero.** The two `optional_bots` produced every actionable finding: 6 filed
  (5 `fixed`, 1 `taken_into_account`). The finalize step's "0 comment(s) found — 2 reviewed, 1 empty"
  is a re-review round zero, not the PR's comment population.
- **7 threads remain unresolved on the merged PR** (`ci pr comments`: `total: 21`, `unresolved: 7`).
- CI/merge: green at `cccdb08d9`; merged **via the merge queue** as `77db1a0d3`; `branch-cleanup`
  recorded `merge_state=merged`, `merge_mechanism=merge_queue`, `action=noop`. Sync-baseline rebased
  onto `origin/main` over 3 upstream commits. No conflicts, no re-verify signal.
- Surface collisions: none observed against the three concurrently-running plans.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-TRUTH-096 --status shipped`
- [x] row `pr` stamped — `1338`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-096.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator-inbox-and-landing-residue`
- [x] epic.md narrative reconciled; both GENERATED blocks regenerated from status.json
- [x] 13 inbox messages drained (12 from this plan + 1 from `code-intelligence-substrate`)
- [x] Open Defects opened: landing incomplete at `pr`; three defect-bearing findings archived
      `pending`; message 009 amended outside the `inbox amend` verb; prep-ready gate vacuous over
      19 specs; required review bot silent
- [x] resume_anchor updated

## Follow-Ups

| Item | Disposition |
|------|-------------|
| Footprint unresolvable — five consumers degraded, none aggregated (msg 001) | folded → PLAN-TRUTH-098 Arm 1 |
| `affected_files` diverges both ways: 13 declared / 16 landed (msg 003) | folded → PLAN-TRUTH-098 Arm 2 |
| Chat-history aspect analysed 1 of 2 recorded sessions (msg 002) | folded → PLAN-TRUTH-111 |
| `[ARTIFACT]` emitted for 1 of 18 tasks (msg 004) | folded → PLAN-TRUTH-089 DC |
| Permission-prompt aspect emits an unfalsifiable `prompts[0]` (msg 005) | folded → PLAN-TRUTH-104 |
| Context-load columns unfed, 19/19 `unmeasured` (msg 006) | folded → PLAN-TRUTH-097 F2 |
| Finalize re-fire burn — 7 self-review firings, 6 failed (msg 007) | folded → PLAN-TRUTH-097 DB |
| `billing_weighted_total` unmeasured at order 995 (msg 008) | folded → PLAN-TRUTH-097 F2 |
| `signal_qgate_pending_count` carries pending-plus-resolved (msg 009) | folded → PLAN-TRUTH-111 |
| Internal rejection reversed only after two external bots re-raised it (msg 010) | forwarded → `review-apparatus` |
| `sync-plugin-cache` staleness guard names the wrong cause (msg 011, finding `5721cb`) | folded → PLAN-TRUTH-086 |
| `create-pr` recorded no `pr_number` typed fact (finding `e9ef2c`, **error**) | folded → PLAN-TRUTH-106 |
| Preference-emitter attribution gate tests the sentinel, not set membership (finding `5ed45d`) | folded → PLAN-TRUTH-093 |
| Claim sections in table form parse to zero claims (CIS msg 026) | observed → Open Defect; remedy owned by `PLAN-CIS-051` |
