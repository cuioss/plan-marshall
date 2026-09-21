# Landing Analysis: PLAN-17 — fast-ci-footprint-gating

epic: plan-optimization
workstream: WS-05
pr: 948 — https://github.com/cuioss/plan-marshall/pull/948 (merged `250f9a4ea`)

> Landing record for one shipped plan. Claims verified against ground truth: PR #948 confirmed
> `state: merged` via the CI abstraction; merge commit `250f9a4ea` on `origin/main`; the merged diff
> inspected (`git show`) — 2 files, the `skip-on-docs-only: true` opt-in against the **v0.11.1** pin
> (corroborating the mid-finalize rebase) plus the CLAUDE.md reconciliation. The "two lines and a doc
> fix" account is accurate.

## Deliverable Fidelity vs Spec

The spec assumed a three-deliverable chain. The analysis/re-grounding **substantially changed the plan**:
D1 (org-side gate) had already landed externally as v0.11.0; D2's pin bump had landed via the automated
#946 — but **the feature was inert** because `skip-on-docs-only` defaults to `false` and nothing had
opted in; and D3's ruleset move was already done (branch protection has required `verify / conclusion`
since 2026-06-23), leaving only stale CLAUDE.md prose. The genuine remaining work was the opt-in plus a
doc fix.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — upstream footprint gate in org `reusable-pyprojectx-verify.yml` | shipped-externally (pre-landed, verified not re-done) | org v0.11.0; consumed here via the pinned `uses:` ref |
| D2 — activate the gate in `python-verify.yml` | shipped-as-specified (the real residual) | `python-verify.yml` +7: `with: skip-on-docs-only: true` against `reusable-pyprojectx-verify.yml@…# v0.11.1` |
| D3 — required check `verify/conclusion` + CLAUDE.md note | shipped-modified (ruleset half already done) | branch protection already required `verify / conclusion` since 2026-06-23; CLAUDE.md +4/-1 reconciled from the stale `verify / verify` name + documents the footprint-skip |

Net: 3/3 accounted for, but only ~1.5 were actually open — a **correctly-shrunk plan**. This is the third
landing this epic where re-grounding found the premise partly pre-shipped (cf. PLAN-19, PLAN-06); the
pattern is now well-established and the outline gate is reliably catching it.

**The gate proved itself mid-run** — the strongest possible acceptance: on the docs-only fix push,
`verify / verify` was **SKIPPED** while `verify / conclusion` reported green (the required check
satisfied, merge queue not stalled); workflow-touching commits still built fully; the merge queue
force-built the merge result.

## Metrics and Anomalies

- Tokens: ~2.78M
- Duration: 39m23s worked
- Anomalies:
  - **⚠ Released another plan's merge lock on an unsound inference** — see Follow-Ups; the most
    significant finding of this landing and a NEW defect, not a plan defect.
  - **Concurrent org bump collision** — #947 (v0.11.1) landed mid-finalize and conflicted on
    `python-verify.yml`; resolved by rebase to the v0.11.1 pin + the opt-in, so main carries both
    (verified in the merged diff). Handled correctly.

## Routing and Merge Behavior

- Review: 1 nitpick fixed, 1 noise suppressed; 2 reviewers compared. Pre-submission self-review clean.
  Two known lesson recurrences forced manual work (see Follow-Ups).
- CI/merge: all 21 finalize steps green; squash-merged via the merge queue. `pre-push-quality-gate` ran
  with 0 bundles / no python footprint and `plugin-doctor` skipped — themselves demonstrations of the
  footprint-gating principle this plan and PLAN-11 encode.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-17 → shipped, pr 948, plan_marshall_plan_id `fast-ci-footprint-gating`, landing recorded
- [x] epic.md queue reconciled from status.json (WS-05 row 17) — **WS-05 COMPLETE** (PLAN-11 + PLAN-17)
- [x] NEW Open Defect opened — merge-lock staleness check queries a worktree-scoped store (see Follow-Ups)
- [x] Watches reinforced — `2026-07-13-21-001` (bot-agnostic rate-limit) and `2026-07-18-05-001` (D3 completeness guard loop_back)
- [x] resume_anchor updated — **PLAN-18's last gate is CLEARED; it is releasable now**
- [x] START-HERE block regenerated

## Follow-Ups

- **⚠ NEW DEFECT (high value, plan-worthy): merge-lock staleness judged from a worktree-scoped store.**
  This run released `steward-provisioning-fail-closed`'s merge lock after `manage-status list` and
  `worktree-list` returned nothing — but those ran with cwd pinned to the releasing plan's own worktree,
  so they only saw a **worktree-local store view**. The plan was live in another session and landed as
  #950. **No damage** (disjoint files, `no_overlap`, both merged cleanly — independently confirmed: #950
  `e45c7ac8f` and #948 `250f9a4ea` are both on main) — but **the check was unsound and the tooling made
  the wrong answer easy to reach.** A staleness test MUST query the main-checkout store, not a
  worktree-scoped view. Same **CWD-keyed store-resolution class** as the known `manage-lessons`
  cross-repo hazard, and the inverse of PLAN-15 #940: that plan hardened the *auto-reclaim* live-worktree
  gate, while this is the *manual release* path, which has no equivalent guard. Wants a lesson AND a
  guard in `merge_lock` (release-under-holder-id already exists; the gap is the staleness *inference*).
- **`2026-07-13-21-001` (bot-agnostic rate-limit) recurred** — a Sourcery rate-limit notice was again
  stored as an actionable finding and had to be suppressed by hand. This is the **PLAN-10 #936 residual**
  already tracked as an Open Defect (4-series); recurrence raises its priority.
- **`2026-07-18-05-001` recurred** — automatic-review's D3 completeness guard fired `loop_back` on
  findings pending for the not-yet-run unified triage; sunset **gemini had to be pruned from
  `enabled_bots` per-plan** again to break the loop. The standing project-wide prune note still applies.
