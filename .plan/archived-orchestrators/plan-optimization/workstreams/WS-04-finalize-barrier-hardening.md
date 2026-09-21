# WS-04: Finalize-Barrier Hardening

epic: plan-optimization

> Charter document for one workstream. Lives at `workstreams/WS-04-finalize-barrier-hardening.md`
> and tracked in the epic `status.json` `workstreams[]` field.

## Charter

Harden the phase-6 pre-merge comment-completeness barrier against self-inflicted churn. The barrier
exists to block a merge with unread bot comments — but it currently also flags comments the pipeline
itself authored (re-review trigger comments) and bot service-notices (rate-limit messages), which
drives `fail_into_loopback` cycling. Closes when the barrier no longer loops on pipeline-authored /
service-notice noise while still blocking on genuine unaddressed reviewer findings.

## Scope

- In scope: the github `fetch_findings` producer noise pre-filter (`github_pr.py` +
  `standards/comment-patterns.json`), self-authored re-review trigger-comment detection
  (`github_re_review` `bot_kind_for_author`), bot rate-limit service-notice classification.
- Out of scope: the merge-queue mechanism (WS-02 PLAN-06, shipped); the `ci pr safe-merge` verb;
  consumer-config integrity (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-10-review-barrier-noise-filter | ✅ shipped (PR #936) | Dropped pipeline-authored triggers + CodeRabbit rate-limit notices; dogfooded (0 loopback). Lesson 14-002 removed; residual 13-21-001 (bot-agnostic) open |
| PLAN-14-scoped-whole-tree-module-tests | staged | Extend PLAN-02's whole-tree-match discipline to the module-tests gate (lesson 22-001) |

## Sequencing and Surface Notes

- Startable now. Surface (`github_pr.py` + `comment-patterns.json` + `github_re_review.py`) is
  disjoint from in-flight PLAN-07 (manage-config), PLAN-08 (executor), and staged PLAN-09 (ci
  merge-queue enable). Runs concurrently with any of them.
- Relates to still-open lesson `2026-07-13-21-001` — fold that context in at outline.
