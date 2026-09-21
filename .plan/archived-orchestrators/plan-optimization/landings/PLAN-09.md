# Landing: PLAN-09 — merge-queue merge_group CI guard

- epic: plan-optimization / WS-03
- plan_marshall_plan_id: merge-queue-merge-group-guard
- pr: #935 (MERGED 2026-07-18, squash via GitHub merge queue)
- planning_lane: light (no DQ3 escalation)
- execution_profile: auto

## What shipped

**D1 — enable-time guard (code + tests).** `github_ops.py` gained a pure,
stdlib-only helper `_repo_has_merge_group_trigger(workflows_dir)` (PyYAML is
unavailable, so it is an anchored `re` scan of the top-level `on:` block covering
the three canonical GitHub-Actions forms — single string, flow sequence, block
mapping/sequence). A refuse-before-create guard in the
`MERGE_QUEUE_ELIGIBLE_UNCONFIGURED` branch of `cmd_repo_merge_queue_enable`
returns an actionable `make_error` (naming the bricks-main footgun and the
add-a-`merge_group:`-trigger remedy) instead of POSTing the ruleset when no
trigger exists. GitHub-only; fires only on the create branch, never the
`eligible_configured` reconcile branch. New focused test file
`test_github_ops_merge_group_guard.py`.

**D2 — contract-surface docs.** Reconciled steward `merge-queue-setup.md` (Step
MQ-2 now inspects the enable status instead of asserting success), plus
`tools-integration-ci` SKILL.md and `standards/pr-operations.md`.

## Design decision

The open (a)/(b) choice resolved to **(a) refuse at the enable handler** — the
`ci` scripts are non-interactive so (b) auto-add is structurally impossible in
the API layer; refuse-at-API protects every caller and is deterministically
testable.

## In-run review fix

Gemini surfaced a valid false-positive: the block-form scanner matched
`merge_group` on any indented line under `on:`, so a branch literally named
`merge_group` (`push: branches: [merge_group]`) falsely counted as a trigger —
which would let the queue be enabled on a repo with no real trigger, defeating
the guard. Fixed by tracking the `on:`-block direct-child indent and matching
only at that level; added `test_helper_ignores_merge_group_as_nested_branch_name`.
CodeRabbit and Sourcery both hit review rate limits (no review).

## Verification

- `module-tests plan-marshall` green (new suite + no regressions).
- `quality-gate plan-marshall` green (mypy + ruff).
- whole-tree plugin-doctor quality-gate clean (0 issues).
- CI `verify / verify` green on the merged HEAD; merged via merge queue
  (re-tested via `merge_group` on `gh-readonly-queue`).

## Notes / recurring gaps hit this run (not fixed by this plan)

- Lesson `2026-07-18-13-001` (light-lane does not persist `pr_title`) recurred —
  worked around by authoring the PR title manually at the 3-outline handshake.
- Lesson `2026-07-13-21-001` (Sourcery rate-limit notice stored as a pr-comment
  finding) recurred — triaged `taken_into_account`.
- Repeated harness stream-idle timeouts on dispatched execution-context agents
  forced phase-5 and phase-6 to be driven inline by the orchestrator; each
  dispatch still completed its on-disk work before the stream died.
