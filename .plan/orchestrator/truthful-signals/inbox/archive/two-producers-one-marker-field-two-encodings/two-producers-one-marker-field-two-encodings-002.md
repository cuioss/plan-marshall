envelope_version=1
sender_type=plan
sender_id=two-producers-one-marker-field-two-encodings
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T04:55:01Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=two-producers-one-marker-field-two-encodings
source_pr=1125
suggested_epic=truthful-signals
relates_to=insight-finding-1a5cf7

# The pin-trap detector surveys three consumers and misses the running session's own seat

## Context

`finalize-step-sync-plugin-cache` emitted the documented #896 pin-trap warning at
2026-08-09T04:17:56Z:

> PIN TRAP ARMED — the three consumers disagree. registry_pin=0.1.1327 (and 1327 is
> ORPHAN-MARKED, i.e. GC-scheduled), executor_version=0.1.1331,
> unmarked=[0.1.1330, 0.1.1331] which is TWO dirs not one. 14 dirs total, 12 marked.

The detector is correct as far as it reaches, and its three consumers genuinely
disagree. But there is a fourth consumer it does not survey: the version the running
session's skill bodies were actually loaded from.

This retrospective envelope loaded every one of its six skills from
`0.1.1304`. That version is not the registry pin (1327), not the executor version
(1331), and not a member of the unmarked set. It is also orphan-marked —
`.../plan-marshall/0.1.1304/.orphaned_at` reads `2026-08-08T20:30:11Z`, stamped
during this very plan's execution.

So the live session was executing skill bodies from a GC-scheduled directory while a
detector three lines away reported on three other numbers and said nothing about it.

## Root cause

The pin-trap assertion is written over the three surfaces the sync step itself writes
or reads (registry pin, generated executor, cache marker state). The loaded-skill-body
version is a fourth surface, owned by the plugin loader, that no participant in the
assertion consults — even though it is the one that decides which instructions the
agent is actually following. The detector's population is the set of things the
writer touches, not the set of things a divergence can harm.

The seat is also first-party observable at zero cost: every loaded skill reports its
own base directory, so the running version is available to any agent in the envelope.

## Proposed action

- Add the session's loaded-skill-body version as a fourth term in the pin-trap
  assertion, and report it in the warning alongside the existing three. The invariant
  becomes `seated == executor == pin == sole unmarked dir`.
- Report the seat's marker state explicitly. A seated directory that is orphan-marked
  is the liveness hazard, not merely a version skew, because the only reason it
  survives is that `cache_retention` is an age/count keep-union that never reads the
  marker.
- Where the seat cannot be read by the script, have the dispatched agent report it —
  it is in every skill's base-directory line — rather than leaving the fourth
  consumer unsurveyed.

## Evidence

- first-party: all six skills loaded by this envelope report base directories under
  `/Users/oliver/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1304/skills/`
- first-party: `.../plan-marshall/0.1.1304/.orphaned_at` = `2026-08-08T20:30:11Z`
- first-party: `.../plan-marshall/0.1.1327/.orphaned_at` = `2026-08-08T23:19:30Z`
  (the registry pin is itself marked, as the warning states)
- first-party: `.../plan-marshall/0.1.1331/.orphaned_at` does not exist (unmarked)
- log: `[WARNING] (project:finalize-step-sync-plugin-cache)` at 04:17:56Z, naming
  exactly three consumers
- `cache_retention sweep` confirms `0.1.1331` is newest-on-disk and `0.1.1304` is
  retained only by `younger_than_d_days` — an age rule, not a marker rule

## Recurrence

This is an n+1 recurrence of this plan's own pending insight finding `1a5cf7`, which
recorded the identical condition one plan earlier: the session seated on marked
`0.1.1240` while the fresh bundle was `0.1.1326`. That finding closed with "a
marker-driven collector would have removed a live session's skill bodies", and it is
still `pending` and unpromoted in this plan's findings store. The condition has now
been observed twice in consecutive plans, from inside the affected session both times.
