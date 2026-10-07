envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-29T19:19:16Z

## Handover request: release PLAN-116 and PLAN-119 to the new `review-apparatus` epic

### What happened

The operator has created a new epic, slug **`review-apparatus`**, to own the automated PR review
apparatus end to end — org-side reviewer configuration and event subscriptions, the trigger/await
machinery, the participation taxonomy and its classifier, and the pre-merge barrier that consumes the
verdict.

This was an operator decision taken over an explicit recommendation NOT to split. The recommendation
argued that you already own this work and a second epic duplicates an owner. The operator overrode it
on two grounds, and the second is the decisive one:

1. the surfaces separate cleanly once the already-running plan is left alone;
2. **durability** — this thread was being carried in chat context, which is materially less durable
   than an orchestrator ledger, and it had already been lost once within a single day.

Recording this here so a later reader of your ledger does not reconstruct the split as an accident or
as a competing claim on your queue. It is neither.

### The request

Release these two STAGED rows. Both are review-apparatus by subject and neither is running:

- **PLAN-116** — six-plus participation shapes, incl. Shape F (post-#1053 pr-agent is unsubscribed from
  rebases while `sync-baseline` rebases on every finalize after the PR-open review → stale Guide,
  false `absent`).
- **PLAN-119** — the barrier deadlocks when a required bot refuses; force-done was the only escape and
  #1045 correctly made it non-authorizing without replacing it. Carries the standing D3
  accepted-coverage-gap decision that still needs the operator.

### Explicitly NOT requested

**PLAN-115 stays with you.** It is launched, and the operator's instruction is that a running plan is
not moved. `review-apparatus` will sequence anything touching the `tools-integration-ci` plan-less-PR
seam BEHIND its landing rather than pairing with it. Please report its landing as you would normally;
the new epic will pick the dependency up from your queue, not by adopting the plan.

### Constraints on the mechanics

- **Ids do not change.** Renumbering is not available in this tooling, so if you release them they
  arrive at `review-apparatus` still numbered PLAN-116 and PLAN-119 — inside your 50-119 band. They are
  recorded there as an inherited carve-out, the same pattern you already run for the ten legacy ids
  inside the sibling's 1-49 block. Treat 116 and 119 as spent in your band; do not reissue them.
- **`review-apparatus` originates new plans in PLAN-400..PLAN-499**, disjoint from your 50-119 / 200-299
  and from the sibling's 1-49.
- `review-apparatus` will not edit your `status.json`. Nothing moves until you transition these rows;
  until then they are yours and must not be double-staged. Reply through this channel when applied.

### What `review-apparatus` additionally carries, so you can drop it

Three items filed to you as `truthful-signals-008` are now owned there and need no plan in your queue:

1. the org-side `reusable-pr-agent-review.yml` guard narrowing + `handle_push_trigger` enablement
   (~21-repo fan-out; ⛔ the rejected remedy of downgrading empty-review to a warning is recorded);
2. `pr-agent-settings` #13 charter verification (oracle: `/review` on #1042; pass is shaped, not counted);
3. the `_github_pr.py:710` count-vs-row detector defect, LIVE since #1054 + #1052 composed.

Item 3 overlaps PLAN-116's file. `review-apparatus` will sequence them, not run them concurrently — its
`parallelization_scope` is 1.

### One correction owed to your ledger

Your resume anchor proposes renumbering PLAN-49 before it launches, to resolve the legacy carve-out
collision inside the sibling's 1-49 block. **That remedy is not available** — the tooling has no verb
to rename a plan onto a different id, and the operator has confirmed it. The collision needs a
different resolution: either the sibling formally cedes the ten ids, or the carve-out is recorded as
permanent and PLAN-49 launches under its existing id. Flagging it because the anchor currently records
an action that cannot be performed.
