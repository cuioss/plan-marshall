# Landing Analysis: PLAN-LB-24 — Review step: completion poll, quota recovery, commit currency

epic: live-blockers
workstream: WS-05
pr: #1742 (https://github.com/cuioss/plan-marshall/pull/1742)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-24.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-24-review-step-009.md` (kind `landing`, `landing-check`
`complete: true`; surface delta `unmeasured`, neither a declared nor a realized set supplied).
Checked against:

- `ci pr queue-state --pr-number 1742`: `pr_state: merged`,
  `merge_commit_sha: 7dd1d34338f1fcc3b14c3835ac028156b3f1c8c8`, merge-group run `success`.
- A read-only review of commit 7dd1d3433 against the spec, deliverable by deliverable, by a
  delegated agent that ran nothing. Its verdicts are the table below.

Not read by that review: most of the 13k-line diff body — test bodies beyond their names,
`_findings_core.py`, `post_responses` beyond the hold, trigger B in full, most of the
`bot-participation-contract.md` and `coderabbit.md` rewrites, the user docs, `triage.md`,
`verification-feedback.md`. No test was run here; the merge-group run is the evidence that
the suite passes.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| 1 (LB-05 D3) bounded completion poll | shipped-as-specified | `cmd_bot_completion --wait-seconds` returns `timed_out`/`waited_seconds` (github_pr.py:2738-2792); bots unfinished at the bound go into `display_detail` and the step record |
| 2 (LB-18 D1) rate-window wait handed to the orchestrator | shipped, with a deviation | `rate_window_await` consumed by phase-6-finalize item 7a without an operator prompt; the wait is `merge_lock rate-window wait`, clamped to 480 s per call. The jittered delay after expiry was dropped: 7a re-dispatches the moment the window expires. The live-run evidence the done-when asks for is listed in the PR as still owed |
| 3 (LB-18 D2) reset-time extraction | shipped-as-specified | "Next included review available in" forms in `coderabbit.md`; records carry `eta_seconds`, `eta_extracted` |
| 4 (LB-18 D3) acknowledgments are neither declines nor findings | shipped, with a gap | `acknowledgment_patterns` and `is_acknowledgment_comment` wired into the matcher and the noise filter; the match is a case-sensitive substring, so "Full review triggered." / "Full review finished." are stored as findings and are eligible answers in the matcher. Observed live on #1742 and #1745 |
| 5 (LB-18 D4) no-unreviewed-commit reply | shipped, with a deviation | patterns, `escalated_trigger_comment`, `post_escalated_command` exist; the operator added three outcomes (`accept_review_on_record`, `await_triage`, `leave_to_stale_review`) |
| 6 (LB-18 D5) edited and stale notices | shipped-as-specified | notices sampled by last write; `notice_is_stale` (_github_pr.py:819) |
| 7 (LB-19 D1) trigger every stale bot | shipped-as-specified | `cmd_trigger_bot` returns a list, required bots first |
| 8 (LB-19 D2) wire or delete the currency helpers | shipped, mixed route | `bot_claimed_sha_matches_head` wired; the CI-status half deleted by operator decision; one commit recogniser `commit_tokens` |
| 9 (LB-19 D3) Sourcery currency | shipped as the spec's fallback | disclosure in `reviewed_other_commit_bots[]`, verdict unchanged |
| 10 (LB-19 D4) hold the "fixed" reply | shipped, with a deviation | held until the stamped fix commit is the head or an ancestor; GitHub only; a new `--send-unstamped-fixed` escape; a "reply-covered credit" relaxes currency beyond the spec. Not held until verify is green |
| 11 | per landing facts `deliverables_done=11`; the review grouped the work into ten rows |

Realized surface against the declared one: undeclared — two user docs, manage-findings
`SKILL.md`/`manage-findings.py`/`jsonl-format.md`, `ext-point-triage.md`,
`sonar-roundtrip.md`, two `ref-workflow-architecture` and two `tools-integration-ci`
standards, `workflow-pr-doctor`, `_github_ci.py`, about 28 test modules. Declared, not
touched: `await-long-running.md`, `gitlab_pr.py` (a stated non-goal),
`test_bot_participation_contract_surface.py`.

## Checks carried from the anchor

- **Claim window equals wait budget — confirmed.** Both default to 3600 s; 7a passes no grace,
  so the wake is exactly `expires_at`; a stated window longer than the budget always ends in
  `rate_window_timeout`.
- **Full-review command and acknowledgments — half fixed.** The command is now a registered
  trigger and dropped; the "Full review triggered/finished" replies are still stored.
- **Fixed reply held until commit, not until green — confirmed.** No CI or build result is read.
- **display_detail over 80 characters — only with the suffix.** The rate-window template fills
  to about 64-71 characters, over 80 with `; poll bound hit: {bots}`; it carries an em dash.
  Lesson 2026-10-10-06-004 stays the record.
- **Stale notice settles a required bot that never reviewed — confirmed.** The stale check runs
  before every window and trigger branch and looks at the notice alone; the next pass settles
  it again until the loop-back ceiling. The PR's own follow-ups admit it.
- **"Review in progress" credited as a head-verified review — confirmed by code reading.** The
  matcher applies no participation marker or ignore pattern; `_verifies_head_sha` looks for the
  SHA in the body. No fixture holds the in-progress text.

## Metrics and Anomalies

- Tokens: 15,575,396. Wall time 143,775 s (about 40 hours).
- Self-review used all five fix rounds and was closed by operator decision, then again by
  operator override at two later heads; the CodeRabbit review-fix commits (TASK-23..25) shipped
  without self-review, and CodeRabbit's second round found a real defect in one of them.
- CodeRabbit quota recovery did not recover on its own on the plan's own PR: the main context
  waited and posted `@coderabbitai full review` by hand, twice.
- `scope_creep_check` failed on every task (22 times) with `finding_persist_failed` — since
  fixed by PLAN-LB-33 (#1745).
- Housekeeping Step 1 hit `field_retired` on every firing — the read was replaced by PLAN-LB-32
  (#1741), which merged while this plan was in finalize.
- The lessons corpus dropped from 69 to 0 between two housekeeping firings on 2026-10-09
  (15:25Z and 15:52Z); the `lessons-routing` ingest runs of that day retired the corpus into its
  archive, which is the most likely cause.
- Triage fix tasks were filed under deliverable 10 because `commit-add` rejects deliverable 0.
- Plugin registry repinned to 0.1.1895 by a one-off operator-approved apply.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — 1742
- [x] row `landing` stamped — landings/PLAN-LB-24.md
- [x] row `plan_marshall_plan_id` stamped — lb-24-review-step
- [x] epic.md queue annotation, Open Defects (review-gate follow-ups), Watches updated
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

- Review-gate follow-ups, unowned (lessons 2026-10-10-20-001, -002, -003): stale notice on a
  required bot, in-progress summary credited, case-sensitive acknowledgment.
- Fixed reply released before verify is green; the jittered wake after expiry dropped; live-run
  evidence for D2 still owed.
- Self-review after an operator override carries forward to later heads (lesson
  2026-10-10-20-004).
