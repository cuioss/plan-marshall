envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:41Z

component=plan-marshall:automatic-review
category=bug
status=active

# review_rate_window_await cannot await an optional bot, so it cannot await the only substantive reviewer

## Context

On plan `apply-the-cloud-plan-lane-contract-amendments` the operator explicitly chose to wait for CodeRabbit rather than merge on participation-only coverage, and `review_rate_window_await` was set to `true` for the plan. It had no effect. The rate-window recovery is scoped to `required_bots` by an explicit rule, and the plan's configuration is `required_bots=cuioss-review-bot`, `optional_bots=coderabbit,sourcery` — so the knob could not fire for the bot the operator was waiting on, and coderabbit's refusal settled rather than escalated.

The scoping is inverted against what the bots actually do on this repository. `cuioss-review-bot` — the required one, the one the knob CAN await — publishes a canned intent-echo Guide body carrying no diff-derived observation; the corpus records it returning canned-empty on 42 of 44 reviews, and it did so again here, reporting "no major issues detected" on the same head where CodeRabbit filed two Major findings. `coderabbit` — the optional one the knob cannot await — produced all 3 actionable findings this plan received.

## Root cause

The recovery knob is scoped on the required/optional axis, which encodes *merge-gate authority*, while the thing being waited for is *substantive review output*. Those two properties are independent, and on this repository they point at different bots.

## Proposed action

Decouple the two. Either scope the rate-window recovery to any bot the operator explicitly asks to await (the knob names the bot, not the class), or make the required/optional split reflect which bots actually produce diff-derived findings — but do not leave a wait knob whose only reachable target is a bot that never finds anything. The `escalate_ask` path this run took is the workaround, and it costs an operator prompt every time.

## Evidence

- decision.log 2026-09-04T17:54:47Z — "iteration 2 rate-window recovery NOT ARMED for coderabbit: review_rate_window_await=true but coderabbit is in optional_bots, and the recovery is scoped to required_bots only (required_bots=cuioss-review-bot) - the knob cannot fire for this bot under the current classification"
- decision.log 2026-09-04T17:57:21Z — "Setting review_rate_window_await=true CANNOT await coderabbit: the recovery is scoped to required_bots by an explicit rule, and coderabbit is optional, so its refusal settles rather than escalates"
- decision.log 2026-09-04T17:46:48Z — "this repository's corpus records the required bot returning canned-empty on 42 of 44 reviews"
- finding `8dacd6` triage — "Noted for the record that it reports no major issues on the same head d08dc56e8 where CodeRabbit filed two Major findings"
