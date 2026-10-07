# PLAN-24: Automatic-review recovery and PR record integrity

> ✅ **Staged 2026-09-29 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-24-review-and-pr-record-integrity.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make the review-bot recovery path completable from where it runs, make it read bot responses correctly,
and make the PR records downstream steps read describe the PR that actually merged. In the PLAN-12 run:
- the rate-window recovery could not complete inside its dispatched leaf, three times;
- a CodeRabbit "Review triggered" acknowledgment was matched as a decline while the review was still
  running;
- two status replies were charged to CodeRabbit as false positives;
- the `create-pr` record kept naming #1653 after close-and-reopen replaced it with #1654, which is what
  merged.

## Deliverables

1. **The rate-window await leaves the leaf.** `plan-marshall:automatic-review` is a DISPATCHED step with a
   900 s budget. Its recovery claims a 3600 s rate window, then paces a standalone `sleep 60`, and later a
   jittered wake of `delay_seconds: 1052.77`. The harness rejects the foreground `sleep`, and neither wait
   fits inside the leaf's budget or under the 600 s Bash ceiling. The leaf returned
   `status: blocked, reason: rate_window_await_unreachable_in_leaf`, and the item-5d guard then recorded
   `failed`. Route the await to the orchestrator as an `escalate_ask`-class return carrying
   `claim_expires_at`, and let item 7a wait in the main context through the await-long-running seam
   before re-dispatching. Also:
   - Refresh `coderabbit.md`'s `rate_limit_eta_patterns`: "Next included review available in 38
     minutes." yielded an empty ETA, so the claim fell back to 3600 s instead of ~2280 s.
   - Make `assert-step-recorded --require-terminal` distinguish this dispatch's record from an earlier
     attempt's. On retry it returned `recorded: true, outcome: failed` from attempt 1's stale record.
2. **An acknowledgment is not a decline.** `github_re_review re-review` matched CodeRabbit's "Action
   performed — Review triggered." (`matched: true, head_sha_verified: false`) and routed it to
   `declined`, while `bot_completion` reported `in_progress: true`. The resulting escalation offered
   "Merge anyway — proceed unreviewed" against a review that was running. Classify acknowledgment
   comments as `acknowledged` and continue into the completion poll, and treat `in_progress: true` as
   authoritative over an unverified issue-comment match. The loop-back path must also re-trigger every
   stale required bot, not only the one it selected (cuioss-review-bot was never re-triggered).
3. **Bot status replies are not findings, and a false-positive metric reads more than the enum.** Two
   issues:
   - `fetch_findings` stored CodeRabbit's "Action performed — Review finished" replies (`7447e1`,
     `63896b`) as `pr-comment` findings. Triage could only reject them, and the review retrospective
     then charged CodeRabbit 2 false positives. Classify acknowledgment replies to our own trigger as
     noise, alongside `own_trigger` / `refusal`.
   - A row resolved `taken_into_account` whose detail begins "False positive: …" (`63a935`) was
     counted as zero false positives until it was corrected by hand. Cross-check the resolution
     against its own detail, or require `rejected` for a detail that asserts a false positive.
4. **Close-and-reopen re-stamps the PR record.** The `create-pr` step record kept `facts.pr_number: "1653"`
   and `display_detail: "#1653"`. The work log records the switch ("SKIP create-pr (done, PR #1654 via
   close_and_reopen)"), but no step rewrote the fact, and the landing message then carried `pr=#1653`.
   Re-record the step when a PR is replaced, or have consumers read the live PR, and add a pre-merge
   check that the create-pr fact names the PR being merged.

**Re-scoped at cleanup 2026-09-29 (HEAD `56add3f`):**
- **D1 stale-record facet:** `assert-step-recorded` already takes `--min-firing-count` and refuses an
  older firing's record (`_cmd_assert_step_recorded.py:176-212`), but phase-6-finalize item 5d never
  passes it. The facet is **wiring the flag at item 5d**, not new verb logic. It shares the
  `firing_count` substrate with PLAN-21 D2: a re-stamp that inflates `firing_count` defeats this guard,
  so land PLAN-21 D2 first, or together.
