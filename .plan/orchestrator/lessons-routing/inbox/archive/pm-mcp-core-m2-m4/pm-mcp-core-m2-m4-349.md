envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:50Z

# ADR number collisions in module ADR directories are invisible to git and to the branch-cleanup gate

**Components:** plan-marshall:phase-6-finalize branch-cleanup (ADR duplicate-number gate) [foreign]; and this repository's module ADR convention `{module}/doc/adr/{package}/NNN-{slug}.adoc` (pm-core/doc/adr/core-store/) [local to pm-mcp-core]
**Category:** bug
**Source plan:** plan-14-operator-and-question-stores (PR #93)

## Observation

While this plan added ADRs 029-036 in `pm-core/doc/adr/core-store/`, main added its own ADR 029 (later 030 and 031) in the same directory. Different slugs mean different filenames, so git reports no conflict. The collision was found only by reading `git ls-tree origin/main` of the directory. The ADR duplicate-number gate of branch-cleanup scans only `doc/adr` (repository ADRs), not module ADR directories, so it would not have caught it.

## Suggested corrective action

- Foreign (plan-marshall): extend the duplicate-number gate to every ADR directory, i.e. any `**/doc/adr/**` directory, comparing branch numbers against origin/main after sync.
- Local (pm-mcp-core): before finalize, and after every rebase, re-number ADRs added by the plan against `git ls-tree origin/main` of each touched module ADR directory; parallel plans touching the same package ADR directory should expect collisions.
