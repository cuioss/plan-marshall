envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=landing
created=2026-07-29T09:43:47Z

## PLAN-102 landing: post-merge review findings triaged and fixed

Shipped as PR #1045 (`fix(review-findings): triage and fix untriaged post-merge review findings`),
branch `feature/post-merge-review-findings-untriaged-in-main`.

### What shipped

- **D1** — derived the population of post-merge-landed / unresolved-thread review findings across
  recently-merged PRs (not just the two named sample PRs #1026/#1036) and gathered per-finding
  records via the CI abstraction.
- **D2** — verified each finding against current HEAD, applying the stale-diff-range ground-truth
  check; classified each still-valid / already-fixed / not-valid / needs-its-own-plan.
- **D3** — fixed the still-valid findings that were small and local; recorded the disposition of
  every gathered finding, including the ones deliberately left unfixed.

### Residue the epic should track (one candidate-lesson message per item below)

1. Fixed a cross-PR misdelivery defect in `cmd_post_responses` (no `pr_number` filter): it read the
   whole plan-scoped findings ledger and posted 31 threadless dispositions owned by six other PRs
   onto #1036 in one batch, while `count_responded`/`count_untransmitted`/`status` all reported
   fully green. Fixed in this plan and verified live: later finalize cycles responded to exactly the
   PR-1045 rows and skipped all foreign rows via `belongs_to_pr_*`.
2. Six findings were dispositioned "fixed" ("Routed to D3 for the edit") while their target files
   were never touched. Root cause: D3's outline-time file-scope bound (n=4) was supposed to be
   widened by D2's rebinding via the scope-deviation gate, but the rebinding was recorded as "fixed"
   instead of as a scope widening. Surfaced by lessons-housekeeping, not by any gate.
3. The declared D1 selection rule (post-merge-landed OR unresolved-thread) under-selected against
   the spec's own stated OBJECTIVE. Widening it added 7 findings AND exposed that PR #1032 satisfied
   the ORIGINAL rule and had still been missed outright.
4. pr-agent, the plan's only required bot, never reviewed the merged SHA despite two `/review`
   triggers and roughly 23 minutes of awaiting; the step was still marked done via the force-done
   escape hatch.
5. Doc/script drift traced to PR #1041: the loaded `automatic-review` and
   `workflow-integration-github` skill docs describe `--enabled-bots` / `--settled-bots` while the
   live scripts implement `--required-bots` / `--optional-bots` / `--participated-bots`. Two separate
   leaves in this plan hit the mismatch.
6. `execution.md` sequences "capture the 5-execute handshake" BEFORE the phase-5→6 transition, but
   the transition's own `worktree_dirty_at_boundary` recovery mandates an intervening settlement
   commit — so the capture is guaranteed stale on every plan that takes the recovery path (this plan
   did).

Signal-gate context (not independently recomputed by this dispatch, per dispatcher disclosure): all
three signal sources (pending Q-Gate findings, automated-review outcome, script-failure clusters)
were non-zero for this run.
