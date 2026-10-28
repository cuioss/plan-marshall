# PLAN-LB-101: The barrier states and enforces the operator's review policy — an unreadable roster is an error, a stale required bot is asked again first, no remedy demotes a required bot, and a quota refusal is waited out

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-101-review-policy-barrier.md` and is queued as one row file, `queue/PLAN-LB-101.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the operator's instruction to implement the open HIGH item "the gate-truth half of PLAN-LB-55" (deferred by
> PLAN-LB-55 and PLAN-LB-93). This plan is the **review-policy half** (the rest of PLAN-LB-55 D4, which PLAN-LB-93 D6
> carried). The **merge-path half** is PLAN-LB-100; run that first, because both edit `branch-cleanup.md` and the
> `automatic-review` skill. Re-grounded against HEAD `3aad286fb` while staging: two bullets of the PLAN-LB-93 D6 text are
> narrower than it states, and the deliverables below are written from what the tree shows now (see Claim Labels).

## Objective

The operator's policy for a required reviewer is that it is mandatory, never demoted, and that a quota refusal is waited out.
The tree states that policy in `coderabbit.md` and in one structural prompt, but still contradicts it in several places: a
roster that cannot be read becomes an empty roster, shipped docs still tell the run to move a `declined` or `refused_hard`
required bot to `optional`, and the quota-wait loop is an opt-in knob that is off by default. This plan makes the policy hold
everywhere the tree acts on it.

## Deliverables

1. **An unreadable roster is an error, never an empty roster.**
   - When `automatic-review` cannot read its step params (`step-params get` failing, for example `execution.toon not found`), it
     returns an error and does not forward `--required-bots "" --optional-bots ""`.
   - The barrier's own roster read (`branch-cleanup.md` L843-859) follows the same rule.
   - A genuinely empty roster, read successfully, still means a vacuously satisfied quorum and is reported as such.

   *Done when:* tests: `step-params get` failing makes `automatic-review` return an error rather than an empty roster; a
   successfully read empty roster is distinguishable from an unreadable one in the returned record. Fails at HEAD, where an
   unreadable result defaults to EMPTY.

2. **A stale required bot is re-triggered before the barrier asks the operator, and the question says whether a trigger was attempted.**
   - A required bot on `participated_stale` gets its ordinary trigger before the barrier question is asked.
   - The question states whether a trigger was attempted and its outcome.
   - Behaviour on a loop-back re-entry (trigger B, which already triggers a stale required bot whatever `re_review_on_loopback` says) is unchanged.

   *Done when:* tests: a `participated_stale` required bot gets a trigger before the barrier question; the question text carries the
   trigger state; a bot that is not stale gets no extra trigger. Fails at HEAD for the first-pass barrier.

3. **No shipped document and no generated option moves a required bot to `optional_bots`.**
   - The barrier's option set contains no "make the required bot optional" and none is marked recommended unless the script marks it.
   - `branch-cleanup.md` L1041 (`declined`, `refused_hard`: "move it to `optional`") and L1222 ("move the bot to `optional_bots`"), and
     `automatic-review/SKILL.md` L1202 and L1260 (`declined`: "move the bot to `optional_bots`"), name a recorded merge authorization as
     the acceptance move instead.
   - A contract scanner fails when a shipped document under `marketplace/bundles/` offers demoting a required bot.

   *Done when:* the scanner passes on the changed tree and fails on a fixture document that offers the demotion; the four cited
   sites no longer carry it. The scanner distinguishes a required bot from an optional one that is already optional.

4. **A quota refusal on a required bot is waited out by default, through the existing wait verb.**
   - After a rate-window refusal a REQUIRED bot is re-triggered once its window has passed, through `merge_lock rate-window wait`
     (never a raw `sleep`), up to the configured cap, before any barrier question.
   - The policy in `automatic-review/standards/coderabbit.md` § "Operator review policy" becomes the loop's defaults: the window
     length, the number of windows, and close-and-reopen only when the bot has no review on record. Where the tree's defaults differ
     from the policy, the policy wins and the difference is recorded with the reason.
   - A refusal from a bot outside `required_bots` stays an ordinary settle that asks nothing.
   - `review_rate_window_await` stays a documented knob; its default and the way a project turns the loop off are the owner's design,
     decided at outline and recorded.

   *Done when:* tests: a refused required bot is re-triggered after its window and before the barrier asks; the loop stops at the
   cap and then escalates; an optional bot's refusal triggers no wait; the default configuration enters the loop. Fails at HEAD,
   where `review_rate_window_await` defaults to `false`.

