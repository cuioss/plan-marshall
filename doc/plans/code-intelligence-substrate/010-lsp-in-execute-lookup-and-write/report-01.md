# Run report — 010-lsp-in-execute-lookup-and-write (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/lsp-execute-lookup-write-43d0ar` (harness-assigned; kept as-is per lane contract)    **PR:** _pending_    **Outcome:** in progress

## Skills loaded

Loaded by reading the bundle source path (the plugin was not assumed present in this cloud session):

- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `cloud-plan-lane` (the working contract, loaded first)

Conditional loads deferred until code is written (persona-implementer, python-core, pytest-testing, plugin-architecture, ref-asciidoc read on demand). Recorded per the contract; none was unobtainable.

## D0 — GATE (settled against a live server, not documentation)

**Outcome: CONFIRMED.** A real language server — `pyright-langserver` 1.1.408 (installed at `/root/.local/bin`, via `uv` tools) — was driven over LSP/JSON-RPC (stdio) by a stdlib-only client. No hand-built stand-in was substituted (the plan forbids that on refutation; it is equally avoided on confirmation).

Measurement (workspace scoped to the `manage-architecture` module — a representative task working set):

| Operation | Latency | Result |
|---|---|---|
| Cold start (`initialize`) | **413.4 ms** | server ready |
| `workspace/symbol` (query "run") | 240.6 ms | 0 (pyright needs indexing enabled / config-pull answered — handled in the real client) |
| first `publishDiagnostics` | 736.3 ms | 5 diagnostics |
| `textDocument/documentSymbol` | **2.7 ms** | 10 symbols (coordinates, no bodies) |
| `textDocument/references` | **11.9 ms** | 3 locations |
| `textDocument/definition` | **2.6 ms** | 1 location |
| `textDocument/rename` → `WorkspaceEdit` | **4.9 ms** | **multi-file edit spanning 2 files** |

The rename produced a real, parser-verified, **multi-file `WorkspaceEdit` in under 5 ms** — D2's central primitive, verified against a real server. Diagnostics are available in under a second — D3's primitive. Coordinate lookups are single-digit-to-low-tens of milliseconds.

**Premise refuted?** No. The standing objection (per-query server boot is not viable for one-shot subprocesses) is answered by the measurement: cold start is ~0.4 s, so the natural amortization unit is a **per-call batch** (a single script invocation that boots the server, runs a batch of lookups and/or an edit+re-diagnose, and tears down).

### Hosting decision (D0's second half)

**Decision: host the server _inside the envelope_ — a short-lived subprocess of the client script (per call), not a daemon and not a socket-exposed sidecar.**

Rationale:
- Cold start ~0.4 s makes per-call boot cheap; the value is in the per-call latencies (2–12 ms) and the multi-file `WorkspaceEdit`, not in cross-turn warmth.
- Avoids widening `marshalld`'s machine-global trust boundary. The build-server map shows `marshalld` is one-op-per-connection request/reply — a poor structural fit for a long-lived stateful LSP session — and the plan flags an LSP holding an open workspace as "a new class of long-lived child" whose adoption into the daemon would be an explicit, high-risk recorded decision. Hosting per-call sidesteps that entirely.
- Avoids the unestablished risk (claim label) that a dispatched leaf can hold or reach a long-lived process across turns: a per-call subprocess lives and dies inside one `Bash`→script call, which the leaf tool surface trivially supports.
- Matches the shipped build-skill shape (spawn a subprocess, suspend the LLM, return one TOON; cost independent of duration / file count) — the same shape the plan's OBSERVED token-management claim names.

## Split decision (the split guard)

**Decision: proceed UNSPLIT (D0+D1+D2+D3+D4 in one PR).**

Rationale: the in-envelope host decision collapses D1 (read) and D2 (write) onto one shared client core (spawn → initialize → request), so a lookup/write split would fork the same scaffolding across two PRs and duplicate the config-surface review. D2 is a thin, high-value addition over D1 (rename → capture footprint → apply → re-diagnose), and its adversarial test is cheap to include alongside the read side.

## Deliverables

_(filled in as implemented)_

## Build gate

_(filled in at Step 5)_

## Findings

_(filled in from the verification sub-agent, CI, and PR review)_

## Reviewer participation

_(filled in at Step 7/8)_

## Cost

_(filled in at close)_

## Contract check (Step 9)

_(filled in at Step 9)_

## What have we learned (Step 9)

_(filled in at Step 9)_

## Residue

_(filled in at close)_
