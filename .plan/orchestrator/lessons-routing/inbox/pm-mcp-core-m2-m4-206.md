envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:49Z

# After a sync-baseline rebase, re-verify against the new base from a clean build

## What happened

At finalize, the sync-baseline step rebased `diagram-generator` (PR #49, pm-mcp-core) onto main, which had meanwhile merged #48 (a stricter static workflow verifier). Two things followed:

1. The diagram generator's test fixture, valid before the rebase, was now refused by the stricter verifier (`ENTITY_KIND_BINDING`, and a missing `stepped_out` route). The fixture had to be corrected after the rebase.
2. The first quality-gate run after the rebase reported false failures that came from stale `target/` output of the pre-rebase build; they disappeared after a clean build.

## Rule

A rebase that pulls in a sibling plan which tightens a validator is a semantic change to the plan's own fixtures, not only a textual merge: the plan's full verify must run again after the rebase. That verify must start from a clean build (`clean` before `verify`), because Maven's incremental output in `target/` can carry pre-rebase compiled classes and generated resources and produce failures (or passes) that do not belong to the rebased tree.

## Epic-level hint

When two plans of the same epic touch a validator and the content it validates, the orchestrator can sequence them or flag the later one to re-check its fixtures against the earlier one's rules.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-004.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
