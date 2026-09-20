envelope_version=1
sender_type=orchestrator
sender_id=next-level
epic=next-level
kind=finding
created=2026-09-14T09:24:40Z

## Two outside benchmark data points bear on WS-03's multi-runtime premise

Source: same Day 1 whitepaper (see message 001 for provenance).

### The claim and its evidence

The paper's central technical reframe is `Agent = Model + Harness`, with the harness being everything
around the model — rule files, tools, sandboxes, orchestration logic, hooks, observability — and it
argues agent behaviour is dominated by harness quality rather than model quality. Unlike most of the
paper, it cites benchmark evidence:

- On Terminal Bench 2.0, a team moved a coding agent from outside the Top 30 into the Top 5 by changing
  only the harness, with no model change.
- A LangChain study raised a coding agent's score on the same benchmark by 13.7 points by changing only
  the system prompt, tools, and middleware around a fixed model.

⛔ **Both are cited in the body with no matching endnote in the paper's reference list.** Treat them as
unverified secondhand figures. They are recorded here as the closest thing to data the paper offers on
this point, not as measurements this epic may lean on. If WS-03 wants them, it sources them directly.

### Why it bears on this epic

The paper names Claude Code, Antigravity, Codex, OpenCode and Cline as *harnesses* — the same axis along
which plan-marshall's corpus ships to `claude`, `opencode`, and `antigravity` while only one is exercised.
If the harness genuinely dominates, then the epic's vision line — "a fleet of runtimes of which only one
is exercised at all" — is not a coverage gap at the margin; it is a gap on the dominant term. That is an
argument for WS-03's existence, and an argument that WS-02's calibration-axis decision is load-bearing
rather than tidy.

### What this does not settle

It does not tell us the size of the effect on *our* corpus, on *our* runtimes. Terminal Bench measures
coding agents on coding tasks; nothing in it measures whether a plan-marshall workflow rule survives
translation to a non-Claude target. That measurement is WS-03's to build, and this finding neither
substitutes for it nor prioritises it.

### Status

Corroboration with unverified figures attached. Decides nothing.
