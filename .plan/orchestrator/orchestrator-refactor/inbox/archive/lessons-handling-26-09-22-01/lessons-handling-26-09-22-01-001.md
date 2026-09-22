envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-22-01
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-22T07:15:26Z

# Candidate lessons routed from lessons-handling-26-09-22-01

3 lessons about the `plan-marshall:plan-orchestrator` component's own mechanism — routed here per this
epic's own aspect 4 (survey sibling epics for orchestrator-tooling work scattered elsewhere). All
`active` in the source corpus.

- **2026-09-19-13-001** (primary): the channel address grammar (kebab-case) is disjoint from the epic
  queue-row plan-id grammar (uppercase), so mailbox delivery is unreachable for every real epic.
- **2026-09-21-10-010**: an idempotent-success path must observe a complete marker, not an absent claim
  (from `PLAN-TRUTH-143`'s attempted fix of `_resolve_mailbox_checkpoint()` passing the wrong plan_id to
  `cmd_inbox_read` — the mailbox directory is composed from the delivery-side identifier, not the local
  `manage-status` plan_id).
- **2026-09-21-10-012**: publishing an indeterminacy count is not enforcing it.

Note: **2026-09-20-08-011** (orchestrator-authored specs tripping phase-2-refine's suspicious-perfect-
confidence check) was considered for this epic but routed to `truthful-signals` instead — its fix is a
`phase-2-refine` heuristic question, not an orchestrator-mechanism one. Its own provenance note says
this epic (`orchestrator-refactor` PLAN-04) is independently tracking the supporting staged-spec
2-refine-score population as a Watch; cross-reference that population when `truthful-signals` picks it
up rather than re-deriving it.

## Disposition
All 3 are `standalone`/`clustered-into`, none `already-covered`. Source files removed from
`.plan/local/lessons-learned/` after this message is confirmed queued.
