# PLAN-LB-67: The runbook lane merges on one handled review when a quota-limited reviewer cannot re-review the latest head

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for hand-off.
> Lives at `plans/PLAN-LB-67-standing-review-authorization.md` and is queued as one row file,
> `queue/PLAN-LB-67.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-18 by operator instruction. **Emit only after PLAN-LB-66 has landed**, because it
> amends the `plan-marshall:runbook-lane` skill that PLAN-LB-66 ships. **Each deliverable is its own
> outline deliverable, and each Done-when is its own success criterion. Do not merge them.**

## Objective

Runbook-lane runs keep stalling at the merge gate for the same reason. A required reviewer with a
review quota reviewed the PR once. Every finding was fixed and resolved. Then the quota refused
every re-review of the later heads, which only carried those fixes or a merge of `main`.

PLAN-LB-61, PLAN-LB-63 and PLAN-LB-52 all hit this. The run then either waits up to 10 × 90 minutes
and closes and reopens the PR, or merges on free text the lane does not accept.

The operator's rule (2026-10-18): **if there was at least one correct review by that reviewer, and
all its findings were handled, the run is authorized to merge.** The reason is the quota, which
exists besides any technical trigger problem.

The local runbook (`.plan/local/opencode/RUNBOOK.md` § 7 "Standing CodeRabbit authorization")
already carries the rule for runs started before PLAN-LB-66 lands. This plan moves it into the
product skill, in repository-neutral form.

## Deliverables

1. **The skill's merge gate carries the standing authorization, scoped to quota-limited reviewers.**
   - `runbook-lane/SKILL.md` § merge gate. For a required reviewer that the project marks as
     quota-limited (see D2), "reviewed the current head" may be replaced by all of these:
     1. **a qualifying review exists**: a formal review by that reviewer on one of this PR's heads,
        listed by `ci pr reviews` with its commit id. Rate-limit notices, summary comments and
        thread replies do not count;
     2. **every finding is handled**: each finding from that review and any later one is fixed in a
        pushed commit, or answered with a reason, and every one of that reviewer's threads is
        resolved;
     3. **it was re-triggered once after the last push**, and the refusal or silence is recorded;
     4. **every other gate condition holds on the current head**: every reviewer that is not
        quota-limited reviewed it, every comment is handled, the build gate is green, CI is green.
   - The reviewer quota policy (steps 1–3) applies only while no qualifying review exists.
   - The authorization never applies to a reviewer that is not quota-limited, and never to a PR
     without a qualifying review.
   - The landing report names, per quota-limited reviewer:
     - the head it reviewed;
     - the current head;
     - each finding and how it was handled.
   - The wording stays repository-neutral: PLAN-LB-66's forbidden-literal scan still passes.

   *Done when:* skill doc tests assert that:
   - the gate names the four conditions;
   - the quota policy is conditional on "no qualifying review";
   - the scope sentence excludes reviewers that are not quota-limited;
   - the landing-report section requires the reviewed head, the current head and the per-finding
     handling;
   - the forbidden-literal scan is clean.

   Each assertion fails against PLAN-LB-66's merged skill.

2. **`runbook_lane resolve` reports which required reviewers are quota-limited, from project
   configuration.**
   - Each required and optional bot in the resolve payload gains `quota_limited: true|false`.
   - It is read from the bot's standard (`automatic-review/standards/{bot}.md`, the source the verb
     already reads `trigger_comment` from) or from `marshal.json`. Choose at outline and record why.
   - `coderabbit` and `sourcery` declare `quota_limited: true`; `cuioss-review-bot` declares
     `false`.
   - A bot whose standard declares nothing resolves `false`: the authorization stays off by
     default.

   *Done when:* the resolve tests show:
   - `coderabbit` resolves `quota_limited: true`;
   - `cuioss-review-bot` resolves `false`;
   - a fixture bot standard with no declaration resolves `false`.

   All three fail against PLAN-LB-66's merged verb, which carries no such field.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: the skill's merge gate in the PLAN-LB-66 worktree requires "Every required reviewer
  reviewed the **current head**" (`runbook-lane/SKILL.md` ~L314), and its quota policy covers ANY
  required reviewer (~L294-303). Read at PLAN-LB-66 head `e585b314c`, before it merged; re-read
  at outline.
- OBSERVED: `runbook_lane resolve` returns the required and optional bots with `trigger_comment`
  and `escalated_trigger_comment` from `automatic-review/standards/{bot}.md` (PLAN-LB-66 D2).
- OBSERVED: PLAN-LB-63 merged after one CodeRabbit review on `5f6ea9940` with both findings
  resolved. Eight quota refusals followed (`landings/PLAN-LB-63.md`).
- OBSERVED: PLAN-LB-61's merged head had no CodeRabbit review (`landings/PLAN-LB-61.md`).
- OBSERVED: PLAN-LB-52 is blocked on the quota with **no** CodeRabbit review at all. The
  authorization does not apply to it, and that case must stay blocked.
- HYPOTHESIS: the bot standards carry a machine-readable header the verb parses (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` (D1)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`,
  `sourcery.md`, `cuioss-review-bot.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
  which documents the new declaration (verify-at-outline) (D2)
- HYPOTHESIS: `doc/developer/opencode.adoc`, the runbook-lane section (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: **PLAN-LB-66** (running), which ships `runbook-lane/` and the resolve verb.
- Overlaps with: none of the other running plans (PLAN-LB-45, PLAN-LB-52, PLAN-LB-65) on a file.
- Out of scope: the plan-marshall lane's own merge gate (`automatic-review` / phase-6). The
  operator scoped this rule to the runbook lane.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-67-standing-review-authorization.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
