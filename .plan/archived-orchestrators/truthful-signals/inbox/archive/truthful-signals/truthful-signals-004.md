envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-28T20:51:20Z

## Finding: `manage-lessons.py` mixes local time and UTC — lesson id prefix and retention math disagree on the date

### What was found

`marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py` uses two different clocks in one file:

- **Line 131** — `now = datetime.now().astimezone()` → **local time**. Feeds `date = now.strftime('%Y-%m-%d')` and `hour = now.strftime('%H')`, which compose the lesson-id prefix `{date}-{hour}` used for sequence allocation.
- **Lines 293, 411, 804, 1011, 1085** — `datetime.now(UTC)` → **UTC**. Feed the `removed_at` tombstone, the `today` values, and the retention/quiet cutoff comparisons.

Every other timestamp producer in the repo is UTC — `manage-status`, `manage-metrics`, `jsonl_store`, `manage-ci-artifacts`, `plan-retrospective/compile-report.py`, `generate_executor`, `_build_result`. Line 131 is the outlier.

### The failure window

In a UTC+N zone, between `00:00` and `N:00` local, the local date has already rolled over while UTC has not. On this machine (CEST, UTC+2) that is a **two-hour window each night, 00:00–02:00 local**, during which:

- a lesson filed gets id prefix `2026-07-29-00`, derived from local time
- the retention cutoff, the `removed_at` tombstone, and the `today` comparison all still resolve to `2026-07-28`

Consequences to check when actioning: sequence allocation scans for existing ids sharing the prefix, so a prefix computed on a different calendar day than the retention math can (a) collide against or (b) fail to see the ids its UTC-keyed siblings reserved. Retention arithmetic keyed off a date the id does not share also means an off-by-one-day age for lessons filed in that window. The exact reachable symptom was not reproduced — this is filed as an inconsistency with a demonstrated divergence window, not as a reproduced failure.

Note also the zone-dependence: the window's width equals the UTC offset, and it disappears entirely for UTC and negative-offset zones. A test written in CI (typically UTC) would never observe it.

### Why it belongs to this epic

Theme match — **confident-signal-hides-a-caveat**. A lesson id carries a date prefix that reads as authoritative provenance: "this lesson was filed on 2026-07-29." The retention subsystem simultaneously holds that the same lesson was filed on 2026-07-28. Both signals are emitted confidently, neither is labelled with its zone, and nothing in the id or the tombstone reveals that two different clocks produced them.

It is also a **zone-invisible-under-test** case, adjacent to the epic's population-derived-detector concern: correctness here depends on the runner's timezone, so a green CI run is not evidence the paths agree.

### Suggested disposition

Make line 131 UTC for consistency with the file's other five sites and with the repo-wide convention — subject to one check first: confirm the local-time choice was not deliberate (e.g. intended to give operators human-local lesson ids). If it was deliberate, the fix is the inverse — leave line 131 and label the id's zone — but the two must not stay silently divergent either way. A test that pins the behavior under a non-UTC `TZ` would make the window visible.

### Provenance

Surfaced while enumerating the repo's timestamp producers to explain a two-hour gap between assistant-reported times and system time. The root cause of that gap was UTC-stamped artifacts being quoted without their zone label — correct data, unlabelled. This finding is the one genuine inconsistency the enumeration turned up: not a labelling problem, but two clocks in one file.
