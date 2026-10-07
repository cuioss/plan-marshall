# Landing Analysis: PLAN-75 — Manifest Composer Honours The Declared Step Contract

epic: truthful-signals
workstream: WS-01
pr: 1032

> Merged as `8cd280a3a`. ⚠ **Three PRs on one branch** — #1025 and #1031 were closed, #1032 merged.
> The plan's own inbox landing message names #1025, which was written before the recreations.

## What shipped

**2/2** (corrected — an earlier draft of this report said 3/3). Two independently-observed composer
defects closed in one change (19 files, +1407/−182); released at **v0.1.1239**.

- **Defect A — silent omission.** A step that was configured, enabled, and rendered in the auto-posture
  preview (`plan-marshall:plan-retrospective`) was dropped from the composed manifest with no signal.
  ⭐ **Root-caused AWAY from the spec's guess** — not in `_manifest_validation.py` as the spec supposed,
  but in **`_apply_scope_gated_finalize`**, which dropped the step at **candidate-narrowing, before
  lane resolution, with no re-add path.** So *"the declared lane was structurally unreachable, not
  outvoted"* — a materially different defect from the one staged. The fix replaces the
  `automatic-review` special-case carve-out with a **general rule: an implicit scope gate never
  overrides an explicit declaration.**
- **Defect B — ordering inversion.** `finalize-step-preference-emitter` (`order: 61`,
  `mutates_source: true`) sequenced *after* `branch-cleanup` (`order: 70`), placing a source-mutating
  step after the merge gate and making PLAN-44 / #990 **inert at runtime**. ⭐ **The trigger was
  discriminated empirically by driving the real composer**, not argued: **B-ii refuted** (persisted
  steps were byte-identical to the sort's output), **B-i confirmed** (an unresolvable order gets
  *pinned* by the sort and *skipped* by the check, so nobody reports the inversion). **That pairing is
  why the new gate treats `unresolvable_order` as an OFFENCE rather than a skip** — the fix follows
  from the discrimination rather than from the hypothesis.

⇒ **Both halves are verify-first working as designed**: a staged guess was refuted and replaced by a
root cause, and a two-way hypothesis was settled by execution. Worth citing when PLAN-81 argues about
what in-house gates can and cannot establish — here the *plan* did what a structural reviewer could
not, by running the thing.

⭐ **Evidence discipline was exemplary and is worth copying.** Defect B's mechanism was confirmed
empirically before the fix was designed; **two earlier hypotheses were retracted with
orchestrator-verified evidence** (the `default:`-prefix theory and the stale-cache theory), and the
remaining path-resolution hypothesis was carried as *open*, not as a premise. D5's fixtures were
confirmed to FAIL against the pre-fix composer, so the new tests are not vacuous.

## ⛔ The load-bearing finding: this plan merged with ZERO substantive automated review

On **#1025**, all three bots failed at once — **CodeRabbit rate-limited, Sourcery refused the diff as
exceeding its 150000-character ceiling, PR-Agent silent.** `automatic-review` recorded
`0 comment(s) found` / `outcome: done`, while `finalize-step-review-retrospective` independently
recorded *"Review surface absent: rate-limit, diff-size, silent (3 modes)"*.

**The refusal detectors worked correctly — and that is exactly how the finalize signal became
indistinguishable from a clean review.** Zero findings from three refusals renders identically to zero
findings from three clean reviews. This is the epic's own theme landing on the epic's own PR, and it is
**PLAN-92 defect 1 with a merged consequence.** Two of PLAN-92's five defects (the discarded refusal,
the absent required-bot gate) would each have caught it.

## ⭐ The recreate-the-PR recovery path is CONFIRMED to work

The branch's three PRs form a natural experiment, verified first-party:

| PR | State | CodeRabbit |
|---|---|---|
| #1025 | closed | rate-limited (per the plan's report) |
| #1031 | closed | **`Review limit reached`** — refused |
| **#1032** | **merged** | ⭐ **`Actionable comments posted` — a real review** |

**Closing the PR and re-creating it earned a fresh CodeRabbit review.** This materially de-risks
**PLAN-92 D4**, whose primary recovery path is *sleep → rebase → new PR*. ⚠ **It does NOT settle U1**,
which asks whether a **force-push to the same PR** re-triggers — a different mechanism. What is now
confirmed is the **new-PR** leg.

## Reconciliation

- [x] `status` → shipped; `pr` = 1032; `landing` = landings/PLAN-75.md
- [x] Routed: the zero-review finding → **PLAN-92**; the recreate-works evidence → **PLAN-92 D4**
- [ ] `plan_marshall_plan_id` — not reported, not recoverable from the PR; left empty rather than guessed

## Follow-ups from its inbox messages (4, drained via the new `inbox archive` verb)

| Msg | Kind | Disposition |
|---|---|---|
| 001 | landing | folded into this report |
| 002 | candidate-lesson — *"a fully-filtered set of bot refusals produces the same finalize signal as a clean review"* (`component: automatic-review`, its own `suggested_disposition` merges it into `2026-07-27-07-001`) | → **PLAN-92 defect 1**, now with a first-party account from the affected plan |
| 003 | candidate-lesson — plugin-doctor rule-precision defect (cost the extra commit `9caa8c54e`) | → **PLAN-76** (auditor/detector integrity) |
| 004 | candidate-lesson — the script-level `--timeout` default (**300 s**) truncates architecture-resolved long builds on `build-pyproject` too; an orchestrator-tier build with a **~1586 s** resolved envelope ran with the 300 s default | → **PLAN-89**. ⚠ Its own `suggested_disposition` says broaden `2026-07-16-16-003` from `build-maven` to **every** `build-*` wrapper, and note the CLAUDE.md doc gap. **PLAN-62 (#1022) fixed the floor, not this caller-side default** — a distinct, still-open surface |

**Corroboration only, no new lesson:** the change ledger again carried `status: timeout` with
`exit_code: 0` — already covered by `2026-07-27-00-002` and carried in PLAN-59. Third sighting.
