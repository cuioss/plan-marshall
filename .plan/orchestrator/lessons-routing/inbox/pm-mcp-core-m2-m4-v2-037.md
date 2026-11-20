envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T13:43:24Z

component=doc-review
category=bug

# Make the trace.py links check work from a plan worktree

## Context

In plan-v2-155 the CLAUDE.md links check `python3 ../plan-marshall-documentation/.claude/skills/doc-review/scripts/trace.py ../plan-marshall-documentation/doc .` (also with absolute sibling paths) reported 3 090 broken links when run from the plan worktree, because every relative link into a sibling repository breaks by depth alone. Execute wrote a plan-local `links_check.py` wrapper that compares the worktree against the main checkout, and every review round re-ran that wrapper.

## Root cause

The sibling links are relative to the main checkout's position beside the other repositories; a worktree under `.plan/local/worktrees/` sits deeper, so the check cannot be run as written in the place plans do their work.

## Proposed action

Give trace.py a base-directory option (or document the main-vs-worktree comparison as the canonical check) and change the CLAUDE.md command accordingly, so a plan does not have to rebuild the wrapper each time.

## Evidence

- aspect: chat-history-analysis — execute report: "every link into the sibling repositories breaks from there by depth alone (3 090 false broken links)"
- aspect: llm-to-script-opportunities — measure/anchors/links re-run by hand about 8 times across review rounds
