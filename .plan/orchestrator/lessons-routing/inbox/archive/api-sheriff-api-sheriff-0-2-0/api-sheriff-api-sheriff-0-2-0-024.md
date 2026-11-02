envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-17T13:55:58Z

# Candidate lesson: Build-server long-poll writes the same wait-result line to the work log dozens of times per poll (plan-marshall:build-server-client)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 007.

RECURRENCE: same defect as api-sheriff-api-sheriff-0-2-0-017 (PLAN-V02-44); second plan in a row.


**Source**: plan work log for this run (an observed tooling defect, not a project one).
**Probable owner**: plan-marshall:build-server-client (wait/long-poll logging) / plan-marshall:manage-logging.

## What happened

In one daemon long-poll cycle, the work log got the same line about 70 times with one hash_id, then about 20 more times with the next hash_id, all within the same second:

```
"2026-10-17T10:08:46Z",INFO,96b5d3,"build-server wait result: job_id=929f5f59... job_status=running elapsed=299 eta=195.9 mechanism=daemon_longpoll"
... (repeated, 10:08:46-10:08:47)
"2026-10-17T10:08:47Z",INFO,bf9d5e,"build-server wait result: job_id=929f5f59... job_status=running elapsed=300 eta=195.9 ..."
... (repeated)
```

The same pattern shows up again for job b7e14e8d at 12:23:11. Because of it, the plan's work log is 1090 entries / 200 KB, mostly these duplicates. A `manage-logging read --type work` no longer fits in an agent's read budget, so retrospective and lessons steps can't scan the log for `[FAILED]` / `script_failure` markers.

## Corrective rule (candidate)

The wait loop should log one line per state change (or one per real poll round-trip), not one per internal iteration or retry. A test should check that a single long-poll that returns `running` writes exactly one work-log entry.
