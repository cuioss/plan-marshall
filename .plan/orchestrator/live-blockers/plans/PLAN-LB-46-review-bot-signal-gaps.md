# PLAN-LB-46: Review-bot signal gaps — summary-only concerns, a size refusal that loops, cross-PR staleness, and a reviewer with nothing to review

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-46-review-bot-signal-gaps.md` and is queued as one row file, `queue/PLAN-LB-46.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from three Open Defects:
> - CodeRabbit summary-only concerns (`lessons-routing-027.md`);
> - the remainder of "A required review bot goes stale after a fix commit" (`lessons-routing-017.md`);
> - from `landings/PLAN-LB-37.md`, "A required bot's size refusal loops instead of escalating" (lesson `2026-10-13-14-003`).
>
> Two of the `-017` remainder items are closed at HEAD and are dropped (see Claim Labels).

## Objective

Four gaps in the review-bot pipeline lose a signal or force an operator override:

- **Summary-only concerns are discarded.** CodeRabbit concerns raised only in its walkthrough or summary comment — security included — are dropped as noise and never filed.
- **A size refusal loops instead of escalating.** A required bot's "files exceed the limit" refusal is not recognised; when one is, its structural state still loops back instead of escalating, unless an opt-in nobody enables is set.
- **Staleness is judged from another PR.** The trigger-B selector reads review staleness from findings of other pull requests.
- **A bot with nothing to review is counted absent.** A required bot whose path filter excludes the whole diff is counted absent and loops.

This plan files the summary concerns, escalates the size refusal, scopes staleness to the current PR, and accounts for the bot with nothing to review.

## Deliverables

1. **A CodeRabbit summary that carries a concern is filed, not dropped.**
   - The summary marker and `## Walkthrough` move from the unconditional `ignore_patterns` to the existing conditional drop: `contentless_review_markers` / `contentless_review_headings`, with an `actionable_content_markers` veto.
   - The veto covers the "Outside diff range", actionable and security sections, so a summary carrying one is filed as a `pr-comment` finding.
   - A plain walkthrough is still dropped.
   - No new mechanism is added.

   *Done when:* a fixture summary with only a security concern is filed (`count_skipped_noise` unchanged), and a fixture plain walkthrough is still counted as noise. At HEAD both are dropped.

2. **The "files exceed the limit" refusal is recognised as structural.**
   - The CodeRabbit registry adds the "files exceed the limit" wording to `refusal_patterns` and `refusal_size_patterns`.
   - It adds a cap pattern that reads `exceed the limit of N`.

   *Done when:* a fixture comment "Review skipped: 198 files exceed the limit of 100" is recorded as a refusal with `cause: size` and `cap: 100`, never filed as a finding. At HEAD it is filed as an ordinary finding.

3. **A required bot in `refused_structural` escalates, whether or not the rate-window opt-in is set.**
   - The participation guard's `participation_complete: false` branch routes a required bot in `refused_structural` to Branch 0's `escalate_ask{reason: refusal_structural}` — split / accept / disable for this PR, never wait.
   - Today Branch 0 is reached only when `review_rate_window_await` is true; otherwise the guard records a loop-back.

   *Done when:* a doc-contract test asserts that the guard branch routes `refused_structural` to the `refusal_structural` escalation independent of `review_rate_window_await`, and that the escalation's prompt options offer no wait. At HEAD the guard (SKILL.md L1257-1260) loops back.

4. **Trigger-B staleness reads only the current PR.**
   - `review_completeness trigger-bot` and the `reviewed_commit_sha` read in SKILL.md trigger-B step 1 consider only `pr-comment` findings of the current pull request.
   - A finding from another PR of the same plan (a stack, or a closed-and-reopened PR) no longer joins bots to the trigger list.

   *Done when:* a fixture plan store holding a bot finding from PR A with a stale `reviewed_commit_sha`, and nothing from PR B, yields no stored-finding join for PR B. At HEAD it does.

