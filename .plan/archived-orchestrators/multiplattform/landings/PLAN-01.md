# Landing Analysis: PLAN-01 — Runtime seam neutrality

epic: multiplattform
workstream: WS-01
pr: #1291 (squash `2c8b5b1c`, "refactor(platform-runtime): make the Runtime contract target-opaque and register targets in one place")

> Landing record for one shipped plan. Lives at `landings/PLAN-01.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Ingestion note.** This plan shipped in the standalone `doc/plans/multiplattform/` lane before
this epic ledger existed. This record was written at ingestion from a ground-truth verification
against HEAD `2cd1a19c` — the run report (`report-01.md`, 491 lines, archived at
`archive/010-runtime-seam-neutrality/`) was treated as a claim set, and every deliverable was
re-derived from the implementing source.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Target-opaque `project install-hook` | shipped-as-specified | `runtime_base.py::Runtime.project_install_hook` (lines 159–226) carries zero Claude vocabulary — no hook-event names, no `CLAUDE_CODE_*`, no settings path; parameter is `overwrite: Sequence[str] = ()`, a target-defined key set with a reject-not-ignore contract. `_claude_runtime_impl.py::ClaudeRuntime.project_install_hook` (117–287) holds `_OVERWRITE_KEYS = ("statusline", "env-disable")` and rejects unknown keys with `unknown_overwrite_key` **before any write** (189–197). `contract.md` § `project install-hook` (101–133) matches. Tests assert `unknown_overwrite_key` in `test__claude_runtime_impl.py`, `test_claude_runtime.py`, `test_platform_runtime_router.py`. |
| D2 — Target-neutral ABC docstrings | shipped-as-specified | Whole-file read of `runtime_base.py` (938 lines): zero occurrences of `On Claude`, `On OpenCode`, or any casing of `claude`/`opencode`. Displaced notes verified present in the concrete classes — `claude_runtime.py::_claude_event_to_process_state` (388–416), `_DISPLAY_RENDER_ENTRIES`, `_install_terminal_title_hooks`; `opencode_runtime.py` module docstring (6–24). |
| D3 — Registration consolidated | shipped-as-specified, plus one addition beyond the stated done-when | `platform_runtime.py` 177–200 declares `_DEFAULT_TARGET`, `_REGISTRY`, `_TARGET_BOOTSTRAP_LIBS` in one adjacent block; all three argparse defaults plus the bare fallback read `_DEFAULT_TARGET` (281, 683, 701, 707). `marketplace_paths.py:119` holds a single `_DEFAULT_RUNTIME_TARGET`. `test_target_registration_lockstep.py` asserts both named invariants plus four more. **Beyond done-when:** `marketplace_paths._invoke_layout_op` (193–235) now resolves the runtime class through `platform_runtime._make_runtime(target)`; no local `if target == 'opencode'` branch remains. |
| D4 — Parameterized OpenCode dispatch | shipped-as-specified | `opencode_runtime.py::subagent_dispatch` (522–569) sets `"subagent_type": agent`; the literal `execution-context-level-3` appears nowhere in the file. `test_opencode_runtime.py::test_subagent_dispatch_echoes_requested_agent` (526–542) is parametrized over two levels. |

**Cross-cutting re-derivations.** `Runtime` ABC `@abstractmethod` count re-derived as **24**, matching
the plan's figure. No Claude literal in the ABC or the router outside the sanctioned registration
block. `contract.md` agrees with the code shape (arguments, error codes, disposition vocabulary).

**Descoped: none.** No deliverable in `plan.md` is absent, deferred, or renamed in `report-01.md`.
Two items landed **beyond** the Expected surface, both flagged in the report rather than absorbed
silently: the coupling-inventory `§ Closing a row` convention and its application (operator-directed),
and the `_invoke_layout_op` router-mediated class resolution noted above.

## Metrics and Anomalies

- Tokens: not available — the run executed in the standalone cloud plan lane, which produces no
  `metrics.toon`. The run report carries sub-agent self-reports only.
- Duration: not instrumented in that lane.
- Anomalies: none affecting fidelity. The plan's stated **Goal** is broader than D2's completion
  criteria — see Follow-Ups.

## Routing and Merge Behavior

- Review: CodeRabbit raised the four-independent-definitions observation on PR #1291 (registration
  is lockstep-*checked*, not lockstep-*impossible*); recorded rather than fixed in-plan.
- CI/merge: merged as squash `2c8b5b1c`. No rebase conflicts recorded; no surface collision observed
  with any concurrent plan (none ran concurrently in the standalone lane).

## Reconciliation Actions

- [x] row `status` → `landed` — seeded at `decompose` (ingestion), not transitioned from `staged`
- [x] row `pr` stamped — `#1291`
- [x] row `landing` stamped — `landings/PLAN-01.md`
- [x] row `plan_marshall_plan_id` — `n/a` (standalone lane; no plan-marshall plan id was ever created)
- [x] epic.md queue reconciled from status.json
- [x] Open Defects opened for the six residual gaps below
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

Six residual gaps, all re-derived at HEAD `2cd1a19c` and none of them a landing failure — five are
disclosed in the run report itself, and the sixth is a reviewer observation recorded there.

1. **Four `Runtime` operations document no way to decline.** `project_initial_setup` and
   `health_check` state `Returns: … (success or error)` only; `layout_skill_roots` and
   `layout_bundle_cache_root` state no status vocabulary at all (`runtime_base.py` 155–157, 935–937,
   253–256, 277–282). This is the concrete mechanism behind the Goal-vs-criteria gap: a third target
   with nothing to implement these four has no decline path to point at. → **PLAN-09** (new).
2. **`OpenCodeRuntime.metrics_capture` reports `success` while persisting nothing** for an explicit
   `--total-tokens` (`opencode_runtime.py` 447–487 returns `toon_success` with `tokens_captured` and
   calls no persistence boundary; `claude_runtime.py` 1652–1674 owns the only write path). The ABC
   docstring (689–696) now documents this as a "known violation" — the relocation to a shared
   target-neutral persistence boundary is not done. → **PLAN-09** (new).
3. **`platform-runtime/SKILL.md` carries the same coupling D2 removed from the ABC, one file over** —
   8 hits of "no-op on OpenCode" plus Claude-specific parentheticals and a frontmatter naming both
   targets. Out of D2's declared surface, so not a defect; live undone work of the same class.
   → folded into **PLAN-07** (WS-03 owns bundle prose).
4. **`health_check`'s `permissions` check names a file it did not check** —
   `_claude_runtime_impl.py::health_check` resolves `_claude_project_settings_path()` (prefers
   `.claude/settings.json`) but hardcodes the literal `settings.local.json` in the check's `details`.
   Pre-existing, operator-consequential (misdirects to a nonexistent file). → **Open Defect**.
5. **`_claude_runtime_impl.py:51` hardcodes `"valid targets are: claude, opencode"`** while the router
   derives the identical message from `_REGISTRY` (`platform_runtime.py:734`). A residual target
   enumeration relocated rather than eliminated. → **PLAN-09** (new).
6. **Registration is lockstep-checked, not lockstep-impossible** — `_REGISTRY`,
   `_TARGET_BOOTSTRAP_LIBS`, `_DEFAULT_TARGET` and `_DEFAULT_RUNTIME_TARGET` remain four independent
   definitions across two files; the tests detect drift after the fact. A single registration record
   owning class + bootstrap libs, with every view derived, is not built. → **PLAN-09** (new).
