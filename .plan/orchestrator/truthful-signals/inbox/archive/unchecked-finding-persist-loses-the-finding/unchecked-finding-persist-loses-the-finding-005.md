envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:29:29Z

component=plan-marshall:manage-findings
category=anti-pattern
created=2026-07-28

# The guard that reports lost findings can itself be a lost-finding vector

All four producer-mismatch emitters discovered in this plan were themselves unchecked
persists: the very guard whose job is to report a producer/finding-type mismatch was
silently swallowing its own report when the persist call failed. A reporting mechanism
inherits the exact defect class it exists to catch if its own emission path is not held
to the same checked-persist standard as the paths it guards.

## Solution

When adding or auditing a guard/validator whose job is to report a defect elsewhere,
apply the same checked-persist / fail-loud discipline to the guard's OWN emission path.
Treat "the reporter" as just another producer subject to the population sweep, not as
infrastructure exempt from the defect it detects.

## Impact

A self-referential blind spot in a reporting mechanism means the exact failures it
exists to surface are the ones most likely to go unreported.
