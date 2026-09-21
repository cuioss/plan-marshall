# Landing Analysis: PLAN-CIS-007 — Skill LSP server

epic: code-intelligence-substrate
workstream: WS-03
pr: 1256
merge_commit: `5edca5a85`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/240-skill-lsp-server/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**partial** — 5 of 6 deliverables shipped; D3 unbuilt. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The corpus LSP server genuinely works when driven for real — definition, hover and references all answer correctly through a live `serve` subprocess against the real corpus. But it has **no exception boundary around JSON-RPC dispatch**: one malformed request kills the resident server *and* writes TOON error text onto the LSP stdout stream. And the `verified` provenance flag is silently dropped at the LSP projection, so **162 unconfirmed reference sites reach an editor as ordinary exact Locations**, contradicting two shipped documents' explicit promise.

## Premise verdict

D0(a)'s asserted absence was **partially refuted** — generic Markdown LSP servers now exist, though none understands this corpus's notation. That surfaced a NEW fact (Claude Code's native `lspServers` plugin-manifest support) which reframed the protocol decision mid-run, needed two rounds of operator escalation, and landed on *document, don't ship* — because a shipped manifest declaration would silently hijack a user's own `.md` LSP server on plugin-enable.

## Gaps carried out of this landing

**28 total — 2 high, 9 medium, 17 low.** High: G1, G28.

- **No exception boundary around JSON-RPC dispatch** (G1, high) — any handler exception kills the resident server and corrupts the stdout protocol stream. Residency is this surface's entire value proposition, so this is critical.
- **The `verified` provenance flag is computed correctly by the index and silently dropped at the protocol layer** (G28, high) — false-confident jumps reach the editor.
- ⛔ **D3's deferral justification is now stale AND inverted.** Its hard gate (PLAN-CIS-006) landed on main **74 minutes before this plan merged**, so every doc site explaining *why diagnostics are withheld* cites a ~97%-false-positive figure against a validator now at 61/5081 — the share has **inverted to ~41%**. Nine of the 28 gaps are this one landing-order accident. **Re-take the decision; do not merely fix the numbers.**

## Inconsistencies found, and what was verified

- Self-reported round-4 finding: "the sys.path bootstrap works identically in a deployed plugin cache" | verified by driving `serve` against a synthetic versioned plugin-cache layout | **verdict: false** — three prior verification rounds and 75 passing tests only ever exercised the flat source tree; the bootstrap crashed with `ModuleNotFoundError` in every installed project until round 4 fixed it.

## Residue

The surface has no automatic consumer, by decision — the same zero-adoption shape this epic already hit once (PLAN-CIS-002 -> PLAN-CIS-046), reduced but not prevented.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-007 --status shipped`
- [x] row `pr` stamped `1256` — `orchestrator queue --set-row PLAN-CIS-007 --field pr --value 1256`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-007 --field landing --value landings/PLAN-CIS-007.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**A decision-reversal candidate, not a doc fix**: D3 (live diagnostics) should be re-triaged now that the false-positive share has inverted. Recorded as an Open Decision in `epic.md`. G1/G28 route to **PLAN-CIS-048** (`500`).
