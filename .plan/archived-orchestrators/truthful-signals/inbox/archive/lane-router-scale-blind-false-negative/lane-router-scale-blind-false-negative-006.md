envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:53Z

component=plan-marshall:tools-integration-ci
category=bug
bundle=plan-marshall

# Required-bot evidence can go stale with NO remedy: there is no `pr reopen` verb, so the only refresh path is unreachable

Concrete, fully first-party sequence from PR #1068. `pr-agent` is a required reviewer.
Its review was captured at one HEAD; the branch then advanced. Every available means of
getting a fresh review failed, and the failures were each individually silent:

1. **`pr-agent` subscribes to `opened` / `reopened` / `ready_for_review` only.** A pushed
   HEAD is invisible to it. There is no push-triggered re-review, so an advancing branch
   simply carries the stale verdict forward.
2. **A `/review` comment drew zero response in 449s.** The manual trigger is not a
   reliable remedy — it produced no observable reaction at all, not even a refusal.
3. **`ci pr ready` returned `success` but was a NO-OP.** The PR was not a draft, so the
   verb had nothing to transition; it reported success for having done nothing. A
   success status here is indistinguishable from an actual ready-for-review transition
   that would have fired the bot's subscription.
4. **`tools-integration-ci` exposes `pr close` but NO `pr reopen`.** The one event the
   bot definitely subscribes to that we could still fire — `reopened` — has no verb in
   the sanctioned abstraction. Since direct `gh` use is a hard-rule violation, the
   refresh path does not exist for us at all.

The run proceeded with the gap recorded as finding `ea33a6` rather than blocking.

## Solution

Two distinct fixes, both at the tool layer (we own it):

- **Add a `pr reopen` verb to `tools-integration-ci`.** Without it, `pr close` is a
  one-way door and the `reopened` bot-subscription event is unreachable through the
  sanctioned abstraction. This is the actionable defect.
- **Make `ci pr ready` report a no-op as a no-op.** It must distinguish "transitioned
  from draft to ready" from "was already ready, nothing done". Returning bare `success`
  for both makes the verb useless as evidence that a subscription event was fired — the
  same could-not-look / looked-and-found-nothing collapse this epic keeps finding.

Until both land, treat "the required bot reviewed this PR" as **unverified whenever HEAD
has advanced since the review**, and record the gap explicitly rather than letting a
green finalize imply the bot saw the final diff.

## Impact

Tool-layer defect worth its own plan. Reinforces the standing rule that only
`ci pr comments --pr-number N` is evidence of participation — and adds that even that
evidence is HEAD-scoped, with no supported way to refresh it once the branch moves.
