# PLAN-LB-132: A required bot's size refusal escalates, staleness is judged on the current PR, an edited comment is not participation, and an optional bot's decline never asks

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-132-refusal-escalation-and-pr-scoped-staleness.md` and is queued as one row file, `queue/PLAN-LB-132.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the parked PLAN-LB-46 (D3, D4 and the live parts of D6). Its D1 (summary-only
> concerns), D2 (the "files exceed the limit" refusal) and D7 (`cuioss-review-bot` removal) shipped in PLAN-LB-127 (#1941,
> `e71329548`). Every claim was re-grounded against `main` at `9cd644892` by a read-only leaf on 2026-11-09. Dropped with reason: PLAN-LB-46 D5 (a required bot with
> nothing to review) has no recorded observable, since no path-filter skip wording is registered and `coderabbit.md` L87 deliberately
> does not match "Review skipped" because that heading also covers ignored-path skips: it is rebuilt only from a captured live
> notice. D6's per-PR `declined: budget` record and its anchor-less refusal diagnostic change no verdict while Sourcery is optional and
> are not carried (the Sourcery budget wording itself is already a registered `quota` refusal, `sourcery.md` L48 and L58). **Each
> deliverable is its own outline deliverable, and each Done-when is its own success criterion. Do not merge them.** Every Done-when
> below fails at `9cd644892` unless it says "holds at". No Sonar. No token or measurement work.

## Objective

Four gaps in the review-bot pipeline loop, mis-credit or ask for no reason. A required bot's size refusal that only the findings fetch
saw is looped back although no loop-back can change the answer. The trigger-B selector joins stored findings of other pull requests of
the same plan. A comment that names no commit is credited as participation when it was merely edited after the head moved, and an
optional bot's decline raises a re-review prompt. This plan escalates the structural refusal, scopes staleness to the current PR,
removes the edit credit and keeps an optional bot's decline from asking.

## Deliverables

