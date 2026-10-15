envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:55Z

# Candidate lesson: staged-spec / refine premises not re-checked against sibling-plan landings before merge

**Source plan:** plan-21-entity-addressing (PR #54, merged b25d115)
**Signal source:** orchestrator-observed event, verified in decision.log (entries 0b3537, e95b31, 4861a3)
**Suggested component:** plan-marshall:phase-2-refine (also touches plan-marshall:plan-orchestrator spec review)

## What happened

- Refine (10:45) already found the staged spec's greenfield claim refuted by HEAD (PLAN-13 had landed WorkflowEngine etc.), and corrected it.
- Refine then recorded the premise "no pending-entry store exists yet" behind operator answers q2/q3, and the design (EntityIdGrammar with its own entry_id grammar, PendingEntryReader port whose Javadoc said the pm-runtime store implements it) was built on it.
- While the plan executed, sibling plan #51 (d7b622d) landed pm-core `core.store.EntryId` (grammar `ent-[0-9a-f]{8,32}`) and `PendingEntryStore` / `PendingEntryRecord`.
- The contradiction surfaced only at the finalize branch-cleanup semantic re-verify (13:51), which escalated to the operator; the operator chose "Rework in this PR", forcing a rebase, a new fix task TASK-10 and a loop-back 6-finalize -> 5-execute (one extra execute + verify + CI + review round).

## Gap

There is no step between refine and finalize that re-checks the plan's load-bearing premises against what sibling plans of the same epic have landed (or are about to land) on the base branch. The init-time sibling-collision check (005b07) compared file overlap only and the operator proceeded; it does not re-run later and does not compare semantic premises ("X does not exist yet").

## Possible corrective action (for orchestrator judgement)

- Record refine premises of the form "X does not exist yet" as explicit, re-checkable claims, and re-verify them against HEAD of the base branch at execute entry and/or at the pre-push / sync-baseline step (not only at branch-cleanup).
- Alternatively, when the epic ledger shows a sibling plan in flight whose spec touches the same package or concept, have the orchestrator sequence the plans or flag the dependency in the staged spec.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-001.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
