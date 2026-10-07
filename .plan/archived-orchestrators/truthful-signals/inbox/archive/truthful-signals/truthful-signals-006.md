envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-29T13:29:52Z

## Two review-detector shape defects — consolidated approach, so the epic carries one

### Status of this message

**Consolidates, does not replace, messages `-008` (detector blindness) and `-009` (the guard).** Those carry the raw evidence from the executing plan. This one adds a live consequence neither could see at the time, settles the remedy ordering, and rejects one candidate remedy with reasons — so the epic holds a single agreed approach instead of two compatible readings that a later reader has to reconcile under time pressure.

### The generalisation

Both defects are **shape problems, not duration problems**. Neither is fixed by a longer timeout, and both look like timeouts:

- One detector **counts rows when it should watch a row**.
- The other **asserts a precondition its own configuration denies**.

Both are a mechanism checked against the wrong observable.

### Defect A — `wait-for-comments` counts rows

`_github_pr.py:710`:

```python
def is_complete_fn(data: dict) -> bool:
    return int(data.get('unresolved', 0)) > baseline
```

A pure count comparison against a snapshot baseline. `pr-agent` re-reviews by **editing its one persistent Guide comment in place**, so the unresolved count never grows and the await can only ever time out. Observed: a ~23-minute await that completed nothing while pr-agent had in fact reviewed (guide `updated_at` 09:10:26Z).

**The fix already exists one file over.** `github_re_review.py:247-250` matches on the **later of `updated_at`/`created_at`**, written for exactly this shape. The registry also already declares the answer: `participation_requires_update: true` in `automatic-review/standards/pr-agent.md`. So this is two detectors where one was taught the lesson and the other was not — the fix is to bring `wait-for-comments` onto the same registry-driven semantics, not to invent new logic.

### Defect A is now LIVE and load-bearing — this is the new information

Two changes landed after `-008` was written:

- **#1054** (`25b0c91c9`) — a loop-back now posts each REQUIRED bot's trigger comment and awaits the result.
- **#1052** (`ef80c1c8d`) — `required_bots` narrowed to **`pr-agent` alone**.

Composed, every loop-back from now on: posts `/review` to pr-agent → awaits via `wait-for-comments` → the count never grows → burns the full `re_review_await_timeout_seconds` (600s) → hits `re_review_on_timeout: ask` and escalates to the operator. **Ten minutes and an operator prompt on every loop-back, even when pr-agent reviewed correctly.**

It does not deadlock — the `ask` fallback holds — but the detector is now blind to precisely the one bot it is the sole waiter for. This raises A from a historical curiosity to the highest-value fix in this cluster.

### Defect B — the empty-review guard asserts an unreachable precondition

The org workflow's fail-closed gate fails the job when `REVIEW_OUTPUT` is empty. When `synchronize` was subscribed without the runner being configured to act on it, the runner logged `Skipping action: synchronize`, produced nothing, and the guard failed the job in 39s (run `30449502213`). Nothing was in flight; no budget was near.

### Remedy ordering — decided, so the two readings do not compete

1. **Gate the guard on the events pr-agent actually reviews.** This is a **precondition for, not an alternative to,** enabling the trigger: even with `handle_push_trigger` and `push_commands` set, the runner returns without output on three legitimate paths (`github_action_runner.py:128-146`) — unchanged SHA, merge commit, bot commit. Enabling the trigger without narrowing the guard reproduces the same failure on a subset of pushes instead of all of them.
2. **Then configure pr-agent to review `synchronize`** (`github_action_config.handle_push_trigger` = true, `push_commands = ["/review"]`). This is what #1048 was trying to achieve and could not, because it changed only the caller's event subscription.

⛔ **Rejected: downgrading empty-review to a warning.** PR-Agent's runner **exits 0 when every model call fails**, and this guard is the only thing distinguishing "reviewed and found nothing" from "never reviewed at all". That ambiguity already cost a real misread on #1024, where a plan recorded zero bot review and took a merge decision on that basis while the reviewer had in fact cleared the diff. Making this signal quieter is the failure mode this epic is named after. Do not adopt it as a shortcut when 1 and 2 prove awkward.

### Ownership correction

The guard is **not** #1048's. It landed in the org reusable workflow at v0.15.5 (#214) and predates it; #1048 only added the trigger that made the guard's premise false. Consequence for scoping: **both remedies 1 and 2 are changes to `cuioss-organization/.github/workflows/reusable-pr-agent-review.yml`**, carrying the ~21-repo consumer release fan-out — not one-line edits to a caller. Defect A, by contrast, is a plan-marshall code change and is independently shippable.

### Acceptance

- **A:** an awaited re-review from a bot whose registry sets `participation_requires_update` completes on observed `updated_at` movement, not only on a count increase; covered by a test using pr-agent's in-place-edit shape; a loop-back with a correct pr-agent re-review no longer times out or escalates.
- **B:** with the trigger enabled, a `synchronize` push that the runner legitimately declines (unchanged SHA, merge commit, bot commit) does **not** fail the job, while a genuinely empty review from an event the runner *did* act on still does.

### Sequencing note

A is live, self-contained, and in this repository. B is dormant while `synchronize` stays unsubscribed after #1053, and costs an org release. **Do A first;** B only becomes urgent when re-enabling the push trigger is actually attempted.