Split guard: four deliverables, one theme (the review policy), two files of prose and one script family. Kept whole because each
deliverable is a different net for the same policy and none depends on another's code.

## Standing Constraints

- A required reviewer is mandatory and is never demoted to `optional_bots` on this plan or any other; the only ruling that covers its
  silence is a recorded HEAD-bound merge authorization.
- A CodeRabbit quota refusal is waited out. With at least one valid CodeRabbit review and the quota blocking the re-review, the
  standing authorization applies and moving on is correct, even when the last head changed logic; this plan must not add a question for it.
- Sonar is not enabled for this project and is ignored.
- Every new error path fails closed and says which input it could not read.

## Claim Labels

- OBSERVED: `automatic-review/SKILL.md` reads `required_bots` / `optional_bots` off the `step-params` snapshot and states "both default EMPTY" — `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` L1128 and L1186.
- OBSERVED: `branch-cleanup.md` L1041 names "move it to `optional`" for `declined` and, by reference, for `refused_hard`; L1222 says "move the bot to `optional_bots`"; `automatic-review/SKILL.md` L1202 and L1260 name the same remedy for `declined`.
- OBSERVED: `branch-cleanup.md` L1349 and L1355 already state that no demotion option exists on the structural-refusal path, and L1303 says a required bot is never demoted.
- OBSERVED: a required bot on `participated_stale` is already re-triggered on a loop-back re-entry whatever `re_review_on_loopback` says — `automatic-review/SKILL.md` L222 and L1260. This is narrower than the PLAN-LB-93 D6 text, which asked for the trigger before the first barrier question.
- OBSERVED: the quota loop exists and is opt-in — `review_rate_window_await` (default `false`) and `review_rate_window_timeout_seconds` (default `3600`), `automatic-review/SKILL.md` L48-51 and L479; `merge_lock.py` carries `rate-window {claim,check,wait,release}` (L112, L2437-2440).
- OBSERVED: no PLAN-LB-93 D6 bullet about the "Merge anyway" resume re-acquiring the mutex belongs here: `branch-cleanup.md` L1401 and L1437 already document the re-acquire and the re-validation (see PLAN-LB-100 Claim Labels).
- HYPOTHESIS: the policy numbers in `coderabbit.md` § "Operator review policy" (90-minute windows, up to ten) differ from the knob defaults (3600 s, attempt cap 6) — confirm at `automatic-review/standards/coderabbit.md` and `merge_lock.py` `--attempt-cap` (verify-at-outline).
- HYPOTHESIS: the barrier's option set is authored in prose at the `ask` sites rather than generated by a script — confirm at `branch-cleanup.md` L1349-1437 and decide whether D3 needs a generator or only the scanner (verify-at-outline).
- Verify-first clause (D2): decide whether the first-pass trigger belongs in the barrier or in the `automatic-review` step, and record why; the trigger must not run twice for one head.
- Verify-first clause (D4): the loop spans a long wait. Confirm that the wait is held by the main context (`phase-6-finalize` item 7a) and that the plan holds no merge mutex across it.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — roster read, trigger B, rate-window recovery (D1, D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — roster and state handling (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — the policy as the loop's source (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — barrier prompt, L1041 and L1222 (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — `rate-window` verbs (D4, only if the cap or defaults change)
- HYPOTHESIS: `test/plan-marshall/automatic-review/`, `test/plan-marshall/phase-6-finalize/`, `test/plan-marshall/manage-locks/` — barrier, roster and wait tests; the D3 scanner module is new (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-LB-100 landing first (it edits `branch-cleanup.md` and the same barrier text).
- Overlaps with: PLAN-LB-100 on `branch-cleanup.md`; parked PLAN-LB-46 on `automatic-review/`, `bot_registry.py` and `branch-cleanup.md` (it is parked, and its bot-removal deliverable does not overlap this plan's text).
- Adjacent to: `bot-participation-contract.md`, the taxonomy this plan reads but does not change.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-101-review-policy-barrier.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
