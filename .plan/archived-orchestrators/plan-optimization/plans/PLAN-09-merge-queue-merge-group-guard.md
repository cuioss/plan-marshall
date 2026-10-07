# PLAN-09: merge-queue merge_group CI guard (bricks-main footgun)

epic: plan-optimization
workstream: WS-03

> Staged plan spec. Consumer-surfaced (cui-open-rewrite, PR #106 stalled) + **INDEPENDENTLY VERIFIED
> against upstream source by the orchestrator, 2026-07-18** — confirmed defect. Re-ground citations
> at outline.

## Objective

Stop the marshall-steward wizard from enabling a platform merge queue that will brick `main`. GitHub's
merge queue validates entries by running required status checks on temporary `gh-readonly-queue/*`
refs via `merge_group` events. If no repo workflow triggers on `merge_group`, the required checks
never run, every queued PR waits out `check_response_timeout_minutes`, and `main` becomes unmergeable
(direct merge is also blocked because the queue rule is required). The wizard currently enables the
queue and makes it a required rule WITHOUT verifying a `merge_group` CI trigger exists.

## Deliverables

### D1 — verify a `merge_group` CI trigger before/at merge-queue enable

**Verified (orchestrator, 2026-07-18):** `merge_group` appears NOWHERE in `marshall-steward` or
`tools-integration-ci` (grep exit 1); `merge-queue-setup.md` (Step MQ-2) has no `merge_group` /
`gh-readonly-queue` awareness. On an `eligible_unconfigured` probe the wizard enables the queue +
makes it a required rule with no CI-trigger check.

**Fix (confirm the (a)/(b) choice at outline — reporter offered both):** before enabling (or
immediately after), scan `.github/workflows/*.{yml,yaml}` for a `merge_group:` trigger. If none:
either **(a)** refuse with an actionable message ("no workflow triggers on merge_group; add it before
enabling the queue, or the queue will block all merges"), or **(b)** prompt to auto-add the trigger.
**At minimum the wizard MUST warn** — silently enabling a queue with no `merge_group` CI is a footgun
that bricks merges to the default branch. **Acceptance:** enabling the queue on a repo whose workflows
only trigger on push/pull_request produces a refusal or explicit warning (per the chosen option), not
a silent enable; a repo that already has a `merge_group` trigger enables cleanly.

## Out of scope / do NOT expand

- The `ci pr safe-merge` verb / stuck-state handling — that is the in-flight PLAN-06. This plan is the
  ENABLE-time provisioning guard, not the merge mechanism.

## Expected Surface

- `marshall-steward/references/merge-queue-setup.md` (Step MQ-2)
- `tools-integration-ci` `ci repo merge-queue enable` path (`ci_base.py` / repo-merge-queue) + possibly a `.github/workflows` scan helper
- tests: enable-with-no-merge_group-trigger → warn/refuse; enable-with-trigger → clean

## Dependencies and Sequencing

- Depends on: none.
- **Overlaps with in-flight PLAN-06 (ci-pr-safe-merge):** BOTH touch the `tools-integration-ci`
  merge-queue surface (PLAN-06 = `ci pr safe-merge` verb + branch-cleanup; PLAN-09 = `ci repo
  merge-queue enable` guard). Same GROUP → **sequence PLAN-09 after PLAN-06 lands, or accept a rebase**
  on the ci merge-queue scripts. Disjoint from PLAN-07 (manage-config) and PLAN-08 (executor/provisioning).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-09-merge-queue-merge-group-guard.md"
```

## Status Trail

- plan_marshall_plan_id: merge-queue-merge-group-guard
- pr: #935 (MERGED 2026-07-18, squash via merge queue)
- landing: landings/PLAN-09.md
- outcome: SHIPPED. D1 refuse-at-API guard (stdlib `_repo_has_merge_group_trigger`
  anchored to the `on:` block's direct children) + refuse-before-create wiring in
  `github_ops.cmd_repo_merge_queue_enable` `MERGE_QUEUE_ELIGIBLE_UNCONFIGURED`
  branch; D2 reconciled steward MQ-2 + pr-operations.md + tools-integration-ci
  SKILL.md. In-run review FIX (gemini): block-form scanner false-positive on a
  nested branch named `merge_group` — added direct-child-indent anchoring +
  regression test. (a)/(b) resolved to (a) refuse.
