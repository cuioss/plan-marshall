envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:54:07Z

component=plan-marshall:manage-architecture
category=bug

# A section forbade a third spelling by name and then used it 89 lines later

Source: Q-Gate finding ad9a7b (6-finalize, self-review; fixed in cc4e8cf1b).
Defect class contract_drift — 2 findings in this class this round.

client-api.md's capabilities section declares at lines 1418-1420 that every entry emits
exactly `derivable` or `not_derivable`, with "no per-entry exception and no second
spelling", and the entry-shape table plus all three worked payloads honour it. The
leaf-reading paragraph at line 1507 then says content_search reports `available` off the
leaf's own crawl — a third spelling the same section forbids by name.

A live `architecture capabilities` run in the worktree returns status=derivable for
content_search, so the CODE is correct and the PROSE is wrong.

## Solution

A consumer branching on the documented two-value vocabulary would never match
`available`, and one trusting the sentence would write a branch that never fires. When a
document states a closure ("no second spelling"), the closure claim raises the bar on
every later use of that vocabulary in the same document — grep the document for the
retired spellings in the same change that writes the closure.

## Impact

This is the published consumer contract, so the stale sentence is the one an integrator
reads.
