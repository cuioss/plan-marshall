envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:38:48Z

## The hook-demotion partition has a second tier, and it is where cost escapes

Source: Day 5 whitepaper (see message 006 for provenance). Refines message 002's partition.

### The pattern

Day 5's Policy Server splits enforcement into two layers rather than one:

- **Structural gating** — deterministic rules over roles and environments, read from a `policies.yaml`.
  Fast, binary, no model call. Its example: a `viewer` role cannot invoke `send_email`.
- **Semantic gating** — a secondary LLM inspects the *intent and content* of a proposed action against
  natural-language policy. Its justification is the honest one: "a tool is allowed, but the way it is used
  violates a policy... You cannot regex every possible PII leak."

### Why it matters to message 002

Message 002 partitions the hard-rule set on *mechanically checkable* × *chronically violated* and routes the
intersection to hooks. That partition is too coarse: "mechanically checkable" silently contains two tiers
with different cost profiles.

Several of our rules are structural and would hook cleanly — direct `.plan/` access, bare `gh`/`glab`,
hard-coded `./pw`/`mvn`/`npm`, temp files outside `.plan/temp/`. Others are exactly the semantic case:
"Workflow steps: no improvisation" and "Structured queries first" are not regex-decidable, which is precisely
why they have survived as prose. The obvious next move — put a judging model in front of the calls prose
cannot gate — is the move message 005 warns about. A semantic gate is a model call on every intercepted tool
call, on a substrate that already spends 48–81% of a run inside its verification layer.

### The useful form of the finding

The partition becomes three-way, and the third cell is a decision rather than a task:

| Cell | Route |
|------|-------|
| Structural + chronically violated | Hook. Cheap, deterministic, and it shrinks the static prose tier. |
| Structural + never violated | Deletion candidate from the static tier — the rule is carrying no load. |
| Semantic (not regex-decidable) | ⛔ **Not automatically hook material.** Each one needs a stated cost ceiling before it is gated, or it must stay prose and be measured by WS-01 instead. |

The third row is the finding. Without it, message 002's sweep would route its hardest cases straight into an
unbounded per-tool-call model spend and call that enforcement.

### Status

A correction to a partition this epic has already been asked to run, not a new direction.
