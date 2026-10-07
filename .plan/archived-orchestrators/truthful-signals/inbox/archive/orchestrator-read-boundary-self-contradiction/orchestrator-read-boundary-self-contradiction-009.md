envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:45:27Z

component=plan-marshall:manage-build-server
category=bug
created=2026-07-28
bundle=plan-marshall

# Build-server preflight readiness is a point-in-time probe reported as a standing guarantee

## What happened

At `16:15:03Z`, `1-init` recorded:

```
(plan-marshall:phase-1-init:build-server) Preflight ready (marshalld v1)
  - no action required; builds route to the daemon
```

That claim held for about eighty minutes. One routed build succeeded at `17:34:58Z`
(`mechanism=daemon_longpoll`, `job_status=success`). Then, from `17:36:24Z` onward,
**every** build in the run logged:

```
[BUILD-SERVER] resolved build (requested=auto, resolved=in_process,
  reason=socket_absent, mechanism=in_process_fallback)
```

Ten or more occurrences across phases 5 and 6 — the phase-5 verification sweep, all
three `pre-push-quality-gate` builds, the loop-back re-verification, and the
post-fix builds. The daemon died mid-run and every subsequent build silently
degraded to in-process.

The fallback itself is correct behaviour and it *is* logged at `WARNING`. Two things
are still wrong:

1. **The preflight's phrasing is a standing claim** — "no action required; builds
   route to the daemon" — for a probe that only ever established a fact about
   `16:15Z`. Nothing re-asserted it, and nothing reconciled the init-time claim
   against the run-time reality.
2. **Sustained degradation never escalates.** The tenth identical `socket_absent`
   warning is emitted exactly like the first. A one-off fallback and a
   daemon-is-gone-for-the-rest-of-the-run condition are indistinguishable in the log,
   and neither surfaces to the operator above `WARNING`.

## Solution

**Rule:** a readiness probe reports a *timestamped observation*, not a standing
guarantee, and a repeated degradation is a different signal from a single one.

1. **Phrase the preflight as observed-at.** `Preflight ready (marshalld v1) as of
   {ts} — builds will route to the daemon while it stays up`. Cheap, and it stops the
   init-time line from reading as a contract for the whole run.
2. **Count consecutive fallbacks and escalate.** After N consecutive `socket_absent`
   resolutions, emit one `ERROR`-level line naming the transition
   (`daemon was reachable at {ts}, unreachable since {ts}, {n} builds degraded`)
   rather than the N+1st identical `WARNING`. One transition event beats ten repeats.
3. **Reconcile at finalize.** If a plan preflighted `ready` and then ran every build
   in-process, that discrepancy belongs in the plan's own record — right now it is
   recoverable only by reading the raw work log.

## Impact

On theme: a confident readiness signal that was true when emitted and false for the
majority of the run it was taken to cover.

The practical cost here was schedule, not correctness — in-process builds produce the
same verdicts, just slower, and the two ~10-minute `ci_complete_precondition` waits
plus the general finalize length are consistent with that. But the *shape* is the
dangerous part: an init-time green that no later signal contradicts loudly enough to
notice. This project's memory already carries `marshalld`-related false-signal
incidents in both polarities (a routed build reporting false-green, and a genuinely
green verify reported as `timeout/-1`). A preflight whose claim silently expires is
the same family, and it is the one that makes the other two harder to diagnose —
because "was the daemon even up?" is not answerable from anything except a manual
scan of the work log.
