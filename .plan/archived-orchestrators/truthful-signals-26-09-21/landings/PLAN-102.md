# Landing Analysis: PLAN-102 — Post-merge review findings are untriaged in main

epic: truthful-signals
workstream: WS-01
pr: 1045 — merged as `d714a14e3`, 2026-07-29 12:07:40 +0000

## Status

Merge verified against `origin/main`. ✅ **Verification debt CLEARED 2026-07-29** — the plan report
arrived after this record was first written. **3/3 deliverables shipped, 21/21 finalize steps, 6/6
phases recorded.**

| Deliverable | Verdict |
|---|---|
| D1 — enumerate post-merge and unresolved findings across the merged-PR window | shipped — **28 merged PRs examined → 38 findings gathered** |
| D2 — verify and classify every gathered finding against current main | shipped — **verified by SYMBOL**, per the standing rule |
| D3 — fix the small-and-local survivors and transmit every disposition | shipped — three test files closed vacuous guards, one standards doc lost a contradictory clause, `cmd_post_responses` gained the `pr_number` gate |

## ⭐ The fix proved itself mid-run — a controlled before/after

**Before**: `post_responses` batched **31 dispositions owned by six other PRs** onto #1036 while
reporting **`count_untransmitted: 0`**.
**After**: the same verb responded to exactly the **8** PR-1045 rows and skipped all **38** foreign
ones with `belongs_to_pr_*`.

⇒ A same-run, same-input demonstration — stronger than the regression alone, and the **second** time
this week a plan has produced one (PLAN-111 did the same with its cached-vs-worktree executor pair).

⚠ **Note what the pre-fix behaviour was**: cross-delivering 31 other PRs' dispositions **while
reporting zero untransmitted**. That is not a missing signal — it is a **confidently false** one, and
it was writing into other PRs' comment threads.

## Review coverage — the counter-example worth recording

**3 reviewers, 22 actionable comments across 2 rounds.** ⭐ **This is the epic's best review round of
the week**, against a backdrop where Sourcery is weekly-quota'd, CodeRabbit refuses terminally, and
pr-agent has no working `synchronize` trigger. **Coverage degradation is real but not uniform** — the
`n=4` green-check-lie record should be read alongside this, not as a claim that review never works.

## Post-merge PR revisit — clean

Merged 12:07:40Z; latest comment 11:56:10Z. **No post-merge arrivals.** Late-arrival recurrence stays
at **n=4**.

⚠ The plan's own D3 surface was declared *unknowable until D1 completes* and owed a disjointness
re-check against PLAN-111 and PLAN-112. **Whether that re-check happened is unverified** — part of
the same verification debt.

## Context at landing — three PRs merged in a 12-minute window, only ONE of them queued

| PR | Merge | In a queue? |
|---|---|---|
| #1051 `gate the merge on required-bot participation, not comment count` | `a96272a85` | ⛔ **no** |
| #1053 `Revert "review every pushed HEAD" — the runner skips synchronize` | `6be4c6081` 12:05:09Z | ⛔ **no** |
| **#1045 PLAN-102** | `d714a14e3` 12:07:40Z | ✅ yes |

⛔ **This sharpens the governance gap already recorded**: work is reaching `main` outside the epic
ledger faster than the ledger is tracking it. Two of the three landings in this window had **no
landing analysis, no post-merge revisit, and no residue drain.**

⭐ **#1051 is materially relevant to this epic and landed unqueued**: *"gate the merge on required-bot
participation, not comment count"* is the machinery fix for the **green-check lie** this epic has
recorded at n≥4. It should have been a tracked plan.

## ⛔ #1048 was REVERTED by #1053 — a recorded premise is now void

`fe130064f` (#1048, *"review every pushed HEAD so the primary bot's evidence is reliable"*) was
reverted 12:05:09Z. From the revert's own body:

> #1048 added `synchronize` to the `pull_request` trigger list on the assumption that delivering the
> event would drive `auto_review`. **It does not.** PR-Agent's runner gates that action behind two
> settings that **both default off** — `github_action_config.handle_push_trigger` (`false`) and
> `github_action_config.push_commands` (`[]`). **"The change was half a fix, and the missing half
> made things worse."**

⇒ **Consequences to carry:**

1. The epic Watch questioning whether #1048 covered job-failure recovery is **moot** — #1048 no
   longer exists on main.
2. ⭐ **pr-agent still does NOT auto-review a pushed HEAD.** The reliability premise behind making it
   the sole required bot is **weaker than when that decision was taken** — it fails to review on
   synchronize *by configuration*, not by outage.
3. **A rebase of any open PR onto current main picks up the REVERT**, not a pr-agent improvement.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1045; `landing`; `plan_marshall_plan_id`
- [x] post-merge revisit performed — clean
- [x] verification debt recorded (no plan report; D3 disjointness re-check unconfirmed)
- [x] #1048-revert consequences recorded; the dependent Watch marked moot
