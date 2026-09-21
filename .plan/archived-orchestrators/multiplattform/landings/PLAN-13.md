# Landing Analysis: PLAN-13 — Move chat-signal parsing to the runtime boundary

epic: multiplattform
workstream: WS-03
pr: [#1376](https://github.com/cuioss/plan-marshall/pull/1376) — merged as `bccca692c8bea258966f848a00beabde14177ba8`

> Landing record for one shipped plan. Claims corroborated against the merged diff, PR state and the
> current tree. This is the **largest** landing in the epic so far (32 files, +2249/−1648) and the
> first to change the `Runtime` ABC's operation count — which invalidated a premise in two other
> staged specs. That cross-plan reconciliation is the substance of this record.

## Deliverable Fidelity vs Spec

The plan moved chat-signal parsing from `plan-retrospective`'s script into the `platform-runtime`
boundary: `extract-chat-signal.py` shrank from a parser to a consumer (−381 lines of its old body), a
new `_chat_signal_reducer.py` (+284) carries the reduction, and the ABC gained a chat-signal
operation implemented on both runtimes with an honest OpenCode decline.

| Area | Verdict | Evidence |
|---|---|---|
| Parsing relocated to the runtime boundary | shipped | `extract-chat-signal.py` −381; `_chat_signal_reducer.py` +284; `runtime_base.py` +69; `contract.md` +74 |
| Both runtimes implement the operation | shipped | `_claude_runtime_impl.py` +56, `opencode_runtime.py` +28 — the decline is stated, not faked |
| Test surface rebuilt around the new seam | shipped | 3 new test modules (`..._chat_signal_op.py`, `..._chat_signal_record.py`, `..._chat_signal_reducer.py`, +963 combined) plus fixture relocation |

**Realized surface: 32 files.** The declared surface named `chat-history-analysis.md`, `_chat_provenance.py`, `extract-chat-signal.py`, `runtime_base.py`, `standards/contract.md` and the `test/plan-marshall/platform-runtime/**` glob. The additional runtime files (`_chat_signal_reducer.py`, `_claude_runtime_impl.py`, `opencode_runtime.py`, `platform_runtime.py`, `claude_runtime.py`, `_chat_gate_decisions.py`) sit inside the same seam the plan was chartered to move and are ordinary under-declaration of a relocation's blast radius — not scope drift.

## Metrics and Anomalies

- **Tokens: unavailable** — OpenCode lane, no `manage-metrics` record. Not estimated.
- **Branch form `feature/`** — correct, and the first in this epic to warrant it: a new capability rather than a fix or chore.
- **Two review-driven commits**, both corroborated present: `86e4f0a20` (CodeRabbit findings) and `3a209f61f` (verifier's condition-A survivor).
- **Anomalies:** none in the deliverables.

## Routing and Merge Behavior

- **Review:** CodeRabbit findings applied in `86e4f0a20` — `FileNotFoundError` → `transcript_not_found` (**mutation-verified**, the strongest form of evidence for an error-path change), `OPERATOR_DECISION_TOOL` derivation, the 24→25 guard, a strengthened no-op E2E test, and a hoisted `run_consumer` fixture. The pr-agent thread was replied to and resolved; CodeRabbit obtained.
- **The verifier earned its place this run.** It caught a **condition-A survivor** the review did not: three stale *"24 operations"* docstrings left behind when the count changed — fixed in `3a209f61f`, which also pinned the session-id hop with a distinct value. Verified here: **zero** `24 operations` / `24 @abstractmethod` strings remain under `platform-runtime/`. This is the sweep-and-count discipline working — a count changed in one place and survived in three others, which is exactly the failure a partial edit produces.

## Cross-Plan Reconciliation — the ABC operation count moved 24 → 25

This landing added an operation to the `Runtime` ABC. Re-derived at `bccca692c`: **25** `@abstractmethod`, **7** `permission_*` (unchanged), and `permission_fix.py` still **12** `cmd_*` — so exactly one of the three tracked counts moved. Two staged specs asserted 24, and both were re-scoped **in the same act** as their verdicts were stamped:

| Spec | Claim | Action |
|---|---|---|
| **PLAN-08** claim 7 | "the ABC carries exactly **24** … " — carried a **corroborated** verdict at `2cd1a19c` | text → 25; verdict re-stamped `contradicted` / `rescoped: yes` at `bccca692c` |
| **PLAN-09** claim 5 | "the ABC carries **24** … at HEAD `2cd1a19c`" — no verdict | text → 25; verdict stamped `contradicted` / `rescoped: yes` |

⚠️ **PLAN-08 anticipated this change and named the wrong plan.** Its own text warned *"PLAN-09 may change the op count; if it lands first, re-derive rather than trusting 24."* The instinct was right, the attribution wrong — **PLAN-13** moved it. The lesson is the one the spec already stated and is worth keeping: re-derive the number, never trust the prediction of who will change it.

`blocking_count` remains **0** after both stamps — `contradicted` + `rescoped: yes` admits, so neither plan is blocked.

### A second, quieter drift caught in the same pass

**PLAN-09 claim 0's line numbers had all four rotted.** It cited `runtime_base.py` lines 155–157, 935–937, 253–256, 277–282 for the four operations lacking decline vocabulary. This landing grew that file by ~69 lines and **every one of those ranges now points at unrelated content** — 935 lands inside PLAN-13's own new chat-signal docstring, which would have sent a run reading the very operation it was not looking for.

**The substance was re-checked and it holds:** none of `project_initial_setup`, `health_check`, `layout_skill_roots`, `layout_bundle_cache_root` documents the full `no-op` + `reason` + `alternative` shape (two mention a no-op; none states `reason` or `alternative`), so PLAN-09 D1 is still needed. Verdict stamped `corroborated`, line numbers re-derived (194 / 1046 / 284 / 310), and the claim now instructs locating by **symbol, not line** — because those numbers are one landing away from rotting again.

## Reconciliation Actions

- [x] row `status` → `landed`; `pr` `#1376`; `landing` `landings/PLAN-13.md`; `plan_marshall_plan_id` `n/a`
- [x] PLAN-08 claim 7 re-scoped 24→25 and verdict re-stamped `contradicted` / `rescoped: yes`
- [x] PLAN-09 claim 5 re-scoped 24→25 and verdict stamped `contradicted` / `rescoped: yes`
- [x] PLAN-09 claim 0 line numbers re-derived; verdict stamped `corroborated`
- [x] verified `blocking_count: 0` after all three stamps — no spec blocked
- [x] epic.md reconciled; both generated blocks regenerated; `resume_anchor` updated

## Follow-Ups

- **PLAN-08 and PLAN-09 now carry a shared, freshly-measured dependency on the same figure.** Both restate the op count, and both may move it again (PLAN-09's D1/D2 explicitly). Neither should trust the other's number: re-derive at execution. This is the third time this count has been a source of drift.
- **The `runtime_base.py` line-number citation pattern is a recurring hazard.** PLAN-09 was not the only spec authored with line-anchored evidence into a file under active change. ⚠️ Worth a corpus-wide check at the next `cleanup`: any claim citing `runtime_base.py` line numbers predating `bccca692c` is presumptively stale.
- **The declared-surface gap widened again.** 32 files realized against 6 declared entries. PLAN-04 under-declared by 3 of 7; this plan by considerably more. Both are *relocations*, where the blast radius is inherently hard to pre-state — but the epic's disjointness gate reads declarations, so this is the residual the ledger already names as the weak link now that the parser is fixed.
