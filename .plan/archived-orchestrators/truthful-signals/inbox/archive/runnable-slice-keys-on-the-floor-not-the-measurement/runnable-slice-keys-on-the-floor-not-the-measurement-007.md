envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:55:44Z

component=manage-run-config
category=improvement
created=2026-07-29

# A behavior-preserving default can be a vacuity trap for a new required distinction

`_compute_execution_tier_fields(stamp, measured)` needed `measured` to
distinguish "no measurement" from "measured and safe" — a distinction that did
not exist before this plan. Making `measured` default to `True` would have kept
two existing positional-call tests GREEN while silently pinning a code path
production no longer takes (the unmeasured fail-closed path would never be
exercised). Requiring the parameter (no default) made argument-count failure the
guard itself, and it caught exactly the 5 call sites it was designed to catch.

## Impact

When adding a new required distinction to an existing function via a new
parameter, prefer NO default over a behavior-preserving default — a
behavior-preserving default lets existing green tests mask an unexercised new
code path; a required parameter turns every un-updated call site into an
immediate, loud failure.
