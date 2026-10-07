# PLAN-09: Every runtime operation can be declined, and the seam stops fabricating success

epic: multiplattform
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** from the PLAN-01 landing analysis and the coupling inventory's
> unclaimed §C rows. Source evidence: `landings/PLAN-01.md` § Follow-Ups,
> `../reference/coupling-inventory.md` §C rows 7–8.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

PLAN-01 made the `Runtime` contract target-opaque and its own criteria are met — but its stated
**Goal** was broader than those criteria, and the gap is real: a third-target implementer still cannot
read `runtime_base.py` alone and *decline* every operation, because four operations document no
decline vocabulary at all. Worse, one operation actively violates the no-op policy the epic exists to
uphold: `OpenCodeRuntime.metrics_capture` reports `success` while persisting nothing. Close the
Goal-versus-criteria gap: give every operation a decline path, stop the one fabricated success,
eliminate the residual target enumeration inside a concrete runtime, make registration
single-sourced rather than lockstep-checked, and stop `platform-runtime/SKILL.md` re-asserting the
per-target coupling PLAN-01 removed from the ABC one file over.

## Deliverables

1. **D1 — Decline vocabulary for every operation.** `project_initial_setup` and `health_check` state `Returns: … (success or error)` only; `layout_skill_roots` and `layout_bundle_cache_root` state no status vocabulary at all. Give all four the same `no-op` + `reason` + `alternative` shape the rest of the ABC carries, and state it in `contract.md`.
   **FOLDED IN (PLAN-01 landing, unowned until now) — `health_check`'s `permissions` check names a file it did not check.** While this deliverable already has `health_check` open: `_claude_runtime_impl.py::health_check` resolves the settings path via `_claude_project_settings_path()`, which **prefers `.claude/settings.json`**, but the check's `details` string hardcodes the literal `settings.local.json`. A project holding only `settings.json` is therefore told to look at a file that does not exist. Operator-consequential and pre-existing — not introduced by PLAN-01, which found it. Report the path actually resolved rather than a literal.
   *Done when:* every one of the ABC's operations documents how a target declines it, verified by deriving the operation population from the ABC itself (with a non-vacuity guard) rather than from a restated list; **and `health_check`'s `permissions` details names the settings file it actually resolved, with a case covering a `settings.json`-only project.**
2. **D2 — `metrics_capture` stops fabricating success.** `OpenCodeRuntime.metrics_capture` returns `toon_success` with `tokens_captured` for an explicit `--total-tokens` while calling no persistence boundary; the only write path (`_write_token_cursor` / `_manage_metrics_end_phase`) lives in the Claude runtime. Either relocate the persistence behind a shared, target-neutral boundary both runtimes reach, **or** make OpenCode decline honestly — and say which, with the reason, in the PR body.
   *Done when:* no runtime reports success for metrics work it did not perform; a test drives OpenCode's `metrics_capture` and asserts either persistence happened or an honest `no-op` came back — never a bare success.
3. **D3 — The residual target enumeration goes.** `_claude_runtime_impl.py:51` hardcodes `"valid targets are: claude, opencode"` inside a concrete runtime while the router derives the identical message from `_REGISTRY` (`platform_runtime.py:734`). Consume the router's derivation.
   *Done when:* no concrete runtime enumerates the registered target set; a red-first test adds a fake target to the registry and asserts the message names it.
4. **D4 — Registration is single-sourced, not lockstep-checked.** `_REGISTRY`, `_TARGET_BOOTSTRAP_LIBS`, `_DEFAULT_TARGET` (`platform_runtime.py`) and `_DEFAULT_RUNTIME_TARGET` (`marketplace_paths.py`) are four independent definitions across two files; the existing lockstep tests detect drift *after the fact*. Build one registration record per target owning its class and bootstrap libs, with every view derived from it.
   *Done when:* adding a target requires editing exactly one record; the existing lockstep tests still pass and are re-expressed as derivations rather than comparisons.
5. **D5 — `platform-runtime/SKILL.md` stops restating per-target status.** The operation table restates each operation's per-target no-op status ("no-op on OpenCode" and Claude-specific parentheticals) — the same coupling PLAN-01 removed from the ABC docstrings, recurring one file over. Source it from the runtime or state it as a per-target note.
   *Done when:* the SKILL.md carries no per-target status assertion the ABC itself does not; a sweep for the pattern over the file is clean.

## Out of Scope

- **The permission operations' argument grammar** — PLAN-08's D2 surface. If PLAN-08 has not landed, D1's decline vocabulary still applies to the permission ops; coordinate by re-deriving, never by editing PLAN-08's symbols.
- **`marketplace_paths.py`'s fallback-composer constants** — PLAN-10's surface. D4 touches `_DEFAULT_RUNTIME_TARGET` only.
- **Renaming or relocating `HARNESS_BASH_CEILING_SECONDS`** — PLAN-10's surface.

## Claim Labels

