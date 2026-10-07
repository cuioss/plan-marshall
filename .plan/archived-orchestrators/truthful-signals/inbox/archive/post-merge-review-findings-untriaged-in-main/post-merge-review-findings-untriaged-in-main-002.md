envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:03Z

component=plan-marshall:workflow-integration-github
category=bug
created=2026-07-29
bundle=plan-marshall

# cmd_post_responses cross-delivered dispositions owned by other PRs

`cmd_post_responses` read the whole plan-scoped findings ledger with **no `pr_number` filter**, so
on a multi-PR plan it cross-delivered: 31 threadless dispositions owned by SIX other PRs were posted
as one batch onto PR #1036, while the verb returned `count_responded: 38` / `count_untransmitted: 0`
/ `status: success` — a fully green report for a partly-misdelivered action. The green signal hid the
misdelivery completely; nothing in the returned counts distinguished "delivered to the right PR" from
"delivered to a stranger's PR".

## Solution

Add a `pr_number` filter to the ledger read inside `cmd_post_responses` so only rows whose
`belongs_to_pr_*` matches the target PR are ever transmitted. Verified live post-fix: later finalize
cycles in the same plan responded to exactly the target PR's rows (5, then 8) and skipped all 38
foreign rows.

## Impact

Any plan whose findings ledger accumulates rows from more than one PR (a multi-PR plan, or a plan
that re-triages across finalize loop-backs) was at risk of the same cross-delivery before the fix.
The green outer status made this a silent-corruption class of defect — exactly the epic's
confident-signal-hides-a-caveat theme.
