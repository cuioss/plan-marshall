envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:55:11Z

component=plan-marshall:manage-architecture
category=anti-pattern

# A test that pins a pointer must also assert the restatement is absent

Source: Q-Gate finding 1834df (6-finalize; fixed in e482d93e7).

test_capabilities.py:622 checked only that the pointer LANGUAGE was present. It did not
check that a restated count or roster was ABSENT. The whole point of replacing a
duplicated roster with a pointer is that the duplicate stops existing — a presence-only
assertion stays green if someone later re-adds the roster next to the pointer, which is
the exact regression the change was made to prevent.

## Solution

When a change removes a duplicated source of truth in favour of a pointer, the guarding
test needs BOTH arms: the pointer is present AND the restatement is gone. A
presence-only assertion pins the fix's cosmetic half and leaves its substantive half
unguarded.

## Impact

Generalizes to every "replace the restatement with a pointer at its source" fix, which
is the terminating move for the self-seeded-finding class this repository keeps hitting.
