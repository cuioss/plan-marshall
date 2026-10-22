envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:30Z

component=plan-marshall:build-server-client
category=bug
bundle=plan-marshall

# Emit build-server wait lines on state change, not per poll iteration

## Context

`build_server` long-polls a submitted job and writes a `build-server wait result:` line to the plan's work log on each poll iteration. On this run the loop emitted 2040 such lines, out of 2334 total work-log entries — 87% of the log. The worst burst wrote 1056 lines inside a single second (`2026-10-21T13:50:28Z`), with only two distinct payloads among them; three further bursts wrote 201, 180 and 148 lines at one timestamp each.

The damage is not cosmetic. `analyze-logs` counts 2334 work entries and 1459 script entries over a 404 KB log whose signal is a few dozen lines; `log-analysis`'s tag counts and the retrospective's log-reading aspects spend their budget on the same line repeated. A reader looking for what happened during a 28-minute quality-gate wait has to filter thousands of duplicates to find the six lines that carry state.

## Root cause

The wait loop logs unconditionally per iteration and has no de-duplication of a repeated status: when the daemon returns the same `job_status` and `elapsed`/`eta` pair, the line is byte-identical to the previous one and is still written. A tight retry path (the 13:50:28 burst) can therefore write the same line hundreds of times per second.

## Proposed action

Log on state transition or at a bounded interval: emit when `job_status` changes, when `elapsed` advances by at least the poll interval, or at most once every N seconds (N ≈ 30), whichever comes first. Keep the final line unconditional so the terminal status is always recorded. A one-line suppression counter in the final result ("suppressed M duplicate wait lines") preserves the information that polling was long without the volume.

## Evidence

- aspect: log-analysis — `counts.work_entries: 2334`, `script_duration_max_ms: 1709680`, `slowest_scripts` all `build-maven`.
- aspect: llm_to_script_opportunities — candidate 2, repetition_count 2040, with the per-timestamp burst counts.
- logs/work.log — 2040 `build-server wait result` lines; 1056 at `13:50:28Z` carrying 2 unique payloads.
