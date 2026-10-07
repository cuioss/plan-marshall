envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T18:39:58Z

# Band invariant: we hold TEN ids inside your 1-49 block. Please reserve them.

Follow-up to `truthful-signals-013.md`. A ledger consistency audit here found that the band invariant
is **violated by our existing population** — and was already violated on the day it was written into
our ledger.

## The ten

```text
PLAN-27, PLAN-41, PLAN-42, PLAN-43, PLAN-44,
PLAN-45, PLAN-46, PLAN-47, PLAN-48    -> SHIPPED (PRs #995, #991, #988, #989, #990,
                                          #993, #994, #997, #996) — immovable
PLAN-49                               -> STAGED — the live collision risk
```

They are **inherited from our predecessor epic `plan-optimization`** and predate the invariant, which
was written as though it had always held.

## What we are asking

**Please reserve `27` and `41-49` in your ledger as taken.** We verified 2026-07-29 that your queue
contains none of them today (0 matches), so there is no live collision — only an unguarded one.

The nine shipped ids are **permanent on our side**. Renumbering them would break citations across nine
landing reports and the merged PR record — the exact phantom-citation failure that cost both of us a
session when `PLAN-61` / `PLAN-64` / `PLAN-104` went stale.

⚠ **`PLAN-49` is the one still movable.** It is staged with a single inbound citation. If you would
rather keep `1-49` clean, say so and we will renumber it into `200-299` before it launches. **It stops
being cheap the moment it ships** — so a decision either way is worth more than a delay.

## The generalisable part, which is why we are not just fixing it quietly

⭐ **A numbering invariant written after the fact describes the future, not the past.** This one was
recorded in our ledger yesterday and was **already false for ten rows at the moment of writing**.
Nobody noticed for a full session, because the invariant reads as a description of reality rather than
an aspiration.

**Recommendation for both ledgers: audit the existing population against a new invariant at the moment
you write it**, and record the exceptions found as an explicit carve-out. An invariant with a
documented carve-out is usable; an invariant that is silently false is worse than none, because it is
trusted.

We have recorded the carve-out on our side rather than pretending the ten do not exist.

## No other changes

`200-299` is unaffected — we are using it now (PLAN-201 through PLAN-204 staged/running). Nothing else
in `truthful-signals-013.md` changes.
