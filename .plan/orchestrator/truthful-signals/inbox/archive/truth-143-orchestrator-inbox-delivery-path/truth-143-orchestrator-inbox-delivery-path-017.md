envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:17Z

# Candidate lesson: an idempotency check read an INCOMPLETE marker and reported success for work that may never have happened

## Signal source

PR #1539 CodeRabbit inline comment `c08c67` at `plan-orchestrator/standards/inbox-envelope.md:146`. Severity Minor by the bot's own rating; the triage upgraded it to a data-integrity defect and allocated TASK-020.

## Observation

`consume_message()` has two loser branches (a `FileNotFoundError` path and a same-inode `FileExistsError` path). Both passed a **single unretried** `_marked_consumed_at()` read into `_consume_success`.

The race: a loser that observes the winner's claim *before* the winner stamps the marker returns `already_consumed` with an **empty `consumed_at`**. If the winner then fails and releases the claim (`claim.unlink(missing_ok=True)`), the message was never consumed — but a caller has already been told it was. That contradicts the guarantee `inbox-envelope.md:146` states.

`_marked_consumed_at()` returns an empty value both when the marker is absent and when it is unreadable, so the two cases were indistinguishable at the call site.

## Corrective rule

1. **An idempotent-success path must observe a COMPLETE marker, not merely the absence of work to do.** "Someone else holds the claim" is not the same fact as "the work is done".
2. **Retry while the claim exists; error when the claim is released before a complete marker appears.** Releasing the claim without a marker is positive evidence of failure, and is the only signal that distinguishes a slow winner from a dead one.
3. **A sentinel that collapses "absent" and "unreadable" into one empty value destroys the caller's ability to make this distinction.** Return the states separately, or the retry logic cannot be written correctly at any call site.

## Generalisation

This is the same archetype as the epic's core theme on a concurrency surface: a confident success return (`already_consumed`) whose caveat (the marker was never actually observed complete) is not representable in the return shape. The remedy is the same — make the unmeasured state expressible rather than folding it into the success value.
