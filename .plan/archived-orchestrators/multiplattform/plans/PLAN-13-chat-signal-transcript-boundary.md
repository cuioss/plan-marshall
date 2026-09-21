# PLAN-13: Transcript-format recognition lives behind the runtime, not in the retrospective

epic: multiplattform
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to close an inventory row **no** staged plan names.
> Source evidence: `../reference/coupling-inventory.md` §B row 9.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`plan-retrospective` reads raw Claude transcripts directly: `extract-chat-signal.py`,
`_chat_provenance.py` and `_chat_gate_decisions.py` know the transcript's on-disk layout, its record
shape, and Claude tool names (`OPERATOR_DECISION_TOOL='AskUserQuestion'`), and
`references/chat-history-analysis.md` teaches that format as the format. **No plan in this epic names
`plan-retrospective` anywhere in its surface**, so this survived every landed and staged plan. The
repository already contains the precedent that resolves it: metrics were normalized at the runtime
boundary — `claude_runtime` owns transcript layout, parsing, and cache weights, and `manage-metrics`
consumes a normalized shape and never parses a transcript. Apply the same boundary to chat signal.

## Deliverables

1. **D1 — The normalized chat-signal shape.** Define what a retrospective actually needs from a session transcript — operator decisions, tool-use provenance, gate decisions — as a target-neutral record, derived from what the three scripts consume rather than from what Claude's transcript happens to contain. ⛔ **Derive the shape from the consumers, not from the format**: mirroring the transcript's fields under new names reproduces the coupling with extra steps, which is the failure mode this deliverable exists to avoid. Write the derivation into the PR body and the inbox message before changing code.
   *Done when:* the PR body enumerates every field the three scripts read, the consumer need each serves, and the normalized shape that satisfies all of them; no field survives that no consumer reads.
2. **D2 — The runtime provides it.** The Claude runtime owns transcript location, parsing, and the tool-name vocabulary; a non-Claude target either provides the normalized signal from its own session record or returns an honest `no-op` with `reason` + `alternative` — never a fabricated empty result. ⛔ **An empty signal and an unavailable signal are different answers**, and a retrospective that cannot tell them apart reports "no operator decisions" over a population it never read.
   *Done when:* both runtimes answer; a test drives the non-Claude path and asserts a decline, not an empty list.
3. **D3 — The retrospective consumes the normalized shape.** `extract-chat-signal.py`, `_chat_provenance.py` and `_chat_gate_decisions.py` stop knowing the transcript format and stop naming Claude tools; `references/chat-history-analysis.md` documents the normalized signal and points at the runtime for the per-target transcript detail.
   *Done when:* no `plan-retrospective` script parses a transcript or names a Claude tool; a sweep over the skill is clean; the retrospective's own tests pass against the normalized shape.

## Out of Scope

- **`manage-metrics`** — already normalized; it is the **precedent** this plan follows, not a surface it touches. (Its *documentation* is PLAN-12's D3.)
- **Adding chat-signal capability to OpenCode** — D2 gives OpenCode an honest answer. What session record OpenCode actually keeps is a live-install question, WS-05's territory.
- **The retrospective's analysis logic** — what it concludes from the signal is unchanged; only where the signal comes from moves.
- **`platform-runtime`'s other operations** — a needed operation is added minimally and reported; the ABC's broader shape is PLAN-09's.

## Claim Labels

- OBSERVED: the three scripts are present with the described symbols — `extract-chat-signal.py`, `_chat_provenance.py`, `_chat_gate_decisions.py` (carrying `OPERATOR_DECISION_TOOL='AskUserQuestion'`) — re-derived at HEAD `2cd1a19c`.
- OBSERVED: `references/chat-history-analysis.md` is present and teaches the transcript format.
- OBSERVED: **no** plan in the epic queue names `plan-retrospective` in its Expected Surface — derived at ingestion across all eight then-staged specs. This is why the row survived. A lead: re-read the live queue before acting, in case a later plan claimed it.
- OBSERVED: the metrics precedent is real and is the shape to mirror — `claude_runtime` owns transcript layout, parsing and cache weights; `manage-metrics` consumes `{input, output, cache_read, cache_creation, total}` and never parses a transcript.
- HYPOTHESIS: the normalized chat-signal shape fits behind one new `Runtime` operation — confirm/refute at `platform-runtime/standards/contract.md` and `runtime_base.py` (verify-at-outline). ⛔ If it needs more than one, **report before adding** — the ABC's operation count is stated in `contract.md` and in other carriers, and PLAN-09 owns the ABC's shape.
- HYPOTHESIS: every field the three scripts read is recoverable by reading them — D1 settles it (verify-at-outline). ⛔ **If a field's consumer purpose is not recoverable, halt and report** rather than carrying the field forward on the assumption someone needs it; carrying an unexplained field is how a wire format survives a normalization.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py` — D1, D3
- OBSERVED: `.../plan-retrospective/scripts/_chat_provenance.py`, `_chat_gate_decisions.py` — D1, D3
- OBSERVED: `.../plan-retrospective/references/chat-history-analysis.md` — D3
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py`, `claude_runtime.py`, `_claude_runtime_impl.py`, `opencode_runtime.py`, `platform_runtime.py`, `standards/contract.md` — D2 (verify-at-outline). ⛔ **This is the one place this plan leaves its own neighbourhood.** Make the addition minimally and report it; WS-01 owns this surface.
- OBSERVED: `test/plan-marshall/plan-retrospective/**`, `test/plan-marshall/platform-runtime/**`

## Dependencies and Sequencing

- Depends on: none. **`plan-retrospective/scripts/**` is touched by no other plan in the epic**, which makes this the second fully-disjoint plan after PLAN-04.
- Overlaps with: **WS-01's plans** at the platform-runtime surface **only if** D2 needs an operation addition. ⛔ That conditional overlap is real: if PLAN-08, PLAN-09 or PLAN-14 is in flight, sequence against it rather than pairing. If no WS-01 plan is running, this plan pairs with anything.
- Concurrent with: PLAN-04, PLAN-05, PLAN-06, PLAN-07, PLAN-10, PLAN-11, PLAN-12, PLAN-16 — subject to the platform-runtime caveat above.
- **Scheduling note:** together with PLAN-04, this is one of the two plans that can fill the second slot under `parallelization_scope: 2` against almost any partner. Prefer it when the sequential lane is inside WS-02 or WS-03; prefer PLAN-04 when the sequential lane is inside WS-01.

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- **The decline pin (D2):** a test that drives the non-Claude path and asserts an honest `no-op` with `reason` + `alternative` — ⛔ **never an empty list**. This is the check the whole plan exists for.
- A sweep over `plan-retrospective/**` for transcript-format knowledge and Claude tool names, re-run at verification time.
- **A cold read of the rewritten `chat-history-analysis.md`:** a reviewer reads it without the plan in context and answers "what does a retrospective receive, and who parses the transcript?" An answer describing a transcript record shape means D3's wording failed.
- D1's derivation is a **reported deliverable**, not a working note: the PR body carries the field-to-consumer table, and a field with no named consumer is a finding.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-13-chat-signal-transcript-boundary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write, including every coupling-inventory row retirement.
