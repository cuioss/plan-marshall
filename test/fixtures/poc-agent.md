---
name: poc-agent
description: |
  Fixture canonical agent for the agent-resolution regression test.
  Pinned to model: sonnet (no effort) so the regression test can verify
  Claude Code dispatches THIS file when the parent calls Task: poc-agent
  (canonical no-suffix dispatch / inherit resolution case).

  Examples:
  - Input: any
  - Output: a TOON payload echoing the input plus the agent's <usage> block
tools: Read
model: sonnet
---

# POC Canonical Agent

Trivial fixture agent used by `test_agent_resolution_poc.py` to verify:

1. Claude Code resolves agent names via the canonical / variant suffix
   convention. `Task: poc-agent` MUST dispatch this file.
2. The pinned `model: sonnet` is honoured by the runtime — the agent's
   returned `<usage>` block names the Sonnet model (not Opus inherited
   from the parent).
3. The agent runs without an `effort:` field — Sonnet medium is the
   default.

Do not modify this file's frontmatter without updating the regression
test in `test/marketplace/targets/claude/test_agent_resolution_poc.py`.

## Workflow

Receive an arbitrary prompt, return a TOON payload acknowledging it. The
returned `<usage>` block carries the model fingerprint that the test
inspects.
