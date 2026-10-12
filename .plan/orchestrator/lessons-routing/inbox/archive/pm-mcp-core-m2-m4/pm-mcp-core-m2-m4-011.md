envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:09:59Z

# Candidate lesson: Count loop-back execute usage once, not in both phase rows

- Component: plan-marshall:manage-metrics
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-07-019 (created 2026-10-10), epic pm-mcp-core-m2-m4

## Source

Retrospective of plan primitive-spi-and-validators (plan-efficiency aspect). Derived from `work/metrics.toon`, the three boundary files and the orchestrator's own statement that it accumulated loop-back execute usage into the 6-finalize accumulator. The double count is inferred from the figures; no record states it.

## Context

The plan looped back from finalize to execute three times. Each loop-back execute step recorded a boundary row under 5-execute (266380, 225610 and 195770 tokens; 687760 together). The 5-execute phase had already closed at 22:51:10Z with `total_tokens: 1080515`. At generate time the 5-execute row takes the larger of its measures, the boundary sum 1768275, which contains the three loop-back rows. The orchestrator added the same three usages to the 6-finalize accumulator, whose total is 3276786.

## Root cause

Two writers attribute the same hand-offs to two different phases: the boundary recorder files a loop-back execute step under the phase it ran as (5-execute), the orchestrator's accumulator files it under the phase that was open (6-finalize). The reconciliation picks the maximum per phase and sums the phases, so nothing detects the overlap.

## Evidence

- `work/metrics.toon`: 5-execute `total_tokens: 1080515`, `dispatch_boundary_total: 1768275`, `tokens_cell_source: dispatch_boundary_total`; 6-finalize `total_tokens: 3276786`, `dispatch_boundary_total: 2392241`.
- 1768275 minus 1080515 = 687760 = 266380 + 225610 + 195770, the three boundary rows stamped after the phase closed (23:27:11Z, 23:56:33Z, 06:26:46Z).
- 3276786 minus 2392241 = 884545 = 687760 + 196785. The remainder fits the one finalize hand-off that recorded no boundary row (the documentation pull request update). That last attribution is a fit, not a reading.
- Reported plan total 6475090; without the overlap about 5787330.

## Not established

- Whether the accumulator really holds exactly these three usages: the accumulator file was not opened, only its total.
- Whether the remainder 196785 is the documentation hand-off.

## Proposed action

Decide one owner for loop-back execute usage. Either the accumulator of the open phase never receives a hand-off that also writes a boundary row under another phase, or the reconciliation subtracts boundary rows stamped after a phase's `end_time` from that phase and reports them under the phase that was open. Until then, `generate` should flag a phase whose boundary sum exceeds its closed total by rows stamped after the close.
