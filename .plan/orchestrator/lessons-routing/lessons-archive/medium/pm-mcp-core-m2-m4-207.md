envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T10:35:51Z

# Point leaves at architecture --project-dir for sibling-repo search instead of Bash grep

## Context

Plan diagram-generator carried a deliverable in the sibling checkout /Users/oliver/git/plan-marshall-documentation. Two dispatched leaves reported breaking the "no Bash grep" rule there: the phase-3-outline leaf ran Bash grep twice on the sibling repo, and the finalize-rebase-fix leaf ran it three times. The 4-plan q-gate leaf, by contrast, swept the same sibling repo cleanly through `architecture --project-dir` (capabilities showed it derivable, 187 files scanned).

## Root cause

The persona's search fallback chain (architecture find/search, then Grep/Read) is written for the current project. It does not say that `architecture --project-dir` covers a sibling checkout, so a leaf that sees a path outside the inventory treats the gap as having no sanctioned search path and falls back to Bash grep.

## Proposed action

In persona-plan-marshall-agent tool-usage-patterns (and the manage-architecture client-api search section), add one line: for a path in another checkout, use `architecture --project-dir {checkout} search --content` / `find` first; return the coverage gap to the orchestrator only when that checkout is not derivable. Never use Bash grep.

## Evidence

- chat-history-analysis: phase-3-outline hand-back "I ran grep through Bash twice in that repo"; finalize-rebase-fix hand-back "used Bash grep three times"
- chat-history-analysis: 4-plan q-gate hand-back swept the sibling repo via `architecture --project-dir` with no violation

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `diagram-generator-006.md` from plan diagram-generator (PLAN-16, #49; Claude Code)
