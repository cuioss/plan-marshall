---
name: poc-agent-high
description: |
  Fixture variant agent for the agent-resolution regression test.
  Pinned to model: opus, effort: high so the regression test can
  verify Claude Code dispatches THIS file when the parent calls
  Task: poc-agent-high (variant suffix dispatch case).

  Examples:
  - Input: any
  - Output: a TOON payload echoing the input plus the agent's <usage> block
tools: Read
model: opus
effort: high
---

# POC Variant Agent (high)

Trivial fixture agent used by `test_agent_resolution_poc.py` to verify:

1. Claude Code resolves variant suffixes — `Task: poc-agent-high` MUST
   dispatch this file (NOT the canonical `poc-agent` and NOT some
   fuzzy-matched alternative).
2. The pinned `(model: opus, effort: high)` pair is honoured by the
   runtime — the agent's returned `<usage>` block confirms both fields
   propagated.
3. Effort propagation works at the variant level (the canonical
   declares no effort; only this variant does).

Do not modify this file's frontmatter without updating the regression
test in `test/marketplace/targets/claude/test_agent_resolution_poc.py`.

## Workflow

Receive an arbitrary prompt, return a TOON payload acknowledging it. The
returned `<usage>` block carries the model and effort fingerprint that
the test inspects.
