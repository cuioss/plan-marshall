# PLAN-03: Repair review currency and decide the required-bot await pair

epic: finalize-machinery
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-review-currency.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode +
Muse Spark 1.3): process compliance is mandatory, not advisory.

## Objective

Close the two open merge-gate holes from PR #1409 and settle the required-bot
interaction from #1407: the currency guard must compare the SHA the bot says it
reviewed instead of ordering timestamps, the issue-comment path must reach
head_sha_verified so current reviews stop reading as declined, Trigger-B must reach the
bot that is actually stale, and the coderabbit-required + review_rate_window_await pair
must be decided together — turning the await on, not demoting the bot.

## Deliverables

1. SHA-comparison currency guard: a force-push after a bot review no longer credits the
   stale review as current (lesson 2026-09-04-17-016).
2. Issue-comment path repair: head_sha_verified reachable on the issue_comment publish
   path so a bot that reviewed the merge candidate reads as approving, never as a
   signal to weaken the gate (lesson 2026-09-05-14-001).
3. Required-bot + await pair decided: review_rate_window_await turned on for the
   awaitable refusal class with CodeRabbit required; demotion back to optional
   explicitly rejected with rationale.
4. Trigger-B reach: the trigger selects the stale bot rather than structurally only the
   newest bot-authored finding's kind (lesson 2026-09-06-07-003), with a regression test
   per hole.

## Claim Labels

- OBSERVED: the currency guard orders timestamps instead of comparing the SHA the bot says it reviewed, so a force-push lets a stale review credit — read at corpus lesson `2026-09-04-17-016` § `currency guard`
- OBSERVED: head_sha_verified is unreachable on the issue_comment path, so a current review reads as declined — and on PR #1409 the mechanism advised weakening the gate for two bots that had reviewed — read at corpus lesson `2026-09-05-14-001` § `issue-comment path`
- OBSERVED: #1407 moved coderabbit into required_bots while review_rate_window_await is still false, and CodeRabbit refusals are the awaitable kind — read at `.plan/marshal.json` § `required_bots`
- OBSERVED: Trigger-B selects one bot (newest finding's kind) and cannot reach a different stale bot — read at corpus lesson `2026-09-06-07-003` § `trigger scope`
- OBSERVED: no production file under workflow-integration-github/scripts was touched by #1409, so both holes are open — read at `.plan/orchestrator/finalize-machinery/epic.md` § `transfer verification`
- HYPOTHESIS: comparing the bot-claimed SHA against the merge candidate closes the force-push hole without breaking the current-review path — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` § `currency check` (verify-at-outline)
- Verify-first clause: the consuming phase confirms both holes against the implementing github/automatic-review sources at HEAD before scoping; refutation loops back to re-scope. Re-grounding settles at cleanup via the verdict field.
- Re-grounding instruction: the launched plan treats each HYPOTHESIS above as verify-at-outline against the named file § symbol; cleanup re-grounds the claim labels against HEAD and stamps verdicts via corpus set-verdict.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — currency check
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_checks.py` — check-run review state
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_ci.py` — issue-comment publish path
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — review completeness and Trigger-B
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — required vs optional bot sets
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py` — gate delta decisions

## Dependencies and Sequencing

- Depends on: none (preferred after PLAN-01 conceptually, not a hard dependency)
- Overlaps with: PLAN-02 touches automatic-review SKILL.md while this plan touches automatic-review scripts — file-disjoint, may parallelize; sequence if either widens beyond declared files
- Adjacent to: .plan/marshal.json required_bots + review_rate_window_await config — read, and changed only for the await flag per the pair decision

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/finalize-machinery/plans/PLAN-03-review-currency.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