- **D4 locus:** the close-and-reopen is performed by `automatic-review` SKILL.md Branch 5 (:761-795)
  through the `ci pr` verbs in `tools-integration-ci/standards/pr-review-operations.md`. The only
  `pr_number` re-bind there is a local variable plus a log line. `github_re_review.py` only names the
  action (`RECOVERY_ACTION_CLOSE_AND_REOPEN`). The re-stamp belongs in Branch 5.

## Claim Labels

- OBSERVED: rate-window await unreachable in the leaf (sleep rejected; 3600 s window vs 900 s budget; 1053 s jittered wake vs 600 s ceiling); stale-record guard satisfied on retry; ETA pattern miss — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-014.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: automatic-review SKILL.md:180 900s budget, :596 sleep 60, :640 sleep {delay_seconds} in leaf; coderabbit.md:77-80 ETA regexes miss 'available in N minutes'; item 5d omits --min-firing-count
- OBSERVED: "Review triggered" matched as a decline while `bot_completion in_progress: true` — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-029.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: github_re_review._match_bot_comment:1079-1097 accepts any non-refusal bot comment; _verifies_head_sha:306-333 false -> SKILL.md:260 declined; no 'Review triggered' class
- OBSERVED: acknowledgment replies filed as findings and counted as false positives; `taken_into_account` with a "False positive:" detail — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-030.md` §§ 1–2; post-merge correction recorded in the landing `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-013.md` § Residue
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: coderabbit.md ignore_patterns:58-65 lack 'Action performed'; review-retrospective SKILL.md:44-48 counts only rejected as false positive
- OBSERVED: create-pr record names #1653 while #1654 merged — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-012.md`, `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-030.md` § 3; corroborated by the orchestrator (PR #1654 `state: merged`, merge `26f864b`; the landing facts block carries `pr=#1653`)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: only pr_number re-bind is automatic-review SKILL.md Branch 5:775-795 (local var + log); nothing re-records create-pr facts; no pre-merge fact check
- HYPOTHESIS (**refuted and re-scoped at cleanup 2026-09-29**: it is `automatic-review/SKILL.md` Branch 5; `github_re_review.py` only names the action): the close-and-reopen path lives in `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` and `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` (both name `close_and_reopen` at HEAD) — confirm/refute which one creates the new PR (verify-at-outline)
  - verdict: contradicted | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: yes | evidence: github_re_review.py only names the action (RECOVERY_ACTION_CLOSE_AND_REOPEN:520, :652-653); automatic-review SKILL.md Branch 5:761-795 performs it via ci pr verbs; spec re-scoped in place

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — rate-window recovery, close-and-reopen
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — ETA patterns, acknowledgment classes
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — response matcher
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `fetch_findings` / `bot_completion`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — `fetch_findings` classification
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 5d terminal-record guard, item 7a await consumer
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md` — create-pr record re-stamp
- OBSERVED: `.claude/skills/finalize-step-review-retrospective/` — false-positive metric
- OBSERVED: `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `test/plan-marshall/automatic-review/`
- OBSERVED: `test/plan-marshall/finalize-step-review-retrospective/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-review-operations.md` — close-and-reopen invocations and `pr_number` re-bind (D4) (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `trigger-bot` picks a single bot (D2 re-trigger all stale bots) (added cleanup 2026-09-29 at 56add3f — understated surface)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-20 / PLAN-21 / PLAN-23 (`phase-6-finalize/SKILL.md`). Sequence among the finalize cluster.
- Ownership note: this is PR/review material, whose routing default is review-apparatus. That epic's whole staged queue is parked under the PM-MCP supersession, so no plan there would act on it. It is owned here under this epic's "fix, not relay" directive.
- Scope-bloat guard: 4 deliverables.

## Folded inbox material (same act)

- `plan-12-tool-triage-014.md` (finding): deliverable 1
- `plan-12-tool-triage-029.md` (finding): deliverable 2
- `plan-12-tool-triage-030.md` (finding) items 1–2: deliverable 3; item 3: deliverable 4
- `plan-12-tool-triage-012.md` (candidate-lesson): deliverable 4

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-24-review-and-pr-record-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