- OBSERVED: four operations document no decline vocabulary — `project_initial_setup`, `health_check`, `layout_skill_roots`, `layout_bundle_cache_root`. ⚠️ **The line numbers this claim used to cite (155–157, 935–937, 253–256, 277–282) are STALE** — PLAN-13 (PR #1376) grew `runtime_base.py` by ~69 lines and every one of them now points at unrelated content (935 lands inside PLAN-13's own new chat-signal docstring). Re-derived at `bccca692c`: `project_initial_setup` **194**, `layout_skill_roots` **284**, `layout_bundle_cache_root` **310**, `health_check` **1046**. **Substance re-checked and it HOLDS:** none of the four carries the full `no-op` + `reason` + `alternative` shape (two mention a no-op; none states `reason` or `alternative`). ⛔ Locate these by SYMBOL, not by line — the numbers above are already one landing away from rotting again.
  - verdict: corroborated | checked_at: bccca692c | by: multiplattform/analyze | rescoped: n/a | evidence: Substance HOLDS at bccca692c: none of project_initial_setup, health_check, layout_skill_roots, layout_bundle_cache_root documents the full no-op + reason + alternative shape (two mention a no-op; none states reason or alternative), so D1 is still needed. The claim's LINE-NUMBER evidence was stale - PLAN-13 grew runtime_base.py ~69 lines and all four cited ranges pointed at unrelated content. Re-derived to 194 / 1046 / 284 / 310 and the claim now instructs symbol-based location.
- OBSERVED: `OpenCodeRuntime.metrics_capture` returns success without persisting — read at `opencode_runtime.py` lines 447–487, which returns `toon_success` with `tokens_captured` and calls no persistence boundary; the only write path is `claude_runtime.py` lines 1652–1674. The ABC docstring (`runtime_base.py` 689–696) already documents this as a "known violation," which is disclosure, not remedy.
- OBSERVED: `_claude_runtime_impl.py:51` hardcodes the target list while `platform_runtime.py:734` derives it from `_REGISTRY`.
- OBSERVED: registration is four independent definitions across two files — `platform_runtime.py` 177–200 and `marketplace_paths.py:119`; `test_target_registration_lockstep.py` compares them rather than deriving them.
- OBSERVED: `platform-runtime/SKILL.md` carries **8** occurrences of the "no-op on OpenCode" pattern plus Claude-specific parentheticals and a frontmatter naming both targets. Count is a lead — re-derive before D5.
- OBSERVED: the `Runtime` ABC carries **25** `@abstractmethod` operations, re-derived at `bccca692c`. ⚠️ **Was 24 at HEAD `2cd1a19c`; the PLAN-13 landing (PR #1376) added the chat-signal operation.** Still a lead; **D1 and D2 may change it again**, and `contract.md` states the figure — update it there and report the new number.
  - verdict: contradicted | checked_at: bccca692c | by: multiplattform/analyze | rescoped: yes | evidence: Op count moved 24 -> 25 at the PLAN-13 landing (PR #1376), which added the chat-signal operation to the Runtime ABC. Re-derived at bccca692c: 25 @abstractmethod in runtime_base.py. Spec text updated to 25 in the same act. Kept as a lead: this plan's own D1/D2 may move it again.
- HYPOTHESIS: D2's persistence relocation fits without a new operation — confirm/refute at `runtime_base.py` and `contract.md` (verify-at-outline). If a new operation is genuinely needed, record it and add it minimally rather than widening an existing signature to carry a target's shape.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py` — D1, D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — D1, D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`, `_claude_runtime_impl.py` — D2, D3
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — D3, D4
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — D1, D2
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/SKILL.md` — D5
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py` — D4, **`_DEFAULT_RUNTIME_TARGET` only**
- OBSERVED: `test/plan-marshall/platform-runtime/**`, `test/plan-marshall/script-shared/**`

## Dependencies and Sequencing

- Depends on: **PLAN-08**. Run after it. Both edit the same runtime scripts and `contract.md`, and PLAN-08's D2 may change the permission operations' signatures — which D1 then documents a decline path for. Running this first would make PLAN-08 re-document what D1 just wrote.
- Overlaps with: **PLAN-01** (landed), **PLAN-08**, **PLAN-14** on `platform-runtime/scripts/**`; **PLAN-06** and **PLAN-07** conditionally on `contract.md`; **PLAN-07** on `marketplace_paths.py` (different symbols); **PLAN-10** on `marketplace_paths.py` (different symbols again). ⛔ **Not concurrent with any of them.**
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- Red-first tests for D2 (the fabricated-success pin), D3 (the fake-target message), and D4 (the derivation).
- **Population-derived, not restated:** D1's completeness check enumerates the ABC's operations at test time and asserts each documents a decline path — with a non-vacuity guard so an empty population cannot pass. This is the same discipline PLAN-08's verification uses, and for the same reason.
- A cold read of the four newly-documented operations: a reviewer reads them without the plan in context and answers, for each, "what does a target that cannot do this return?" Any answer other than the no-op shape means the wording failed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-09-runtime-seam-completeness.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write, including every coupling-inventory row retirement.
