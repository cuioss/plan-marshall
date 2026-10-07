envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=landing
created=2026-08-08T20:41:13Z

# Landing: PLAN absent-names-two-states-with-opposite-remedies

**PR #1118 — merged via merge queue.** Plan spec: `plans/PLAN-PR-*-absent-names-two-states-with-opposite-remedies.md` (review-apparatus).

## What shipped

The bot-participation taxonomy grew from five to seven members. The two new members are `participated_stale` and `not_triggered`, and the point of the change is that they are two states an earlier apparatus collapsed into `absent` even though their remedies are opposite: a stale review needs a re-review trigger against the new HEAD, an untriggered bot needs the trigger event to be generated at all, and `absent` needs escalation. Both new members block exactly as `absent` does — no merge verdict was softened.

Surfaces touched: `automatic-review` (SKILL.md, `review_completeness.py`, `standards/bot-participation-contract.md`), `phase-6-finalize` (`standards/branch-cleanup.md`, `workflow/create-pr.md`), `tools-integration-ci` (`ci_base.py` + four standards docs), `workflow-integration-github` (`github_ops.py`, `github_pr.py`, `_github_checks.py`, SKILL.md), `workflow-integration-gitlab`, `workflow-pr-doctor`, `manage-config`, `marshall-steward`, plus eight test modules and `test/_shared/_bot_flag_derivation.py`.

New provider observable: `ci checks pull-request-runs` — does any `pull_request`-event workflow run exist for THIS PR. It is the `not_triggered` detector. Its `None`-vs-`[]` discriminator is load-bearing: a failed fetch must not report "no run exists" on evidence nobody gathered.

## The plan's own new member fired on the plan's own PR

`participated_stale` is not a hypothetical. A pre-merge rebase staled pr-agent's review, the barrier blocked on `participated_stale`, and the loop-back produced CodeRabbit's review — 8 actionable comments including one Major. Those became 9 fix tasks (commit `851e5396b`), then 5 more doc/test fixes at the next self-review pass (`a5749b0d2`). Without the new member the barrier would have read that state as satisfied and merged before CodeRabbit ever looked.

The Major was the plan's own thesis violated at a call site the plan itself added: an unreadable `pull-request-runs` return fell through to "a run exists" instead of UNKNOWN — see the candidate-lesson message on that record.

## How the run ended — participation proven, review quality NOT

The pre-merge barrier passed at HEAD `a5749b0d2` with `participation_complete=true` and 0 pending pr-comment findings, but the quorum rested on `pr-agent=participated_but_empty` (a contentless "no major issues" guide). CodeRabbit was `refused_awaitable` (will not re-review already-reviewed commits) and Sourcery `refused_hard` (diff over the 150000-char limit). **Commits `851e5396b` and `a5749b0d2` carry no bot review content at all.** The fixes made in response to the review were themselves never reviewed. This is recorded verbatim as a `[VERIFY]` WARNING in the work log at 19:53:48Z and rides as its own candidate-lesson message.

## Standing findings left open on the epic's surface

Both are pending Q-Gate findings on this plan and both live in `review-apparatus` territory:

- `b423d3` — `review_completeness` list flags disagree on bot-token form and mis-parse silently. Can manufacture a false merge block.
- `911e3e` — the refusal pre-filter let one refusal body through as a `pr-comment` finding while filtering three siblings from the same bot.

Each has its own candidate-lesson message.

## Related, not owned here

`plan-retrospective` already recorded lessons `2026-08-08-20-001` through `-004` (retrospective hard-coded populations, `manage-lessons` YAML-frontmatter parse failure, `manage-logging read --phase` silently ignored, `record-metrics` ordering) and folded one finding into a sibling plan. They are NOT duplicated in this epic's inbox.

Out of scope by explicit non-goal: Mode 5 (partial — HEAD 1 reviewed, HEAD 2 refused) is owned by PLAN-PR-013.

## Housekeeping owed

This session loaded its skill bodies from plugin-cache `0.1.1304`, which the finalize sync then orphan-marked; `0.1.1326` is the live version. A full restart is owed before the new bodies are seated, and `marshal.json` is separately stale at `1304` and needs `/marshall-steward`.
