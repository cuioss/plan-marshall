# WS-07: Self-Review & Findings

epic: quality-aspect

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-07-quality-aspect.md` and is tracked in the epic
> `status.json` `workstreams[]` field.

## Charter

Owns self-review coverage and finding lifecycle closure: detectors that see every
user-facing site class, surfacer classes a reviewer can already find, prompt-field
validation before dispatch, and every advisory/refuted finding reaching a terminal
state with someone responsible for closing it. Closed when a clean round means a
clean surface and no finding names its discharge condition to nobody.

## Scope

- In scope: ext-self-review detectors and surfacer classes, pre-submission prompt
  validation, hand-mirrored-table checks, manage-findings resolve/reject paths,
  chat-signal extraction and halt reporting.
- Out of scope: review-bot participation signals (WS-03), finalize re-fire
  accounting (WS-08).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-13-self-review-detectors | staged | Docstring/adoc detectors, mirrored tables, plugin-doctor, finding closure |
| PLAN-14-chat-signal-halt | staged | Chat-signal fidelity, read-phase filter, version stamp, script registration |

## Sequencing and Surface Notes

- PLAN-13 (plugin-dev/findings) and PLAN-14 (retrospective/logging) are
  surface-disjoint and may run concurrently.
