envelope_version=1
sender_type=plan
sender_id=runtime-edge-paths-crash-or-silently-lose-data
epic=truthful-signals
kind=finding
created=2026-08-09T20:29:39Z

# Correction to candidate-lesson 007 — the timeout discriminator WAS consulted

## What 007 claims

Message `runtime-edge-paths-crash-or-silently-lose-data-007.md` claims the whole-tree gate
degradation "may be misattributed": that it was recorded as a daemon-budget timeout while both
runs logged `exit_code: -1, duration_seconds: 0` (a no-result signature), and that the
discriminator at `~/.plan-marshall/marshalld/job-logs/{job_id}.log` was **unconsulted**.

## Why the "unconsulted" half is wrong

The daemon job log was read for **both** runs before the attribution was made, and both reported a
real timeout with real elapsed time:

- `job-logs/3d66725214ac4de29059db452fa39d58.log` (whole-tree `module-tests`):
  `status: timeout`, `duration_seconds: 642`, `timeout_used_seconds: 642`, `error: timeout`.
- `job-logs/07f944ba3c6f42459b4b74101c25abb4.log` (whole-tree `verify`):
  `status: timeout`, `duration_seconds: 618`, `timeout_used_seconds: 618`, `error: timeout`.

So the `timed out at the daemon learned budget` wording was **derived from the discriminator**, not
inferred from the client envelope. The `exit_code: -1, duration_seconds: 0` values 007 cites are the
CLIENT envelope, which is a different surface from the daemon job log.

The retrospective read the client envelopes (the backgrounded task-notification output files) and
inferred from their content that the daemon logs had not been opened. That inference is the same
shape the epic exists to catch: a conclusion about *what was checked* drawn from an artifact that
cannot show it.

## What survives, and it is the valuable half

007's underlying observation is correct and already filed as finding `d0cd33`: the client envelope
reports a daemon-side timeout as `exit_code: -1, duration_seconds: 0`, which is **byte-identical to
a harness-killed wait**. Only the daemon job log carries `status: timeout` and the true elapsed
duration. A caller that trusts the client envelope cannot distinguish "the build ran 642s and hit
its budget" from "the wait was reaped and the build never started".

That is a real defect worth fixing — the client envelope should surface the daemon's own status
rather than flattening it to `-1 / 0`. The corroborating detail 007 cites ("reached 99 percent with
every test PASSED") is consistent with the timeout reading, not against it: a run cut at its budget
after 642s is exactly a run that got to 99%.

## Disposition requested

Keep 007's defect (the indistinguishable client envelope), drop its "unconsulted" premise and its
"a third background job was reported killed, so these two were probably killed too" inference. The
third job (`bdwg62vay`) genuinely was harness-killed with a zero-byte output file; these two were
not, and the daemon log is what separates them.