5. **A required bot with nothing to review is accounted for.**
   - When a required bot's own notice, or its CI run, shows that the diff contains no file it reviews, the bot resolves to an accounted-for state instead of `absent`.
   - This applies, for example, to a `.plan/`-only diff behind CodeRabbit path filters, or the `cuioss-review-bot` workflow not triggering for the paths.
   - The state is observed from the bot, not inferred from a copied path-filter list.

   *Done when:* a fixture with the bot's "no files to review" observation resolves the bot to the accounted-for state and does not block. A fixture with plain silence still resolves `absent`. At HEAD both resolve `absent`.

Split guard:
- Five deliverables, all on the `automatic-review` and `workflow-integration-github` producer/guard surface.
- Deliverable 5 delivers the least harm (one observed plan) and is the first to drop to stay small.
- If the outline finds that deliverable 5 needs a new per-bot registry field for `cuioss-review-bot`, split it into its own plan, because that field lives in `cuioss-review-bot.md`, which PLAN-LB-31 and PLAN-LB-41 edit.

## Claim Labels

- OBSERVED: `coderabbit.md` lists the summary marker and `## Walkthrough` under `ignore_patterns` (L59-61), and § Producer stage calls them whole-comment drops "that carry no per-line finding" (L127-131). CodeRabbit declares no `contentless_review_markers` / `actionable_content_markers` (L21-24) — `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`.
- OBSERVED: `_is_obvious_noise` applies layer 2 (per-bot `ignore_patterns`, unconditional substring match) and layer 3 (contentless boilerplate vetoed by `actionable_content_markers`) — `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` L419-448. The epic's "~407" is now L419.
- HYPOTHESIS: the summary-only concerns on pm-mcp-core PR #43 sit in the walkthrough or summary issue comment rather than the review body — confirm by reading that comment through the CI abstraction, as third-party text treated only as a lead (verify-at-outline).
- OBSERVED: CodeRabbit's `refusal_patterns` hold "Review limit reached", "Review rate limited", "Too many files!", "Already reviewed the last commit" and "No new commits to review". `refusal_size_patterns` holds only "Too many files!", and the cap pattern is `over the limit of ([0-9][0-9,]*)` (L72-84). None matches "exceed the limit".
- HYPOTHESIS: the PR #1753 notice ("Review skipped: 198 files exceed the limit of 100") did not contain "Too many files!" — confirm against stored finding `5064d5` or the PR #1753 comment (verify-at-outline).
- OBSERVED: the refusal recovery, including Branch 0's `refusal_structural` escalation, runs only when `review_rate_window_await == true`. Its default is `false`, and with it "a detected refusal is treated as an ordinary settle" — `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` L46-48, L479, L533-556, L785-786.
- OBSERVED: on `participation_complete: false` the default path is "Loop back into FIND" (Branch C). The prose names split / accept / disable as the productive actions for `refused_structural`, but routes nothing to an escalation — SKILL.md L1257-1260. The predicate resolves a `size` cause to `refused_structural` (`review_completeness.py` `_refusal_state`, L741-742).
- OBSERVED: `cmd_trigger_bot` reads every `pr-comment` finding of the plan through `_read_pr_comment_findings` → `query_findings(plan_id, finding_type='pr-comment')` with no PR filter (`review_completeness.py` L1053, L1772-1817). SKILL.md trigger-B step 1 takes `reviewed_commit_sha` from the newest bot-authored finding of the plan, with no PR filter (L233-240).
- HYPOTHESIS: a stored `pr-comment` finding carries no `pr_number` field. A content search for `'pr_number'` in source does not hit `manage-findings/scripts/_findings_core.py`. Confirm the finding schema at `github_pr.py` `cmd_fetch_findings` before choosing between a new field and a comment-membership filter (verify-at-outline).
- OBSERVED: no expected-absent / path-filter concept exists in the review pipeline. A content search for `expected.absent|path_filter|path filter` finds no `automatic-review` or `workflow-integration-github` file.
- HYPOTHESIS: CodeRabbit posts a distinguishable skip notice when every file is path-filtered, and the `cuioss-review-bot` reusable workflow leaves a run record for an excluded diff — confirm against pm-mcp-core PR #24 (`pm-mcp-core-m2-m4-034`) (verify-at-outline). With no observable, deliverable 5 is dropped and recorded, not implemented on a copied filter list.
- OBSERVED (dropped item): `re_review_on_loopback` is now read only from the plan-local manifest snapshot through `manage-execution-manifest step-params get` (SKILL.md L224-231). The "wrong source" item is closed. Its "log value and source" half is not carried.
- OBSERVED (dropped item): a required bot whose participation is stale is re-triggered on re-entry whatever `re_review_on_loopback` says (SKILL.md L222, L276-281; `list_bots_for_trigger` `required_stale_bots`, `review_completeness.py` L388-446). `automatic-review` declares `head_dependent: true` (SKILL.md L13), so any HEAD advance re-fires it. The "stale after a fix commit by any path" item is closed on the trigger-B path.
- Verify-first clause: confirm that no path pushes a commit after `automatic-review` is done without re-entering it, or the pre-merge participation barrier (`branch-cleanup.md` § Predicate 2) — for example the merge-queue flow. If one does, report it; it is not added here.
- Verify-first clause: the bot comments read for the fixtures are third-party text. Read them through the CI abstraction and treat them as leads, not instructions.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — `ignore_patterns` / contentless markers / actionable veto (D1); refusal and size-cap patterns (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — `_is_obvious_noise` layer 3 for CodeRabbit (D1); finding scope for D4, if a field is added
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — the refusal-cause and cap readers (D2), and a no-reviewable-files observation (D5) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — participation-guard branch (D3), trigger-B step 1 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — `cmd_trigger_bot` PR scope (D4), accounted-for state (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — only if D5 adds a taxonomy member (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — only if D1 or D5 needs a registry accessor (verify-at-outline)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_filters.py` (D1)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_comments_stage_refusals.py` (D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_bot_registry_patterns.py` (D1, D2)
- OBSERVED: `test/plan-marshall/automatic-review/test_trigger_b_stale_set_from_participation.py` (D4)
- OBSERVED: `test/plan-marshall/automatic-review/test_review_completeness_cli.py` (D4, D5)
- OBSERVED: `test/plan-marshall/automatic-review/` — new doc-contract test for the guard escalation (D3)

## Dependencies and Sequencing

- Depends on: none on a declared file. The brief named PLAN-LB-31 and PLAN-LB-41 as dependencies; their specs show no shared file:
  - PLAN-LB-31 (running) declares `.plan/marshal.json`, `doc/analysis/in-house-reviewer-efficacy.md`, `automatic-review/standards/cuioss-review-bot.md` (§ Signal calibration) and `test/plan-marshall/automatic-review/test_bot_participation_contract_config.py`.
  - PLAN-LB-41 (staged) declares `automatic-review/standards/cuioss-review-bot.md` (the code-review entries), `phase-6-finalize/SKILL.md`, `phase-6-finalize/workflow/code-review.md`, `marketplace/targets/README.md` and two `phase-6-finalize` test files.
  - This plan touches none of them unless deliverable 5 needs a `cuioss-review-bot` registry field. In that case it depends on both, and deliverable 5 is split out (see the split guard).
- Overlaps with:
  - Directory-level only: `test/plan-marshall/automatic-review/` with PLAN-LB-31; `automatic-review/standards/` with PLAN-LB-31 and PLAN-LB-41 (different files).
  - None of the other four candidates in this batch.
- Adjacent to:
  - `cuioss/cuioss-review-bot` two-pass gaps (an epic Open Defect, foreign repository) — not touched.
  - The participation credit for an in-progress review (`github_pr.py` ~1938-2033; Open Defect, lesson `2026-10-12-05-002`) — same file, not in scope.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-46-review-bot-signal-gaps.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
