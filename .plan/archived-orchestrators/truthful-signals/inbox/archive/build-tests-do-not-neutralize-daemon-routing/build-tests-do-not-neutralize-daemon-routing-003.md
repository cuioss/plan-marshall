envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:01:29Z

component=plan-marshall:build-server-client
category=bug

# A daemon-routed build false-greens any plan that tests the routing seam

The `marshalld` daemon child sets `MARSHALLD_JOB_ENV` in its process environment. That variable ambiently neutralizes daemon routing for **every test running in that process** — including the tests whose entire purpose is to exercise the routing decision.

Observed directly in this plan: a routed run of the plan's own suite reported **SUCCESS**, while the identical tree run with `--execution-mode in_process` failed **3 tests, then 4** after the population was widened. Every build in this plan had to be forced `in_process` for that reason.

The failure mode is not "the daemon is broken". The daemon works. The problem is that the build's *execution mode* silently changes the value of the signal the plan is trying to measure, and the green it produces is indistinguishable from a real green.

## Solution

- **When the deliverable under test is the routing seam itself (or anything that reads `MARSHALLD_JOB_ENV`), force `--execution-mode in_process` for every build in the plan.** A routed run is not evidence for that surface.
- More generally: before trusting a green, ask whether the build's execution mode could have neutralized the property under test. The build harness is part of the test environment, not outside it.
- The durable fix belongs at the tool layer: the routing-owning tests should neutralize `MARSHALLD_JOB_ENV` at fixture scope (which is what this plan shipped) so the two execution modes agree, rather than relying on the operator to remember to force `in_process`.

## Impact

Generalizes beyond daemon routing: **any ambient environment signal the build harness injects can invalidate the tests that read it, and the resulting false-green is silent.** Adjacent to the standing "never trust a routed build's outer status" rule, but a distinct mechanism — that rule is about the wrapper's status field lying; this is about the routed *environment* changing the test's answer, so the status field is telling the truth about a measurement that has been quietly voided.
