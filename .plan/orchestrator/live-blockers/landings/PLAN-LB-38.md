# Landing Analysis: PLAN-LB-38 — An empty change list runs tests, and the review gate passes only on a finished review

epic: live-blockers
workstream: WS-05
pr: #1752 (https://github.com/cuioss/plan-marshall/pull/1752)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-38.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `plan-lb-38-review-gate-and-empty-scope-005.md` (kind `landing`,
`landing-check` `complete: true`; surface delta `unmeasured`). Checked against:

- `ci pr queue-state --pr-number 1752`: `pr_state: merged`,
  `merge_commit_sha: 4a985a1bf8524280c0079a648045a65924a78569`, merge-group run `success`.
- The merge as it fast-forwarded into the ledger worktree: 49 files, 3744 insertions, 598
  deletions (including `uv.lock`, 353 lines).
- A read-only review of commit 4a985a1bf against the spec by a delegated agent that ran nothing.

Not read by that review: the plan's outline and logs, PR #1752's comments, several test bodies
(dedupe, update-text, stage-post, ci aggregation, fix-stamp source), the secondary documents'
diffs, `bot_registry.py` (so the D10 drop reason is unverified here), `_github_pr.py`. Line
numbers marked `~` in the review came from diff hunk offsets.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 — an empty change list never resolves to "no tests" | shipped-as-specified (refuse) | `resolve-test-scope --changed-paths ""` → `empty_changed_paths`, exit 2, no `divergence_possible`; `architecture resolve --narrow-unit ""` → `empty_narrow_unit`; Step 5(b): with no changed file the leaf omits the flag and resolves by `--plan-id` |
| 2 — "review in progress" is not an answer | shipped, with a deviation | marker gate for CodeRabbit issue comments (`recent_review_start`) and the in-progress hold now withholds any match, including one naming the head (`github_re_review.py` ~1245-1259, ~1633-1678). Fixtures reconstructed (`IN_PROGRESS_RECONSTRUCTED`), because CodeRabbit had overwritten the #1742 bodies |
| 3 — a re-review for one bot is not satisfied by another | shipped; defect confirmed | old docstring "deliberately NO author gate"; now `bot_kind_for_author(...) != bot_kind` skips (~1520-1524); tests parametrized for both bots |
| 4 — a "fixed" reply waits for a green build | shipped, with a deviation | `_pr_head_ci_hold_reason` (`github_pr.py` ~3135) reads the provider's overall check conclusion over non-bot rows, not `ci-verify`; reasons `pr_head_ci_pending/failed/unreadable` |
| 5 — a stale notice re-triggers a required bot with no review | shipped | `resolve_recovery_action` → `trigger_stale_notice` (~957-972); one trigger then `await_window`; spent budget escalates; controls |
| 6 — the quota wait has a margin | shipped, with a deviation | fixed `_RATE_WINDOW_WAKE_MARGIN_SECONDS = 60` as the `--grace-seconds` default, `grace_seconds` in the result; no jitter; the over-budget escalation is an item 7a instruction only |
| 7 — an in-place edit is not a new finding | shipped, operator-changed resolution; defect confirmed | `_stored_pr_comment_hashes` + new `_findings_core.update_finding_text` (+120 lines): updated / reopened / kept_resolved; reopen-on-change by operator decision in finalize |
| 8 — a review bot's status is not CI | shipped; defect confirmed | `_split_review_bot_rows` by the registry's `completion_check_name` set feeds `ci status`, `ci wait`, overall status and the D4 hold; set-aside rows in `review_bot_checks[]` |
| 9 — full-review acknowledgments are noise | shipped-as-specified | `_normalise_acknowledgment_text` casefolds both sides, shared by the noise filter; an edited acknowledgment is recorded once; genuine short review still a finding (control) |
| 10 — pre-PR size-cap check | dropped under its own clause | no registered bot declares a size cap (PR notes; not verified here) |

Realized surface against the declared one: outside the declaration — `uv.lock` (by operator
choice), `manage-findings/scripts/_findings_core.py` (D7), `_github_checks.py` and
`github_ops.py` (D8), nine documents, about 16 test files. Declared and not touched:
`_github_pr.py` (D5 needed no change there), `bot_registry.py` and `create-pr.md` (D10 dropped),
two tests.

## What the plan achieved against its objective

- **Part A met.** An empty change list is refused, and an empty task change set resolves by plan.
- **The gate credits only a finished review of the head — on the re-review path.** In-progress
  answers are held, another bot's review no longer matches, acknowledgments are noise, a bot's
  status is no longer CI.
- **Not on the participation-credit path.** `github_pr.py:1938-2033` is unchanged: it applies the
  refusal exclusion, the marker gate and currency, but never `read_bot_in_progress` or a
  completion check. So an edited, marker-bearing, pre-existing comment is credited while a review
  is running — observed on the plan's own PR, where CodeRabbit was credited
  `participated_but_empty` from such a comment.
- **New hold that never releases on a repository without CI.** With bot rows set aside and no
  other check, the overall status is `none` and the "fixed" reply is held as
  `pr_head_ci_pending` indefinitely; `--send-unstamped-fixed` does not release a stamped finding.
- **Self-recovery: a stale notice now triggers.** The 60-second margin has no jitter, so several
  plans waiting on one bot still re-trigger together.

## Metrics and Anomalies

- Tokens: 9,525,584. Wall 55,586 s (about 15.4 hours). Finalize 3.79M (42 percent).
- `pre-push-quality-gate` failed twice on the root-level guard R5 before passing — third plan in
  a row; the fix commit re-fired three finalize steps.
- `uv.lock` re-locked by every build after the dependabot floor bumps #1743/#1744 landed with a
  stale lock; committed here by operator choice.
- review-retrospective: indeterminate — no `pr-comment` findings, no reviewer content.
- All 16 dispatch-boundary rows keyless — seventh landing.
- Self-review closed without an operator override (`pre-submission-self-review:done`, no
  `may_close=operator_override` fact).
- `archive-plan` pending.

## Collisions with plans in flight

- PLAN-LB-37 (running) declares three files this commit changed: `phase-6-finalize/SKILL.md`
  (item 7a wait and margin, item 7c(0) CI-hold rows), `automatic-review/SKILL.md`
  (rate-window description, acknowledgments, Branch 2 `trigger_stale_notice`), and
  `automatic-review/standards/bot-participation-contract.md`. PLAN-LB-37 must rebase onto
  `4a985a1bf`.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1752; `landing`; `plan_marshall_plan_id`
  plan-lb-38-review-gate-and-empty-scope
- [x] epic.md: the two Open Defects PLAN-LB-38 owned closed or reduced; new Open Defects;
  queue annotation; drain recorded
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- Apply the in-progress / completion check on the participation-credit path (lesson
  `2026-10-12-05-002`).
- Release the CI hold on a repository with no non-bot check.
- Jitter on the rate-window wake; the over-budget escalation in code.
- Advisories left open: the "both are subtracted" wording; the self-response trailing-run guard
  ignores in-place edits; the stale `review_rate_window_timeout_seconds` description.
