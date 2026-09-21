# WS-05: OpenCode is a validated runtime, not best-effort output

epic: multiplattform

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-live-validation.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own everything that cannot be settled without a real OpenCode install. **OpenCode has never executed
a plan-marshall workflow live.** The runtime answers every operation and the emitter produces a
complete tree, but the behaviours the design assumes — subagent user-prompting, `task`-tool dispatch,
`skill`-tool loading, parallel dispatch, instruction retention — are unobserved. The workstream
closes when the protocol has run against a live install and the facts it confirmed are documented as
facts rather than assumptions.

⛔ **RESOLVED VIA SIBLING EPIC, 2026-09-15 — not by a plan run from this workstream.** The premise
above ("never executed... live") is now FALSE for the consumption-path half of the protocol:
`tooling-truthfulness/PLAN-07-opencode-install-docs.md` (PR #1484, shipped 2026-09-13) ran the
protocol's candidate-path test against a live OpenCode 1.18.30 install and shipped install
documentation. This was a deliberate, operator-accepted cross-epic duplication (see that epic's
2026-09-11 Decisions entry), not an accident. PLAN-17's D1/D2 and PLAN-18's D1/D4 are discharged by
it; PLAN-18's D2 (per-operation orientation layer) and D3 (confirmed limitations) are NOT — see the
discharge notes on each spec. The epic is closing with both plans left `parked` and this residual
recorded as accepted, deferred scope rather than run. See `epic.md` Decisions for the full record and
the corroborating evidence (landing report, `corpus cross-check` collision rows).

## Scope

- **In scope:** running `reference/opencode-validation-protocol.md` against a live install; pinning the install path against the published `dist-opencode` refs; the OpenCode user documentation and its confirmed limitations; upgrading the validation framing in the developer and repo-root multi-assistant documentation.
- **Out of scope:** every behaviour that can be confirmed without an install — those are WS-01 through WS-04's plans, none of which may block on this workstream. Deciding what permission semantics OpenCode *should* have is likewise here, not in WS-01.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-17-pin-opencode-install-path | parked | Blocked on the protocol. Which consumption path works against `dist-opencode` / `opencode/v*` is unverified on a live client. |
| PLAN-18-opencode-user-documentation | parked | Blocked on PLAN-17. The verified install path, the per-operation behaviour orientation layer, the confirmed limitations, and the validated-runtime framing upgrade. |

## Sequencing and Surface Notes

- ⛔ **Both plans are `parked`, not `staged`, and the `next` verb must never emit either of them.** The gate is not a predecessor plan — it is an operator with a live OpenCode install at an interactive terminal. The cloud plan lane cannot provide one, and no amount of ledger state changes that.
- **The protocol itself is not a plan.** It is an operator-run runbook (`reference/opencode-validation-protocol.md`) with exact commands, expected observations, and pass/fail criteria. It is carried as a Watch on the epic, not as a queue row, because staging a row for work the orchestrator can never emit would misrepresent the queue.
- **Unparking sequence, so a resuming session does not have to re-derive it:** the operator confirms an install exists → the operator runs the protocol → the orchestrator `analyze`s the protocol's observations → PLAN-17 moves `parked` → `staged` and is re-grounded against whatever the protocol actually found → PLAN-18 follows PLAN-17.
- PLAN-17's outcome may **refute** a premise elsewhere in the epic. The known one: PLAN-04's plural-directory assumption (protocol § 1.2). A refutation there is a re-scope of PLAN-04's D1, not a defect in it.
- Coupling-inventory §C row 1 (`persona-plan-marshall-agent`'s tool-usage vocabulary) is deliberately gated on this workstream and is correctly unclaimed by any WS-01–WS-04 plan. It is not an oversight; it graduates to a plan once the protocol says whether a rewrite is needed at all.
