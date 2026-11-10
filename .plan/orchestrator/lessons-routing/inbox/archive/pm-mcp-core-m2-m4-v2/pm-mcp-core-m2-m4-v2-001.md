envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:05Z

component=plan-marshall:phase-5-execute
category=bug
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Record a rewriting quality gate's success against the tree it verified

## Context

In plan-v2-93 `verify -Ppre-commit` rewrote the import order of `pm-provider-http/.../HttpClient.java` on every run. The freshness gate then stayed `stale` with `build_indeterminate`: the dispatch row was recorded against the clean tree `1c781679` with status `unknown` (the wrapper returned `running` after 300 s), and the success row (1049 s, 9367 tests) was recorded against the dirty end-state tree `9d87c1fb`. After the rewrite was discarded the tree was `1c781679` again, so no success row matched it. Re-running the gate could never clear it. Two jobs showed the same pattern (8af4fa43, e01bad99). It took an extra hand-back dispatch and an operator ruling to get out.

## Root cause

The freshness check keys a build's verdict on the tree at completion. A gate that rewrites files ends on a tree nobody commits, so its success can never match the tree it actually tested.

## Proposed action

Record the success row of a long-running or rewriting build against the tree at dispatch (or record both and let the freshness check accept a match on the dispatch tree when the end-state diff is only the gate's own rewrite). When the gate rewrites files, name the rewrite in the hand-back so the orchestrator commits it or the operator is asked once.

## Evidence

- chat-history-analysis: freshness hand-back report with both tree hashes and the three options
- plan-efficiency: an extra 5-execute hand-back dispatch and a 1049 s whole-tree verify run twice
- request-result-alignment: 10 undeclared pm-provider-http files, all rewrites by the gate
