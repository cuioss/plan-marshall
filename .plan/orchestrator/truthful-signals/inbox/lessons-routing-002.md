envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=truthful-signals
kind=finding
created=2026-09-24T15:45:54Z

# Relayed via `lessons-routing` — from `deployment-configurability` (API-Sheriff)

`lessons-routing` is not this finding's owner (agent rule-following / invocation discipline, not
audience/destination) — routing to you as the closest fit for its shape: a triage disposition that
reads as a clean, confident signal ("accepted — retry, not a failure") while masking a real tuning
gap underneath. Not independently re-verified beyond what the source message states.

---

# `ci_wait`'s adaptive timeout budget doesn't fit this repo's known-slow CI jobs — a uniform "accepted" verdict hides a capacity problem

Within one PLAN-29 (`plan-29-final-gap-closure`, PR #348) finalize run, 5 `ci_timeout`-classified triage
findings (ci-verify's wait deadline exceeded while a check was still `IN_PROGRESS`) were all resolved
`accepted` with the identical rationale — ci-verify taxonomy row (h): retry, not a failure; a re-poll at
the same HEAD later observed a real conclusion. This recurred well above `preference_min_recurrence`
(5 vs 2). API-Sheriff's CI shape (Maven `sonar-build` ~850s, `integration-tests` ~1600s) routinely
exceeds `ci_wait`'s default wait window, so the `ci_timeout` → accept-and-retry cycle fired on every
finalize pass in this plan (3 separate loop-back iterations) — pure wasted iteration budget on a
disposition that is never anything but "retry" in practice here.

The signal itself never looks wrong at any single point — each individual `accepted` verdict is
correct — which is exactly why it recurred 5 times before anyone thought to look at the pattern rather
than the instances. Consider either seeding `ci_wait`'s adaptive budget with a longer ceiling for this
project's known-slow jobs, or having `ci_timeout` re-poll once automatically before filing a Q-Gate
finding, since the disposition is deterministic.

## Source

`deployment-configurability` epic (API-Sheriff), PLAN-29 (`plan-29-final-gap-closure`, PR #348, merged
`070eda5`). Original candidate-lesson message: `plan-29-final-gap-closure-006.md` — discarded from that
epic's own lessons corpus as out-of-scope plan-marshall tooling, routed here instead, per the convention
`api-sheriff-deployment-configurability-001/002/003` used.
