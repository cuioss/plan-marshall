envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:48Z

component=plan-marshall:tools-integration-ci
category=bug

# ci pr merge-queue reports enqueued:true from a branch-rule probe, never from the queue's own entries

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Filed in **API-Sheriff's** store, whose
repo does not own the `plan-marshall` bundle. Written here first and removed there second
(integrate-then-remove), `deployment-configurability` epic lessons intake 2026-09-11.

Origin id: `2026-09-06-01-001` (created 2026-09-06).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| `enqueued: true` with `enqueue_corroboration: merge_queue rule active on branch` although the PR never entered the queue | STILL-VALID | `_github_pr.py:2244-2251` returns `enqueued: True` with the corroboration string from the branch-rule probe (`github_ops.py:982`); queue entries are never read | PLAN-TRUTH-118 D4 (staged, `:54-62`, remedy: confirm via `pr auto-merge` or poll `pr view`); lesson `2026-09-06-16-001` (active, proposes `isInMergeQueue` / `mergeQueueEntry`) |

**What this message adds:** a second-repo sighting (API-Sheriff PR #255, a 30-minute wait on a PR that
was never queued) and the concrete read-back: after enqueuing, query
`repository.mergeQueue(branch:).entries` and require an entry whose `pullRequest.number` matches before
reporting `enqueued: true`; otherwise return `status: error` naming the attempted route. Fold into
PLAN-TRUTH-118 D4.

---

## Original lesson `2026-09-06-01-001` (verbatim)

id=2026-09-06-01-001
component=plan-marshall:tools-integration-ci
category=bug
status=active
created=2026-09-06

# ci pr merge-queue reports enqueued:true without corroborating that the PR entered the queue

## What happened

`ci pr merge-queue --pr-number 255` returned:

```
status: success
operation: pr_merge_queue
enqueued: true
enqueue_corroboration: merge_queue rule active on branch
```

The PR was **not** enqueued. It sat `OPEN` for 30 minutes with an empty merge
queue, `autoMergeRequest: null`, and `mergeStateStatus: CLEAN`. A direct query
confirmed the queue held no entries at all:

```
gh api graphql '{repository(...){mergeQueue(branch:"main"){entries(first:10){nodes{...}}}}}'
-> (empty)
```

Running `ci pr auto-merge --pr-number 255 --strategy squash` immediately after
put it in at `pos=1 AWAITING_CHECKS`, and it merged normally.

## Why it matters

The skill documents `pr merge-queue` under a "corroborate-not-report" contract —
the verb is supposed to confirm the platform actually performed the disposition
rather than assume it. The corroboration string it emits, `merge_queue rule
active on branch`, attests something different from what the `enqueued: true`
field claims: it confirms the **branch has a queue rule**, not that **this PR
entered the queue**. Those come apart exactly when the enqueue silently fails,
which is the only case the corroboration exists for.

The failure is silent and expensive. A finalize run that trusts the return value
waits out its entire `merge_queue_wait_budget_seconds` (1800s here) on a PR that
was never queued, then reports a timeout whose stated cause — a slow queue — is
wrong. Nothing in the payload distinguishes it from a genuinely slow merge.

Note that `pr auto-merge` emits the *same* `disposition_detail` string while
actually enqueuing, so the string cannot be used to tell the two apart either.

## How to fix

Corroborate against the queue itself, not the branch rule: after enqueuing, read
back `repository.mergeQueue(branch:).entries` and require an entry whose
`pullRequest.number` matches. Report `enqueued: true` only when that entry is
found; otherwise return `status: error` naming the attempted route, so the caller
retries or escalates instead of waiting out a budget.

Until that lands, a caller must verify membership itself after calling the verb
and must not treat `enqueued: true` as evidence.

## Workaround used

Verified queue membership directly after each enqueue attempt, and watched with a
detector that distinguishes "still queued" from "dropped out of the queue" so a
rejected entry surfaces instead of looking like a slow merge.
