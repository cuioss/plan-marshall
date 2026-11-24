envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:25Z

component=plan-marshall:plan-marshall
category=improvement

# Record an API-limit kill of a dispatched envelope as a dispatch boundary

## Context

In plan-v2-155 execute envelope 2 was terminated by the weekly API limit (HTTP 429). The orchestrator resumed it with "continue" and the envelope finished, but the kill left no dispatch-boundary row, no work-log line and no termination cause; it is visible only in the chat transcript, and its spend is folded into the later row.

## Root cause

The dispatch-boundary recording runs on a normal return; a harness-level agent failure notification does not pass through it.

## Proposed action

When a dispatch returns a failed task-notification, record a `harness_cancellation` boundary row (with the API error cause) and a work-log WARNING before re-dispatching or resuming.

## Evidence

- aspect: logging-gap-analysis — weekly-limit kill has no dispatch-boundary row and no work-log line
- aspect: chat-history-analysis — task-notification "Agent terminated early due to an API error: You've hit your weekly limit"