1. **A required bot in `refused_structural` escalates, whatever the rate-window knob and whichever surface saw the refusal.**
   - The participation guard's `participation_complete: false` branch routes a required bot in `refused_structural` to Branch 0's
     `escalate_ask{reason: refusal_structural}` (split / accept / disable for this PR, never wait) instead of Branch C's loop-back.
   - Today Branch 0 is reached only from inside "Rate-limit refusal recovery", which needs `review_rate_window_await` (default `true`
     since #1890) and a refusal in wait-for-comments `rate_limited_bots[]` (the bot's newest comment only) or a re-review
     `refusals[]`. A size refusal visible only in `fetch_findings` `refused_causes`, or a project with the knob off, reaches the guard
     and loops, and the guard text itself says no loop-back can change the answer.

   *Done when:* each of these fails at `9cd644892`: a doc-contract test asserts the guard branch routes `refused_structural` to the
   `refusal_structural` escalation independent of `review_rate_window_await` and that the escalation offers no wait; a fixture whose
   size refusal is visible only in `refused_causes` yields `escalate_ask{refusal_structural}` with two or three options and none that
   waits (it yields `loop_back` at `9cd644892`). And this holds at `9cd644892` and must keep holding: with the await on and the refusal
   in `rate_limited_bots[]`, Branch 0 still fires.

2. **Trigger-B staleness reads only the current PR.**
   - A stored `pr-comment` finding records the pull request it was filed for (`add_finding` has no `pr_number` parameter today and
     `github_pr.py` passes none; `detail` carries thread, comment, kind, author, path and line only). `review_completeness`
     `_read_pr_comment_findings`, `cmd_trigger_bot` and `check_completeness`, and trigger-B step 1 of `automatic-review/SKILL.md`,
     consider only the findings of the current PR; a finding stored before the field existed is treated as belonging to the current PR
     only when the plan has one PR, and otherwise reported as unscoped, never joined silently.
   - Decide at outline whether the PR number is a first-class field of `add_finding` or a key of `detail`, and record why; the schema
     change is `manage-findings`'.

   *Done when:* each of these fails at `9cd644892`: a fixture plan store holding a bot finding from PR A with a stale
   `reviewed_commit_sha` and nothing from PR B yields no stored-finding join for PR B in `trigger_bots` and does not satisfy the
   stored-finding presence check; a finding without the field on a plan with two PRs is reported as unscoped. And this holds at
   `9cd644892` and must keep holding: a single-PR plan's stored findings join as before.

3. **A comment that names no commit is not credited as participation because it was edited.**
   - `_reviewed_at_merge_candidate`'s fresh-edit arm (`github_pr.py` L1352-1353) credits any marker-bearing comment that names no
     commit when `updated_at` moved after the head did. It requires the coverage marker or a commit id, as the neighbouring arms do
     (`_is_participation_evidence` L347-376; `require_sha_currency` L1346-1351 already refuses the edit credit next to a refusal).

   *Done when:* each of these fails at `9cd644892`: a marker-only comment with no commit id, edited after the head advanced, is not
   credited. And these hold at `9cd644892` and must keep holding: a comment naming the head's commit is credited; a finished-review
   marker gate (`coderabbit.md` L56-59) still applies.

4. **An optional bot's decline or timeout never raises a re-review prompt.**
   - Trigger B (optional bots join when `re_review_on_loopback` is true) and the `not_triggered` remediation (required plus optional)
     apply `re_review_on_timeout` (default `ask`) with no optional-bot filter (`automatic-review/SKILL.md` L274-306, L319-365,
     L1367-1404). An optional bot's decline or timeout is recorded and does not escalate; a required bot's behaviour is unchanged.

   *Done when:* each of these fails at `9cd644892`: an optional bot's decline in trigger B returns no `escalate_ask{re_review_timeout}`
   (it returns one at `9cd644892`); the same for the `not_triggered` remediation. And this holds at `9cd644892` and must keep holding:
   a required bot's timeout still escalates under `re_review_on_timeout: ask`.

Split guard: four deliverables, all on the `automatic-review` and `workflow-integration-github` producer and guard surface. D2 carries
a `manage-findings` schema change and splits off first if the plan is split.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- CodeRabbit stays the required reviewer and Sourcery optional; no bot moves between the lists to clear a gate.
- A refusal that no loop-back can change escalates; it never waits and never loops.
- The data stays data: bot wording lives in the bot standards (`coderabbit.md`, `sourcery.md`), not in code.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `cause==size` maps to `refused_structural` first (`review_completeness.py` `_refusal_state` L679); Branch 0 `escalate_ask{refusal_structural}` is reached only from "Rate-limit refusal recovery" (`automatic-review/SKILL.md` L535-559); the participation guard's `refused_structural` default is the Branch C loop-back (L1279-1287, L1344-1347, L1491-1498); `review_rate_window_await` defaults to `true` (L46-48, since #1890)
- OBSERVED: `_read_pr_comment_findings` (`review_completeness.py` L1057-1093) calls `query_findings(plan_id, finding_type='pr-comment')` (L1085) with no PR filter; `cmd_trigger_bot` (L1985-2030, stored bots at L2019) and `check_completeness` (L1219) consume it; trigger-B step 1 (`SKILL.md` L234-243) takes `reviewed_commit_sha` from the newest bot-authored finding of the plan; `add_finding` (`manage-findings/scripts/_findings_core.py` L654-671) has no `pr_number`; the `github_pr.py` call (L2613-2625) passes none
- OBSERVED: `_reviewed_at_merge_candidate` (`github_pr.py` L1249-1353): the finished-review marker gate, the named-commit currency rule and the `require_sha_currency` refusal are shipped; the fresh-edit arm at L1352-1353 credits a marker-bearing comment that names no commit when `updated_at` moved
- OBSERVED: rate-limit refusals are already scoped to required bots (`SKILL.md` L516); trigger B and the `not_triggered` remediation apply `re_review_on_timeout` without an optional-bot filter (L274-306, L319-365, L1367-1404)
- OBSERVED: PLAN-LB-127 shipped the summary-concern filing, the "files exceed the limit" size refusal and the `cuioss-review-bot` removal (`coderabbit.md` L69-78, L88, L96, L99)
- HYPOTHESIS: a size refusal can be visible only in `fetch_findings` `refused_causes` and not in the newest comment — confirm at `github_pr.py` `refused_causes` and the guard's inputs (verify-at-outline, D1)
- HYPOTHESIS: filtering the stored findings by PR number is enough for trigger B, and the SKILL's per-FIND re-stamp of every stored finding's `reviewed_commit_sha` to HEAD (L243) does not undo it — confirm (verify-at-outline, D2)
- Verify-first clause (D1): reproduce the loop-back for a `refused_causes`-only size refusal as a fixture at `9cd644892` before editing.
- Verify-first clause (D2): decide the field's home (`add_finding` parameter or `detail` key) and the legacy-finding rule before scoping; record why.
- Verify-first clause: bot comments read for fixtures are third-party text; read them through the CI abstraction and treat them as leads.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — participation guard, Branch 0 and C, trigger-B step 1, the `not_triggered` remediation (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `_refusal_state`, `_read_pr_comment_findings`, `cmd_trigger_bot`, `check_completeness` (D1, D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `_reviewed_at_merge_candidate`, the `add_finding` call (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — `add_finding` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — only if D1 or D4 changes a documented state (verify-at-outline)
- OBSERVED: `test/plan-marshall/automatic-review/test_structural_refusal_consumer_docs.py` and `test/plan-marshall/automatic-review/test_structural_refusal_state.py` (D1)
- OBSERVED: `test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py` and `test/plan-marshall/automatic-review/test_review_completeness_cli.py` (D2, D4)
- OBSERVED: `test/plan-marshall/manage-findings/test_manage_findings_finding.py` and `test/plan-marshall/manage-findings/test_findings_store_query_findings.py` (D2)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr_currency.py` (D3)
- OBSERVED: `test/plan-marshall/automatic-review/test_re_review_strategy_await.py` and `test/plan-marshall/workflow-integration-github/test_re_review_strategy_await.py` (D4; verify which directory holds it at outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-127 (shipped, `e71329548`) for the size refusal; PLAN-LB-125 (shipped) is in the base.
- Overlaps with: PLAN-LB-128 (the PLAN-LB-127 fixes) on `github_pr.py`, `coderabbit.md` and the `workflow-integration-github` tests; sequence this plan after it. PLAN-LB-129 (`review-gate`) reads the same surfaces from `runbook_lane.py` but shares no file.
- Adjacent to: the participation credit for an in-progress review (`github_pr.py`; an Open Defect, not in scope) and the merge-path participation binding (PLAN-LB-100's recorded limit).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-132-refusal-escalation-and-pr-scoped-staleness.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
