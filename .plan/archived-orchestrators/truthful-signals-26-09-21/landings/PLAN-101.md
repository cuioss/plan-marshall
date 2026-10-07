# Landing Analysis: PLAN-101 — Lane router reads the wrong body

epic: truthful-signals
workstream: WS-01
pr: 1049 — merged as `83a0466d2`, 2026-07-29 10:27:40 +0000

> ⚠ **Not reported by the plan.** This landing was discovered by the orchestrator during the #1047
> reconciliation and verified against `origin/main` before recording.

## Deliverable Fidelity

Merged as *"fix(planning-lane): score actual request body, not truncated header"* — D1/D2 (the read
seam) are evidently present. ⚠ **Full per-deliverable fidelity is NOT established**: no plan report
was supplied, so D3 (counting precision) and D4 (the four pre-fix-failing tests) are **unverified**.
**Recorded as an open verification debt, not as shipped-as-specified.**

## ⛔ Post-merge PR revisit — THE RULE FIRED AGAIN, n=3 → n=4

| Event | Time |
|---|---|
| **PR merged** as `83a0466d2` | **10:27:40Z** |
| CodeRabbit posts **2 actionable inline findings** | **10:32:38–10:32:42Z** |

**~5 minutes post-merge.** Both findings are **live and untriaged in main**, and both sit in
`_cmd_planning_lane.py` — **the file this plan just changed.**

### Finding 1 — 🟠 MAJOR: the shipped doc claims a mechanism the code does not implement

> *"An unset `change_type` does not deep-bias — no mechanism backs this claim."* Both bullets state a
> missing `change_type` is treated as a deep-biasing default "per the DQ1 signal set", but in
> `evaluate_signals_pure` the predicate is
> `s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete` — `None` is not in
> `_DEEP_CHANGE_TYPES`.

⭐ **This is the epic's theme reproduced by the fix for the epic's theme.** PLAN-101 existed because
the lane router made confident claims from inputs it had not really read; it shipped **documentation
asserting a safety behaviour (unset ⇒ deep) that the predicate does not provide.**

⛔ **And it interacts directly with PLAN-112, which is IN FLIGHT.** PLAN-112 concerns the ceremony
pre-filter dropping the security audit on a **stale** `change_type`. This finding establishes that an
**unset** `change_type` does **not** bias toward `deep`. ⇒ **Both the stale and the unset cases fail
toward the NARROWER posture**, which is the direction that drops sonar-roundtrip, automatic-review
and the security audit. **PLAN-112's D2 ("fail toward inclusion") must treat `None` explicitly, and
its D1 must read this finding.**

### Finding 2 — 🟡 Minor: the title filter drops every `# Request…` heading

The docstring says the host title is *"the ONLY line removed"*; the generator filters **all** matching
lines, so an ingested spec heading is silently dropped from the scored text. Effect is conservative
(the band widens), but **the docstring is false** — doc-contract divergence in the very seam the plan
rewrote.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1049; `landing`; `plan_marshall_plan_id` — all four stamped
- [x] late-arrival recurrence advanced **n=3 → n=4**
- [x] both findings recorded as live/untriaged (owner: PLAN-102's sweep)
- [x] the `change_type` interaction relayed to PLAN-112 as a scoping input

## Follow-Ups

- ⛔ **Two live untriaged findings in main**, one Major. PLAN-102 owns the sweep; this is its third
  confirmed population source after #1036 and #1042.
- ⛔ **Verification debt**: D3 and D4 fidelity unconfirmed. Establish at the next `status`, or accept
  explicitly.
- ⚠ **PLAN-57 is now unblocked** — it shares `_cmd_planning_lane.py` with this plan, which has landed.
