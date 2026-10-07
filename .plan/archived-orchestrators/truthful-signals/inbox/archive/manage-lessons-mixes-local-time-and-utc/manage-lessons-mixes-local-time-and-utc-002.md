envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:38:26Z

component=plan-marshall:manage-lessons
category=anti-pattern
created=2026-07-29

# A timezone-faking test double must reproduce real projection semantics, not just strip tzinfo

`_FakeDatetime` in `test/plan-marshall/manage-lessons/_lessons_helpers.py` implemented `now(tz=None)` as a bare tzinfo strip on a fixed instant, instead of projecting that instant into local wall-clock time the way the real `datetime.now()` does. Any regression test written against this double to catch a local-vs-UTC divergence in `manage-lessons.py`'s id-prefix logic would pass identically whether the divergence bug was present or already fixed — the double could not express the very defect it was meant to help catch.

## Solution

Fix the fake first, then write the regression test, and confirm the test is red against the pre-fix production code before trusting it green against the fix. The freezer had to be corrected in this plan before the regression could ever be observed red.

## Impact

Any test double standing in for a timezone-, clock-, or locale-sensitive stdlib call is at risk of this "instrument can't see the defect it exists to detect" failure mode. When authoring or reviewing such a double, verify it reproduces the real semantics under the exact divergence the test is meant to catch (here: local-vs-UTC projection, not a tzinfo strip) — not merely a superficially similar signature.
