envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=finding
created=2026-08-30T20:37:35Z

# PLAN-145 — D1 refutes the missing-seam premise; PLAN-150 is not blocked

PLAN-145 is **parked at the 3-outline review gate** by operator decision, before task
creation. It has not landed and has no PR. This message files the one result that
must not wait for a landing, because two epic sequencing decisions rest on it.

## 1. D2 is empty — the gap PLAN-145 exists to close does not exist

D1's tree-wide re-derivation (the sweep PLAN-090 declined) was run at outline time
against HEAD using the real `conftest.parse_ns`, not inferred:

| Figure | Value |
|--------|-------|
| Entry-point scripts in `marketplace/bundles/**` | 118 |
| Reach a parser seam | 113 (27 via a published zero-arg builder, 86 via `main()` interception) |
| Raise `ParserSeamNotFound` | 5 |
| **Owed a `build_parser()` seam** | **0** |
| **`parse_ns` call sites unblocked** | **0** |

All 5 raising scripts are deliberate shapes, not gaps:

- `platform_runtime.py` — dispatch router; the raise is already pinned as the
  *intended* contract by a passing test,
  `test/test_shared_harness.py::test_a_router_script_fails_loudly_rather_than_yielding_a_guess`.
  Publishing a seam here would break that test.
- `claude_hook.py`, `claude_pretooluse_capture.py`, `claude_pretooluse_hook.py` —
  stdin-driven hook entry points with no argv contract.
- `plan_logging.py` — import-only library.

## 2. Consequence for PLAN-150 — re-sequence it

PLAN-145's spec states PLAN-150 depends on it because *"PLAN-150's ~506-site
conversion cannot reach the sites these seams block."* **Those seams block zero
sites.** PLAN-150 is therefore **not blocked by PLAN-145** and can be staged
independently. The D4 figure PLAN-150 was to be sized from is `0`.

## 3. Consequence for concurrency — a slot is free

The epic recorded R=2 of `parallelization_scope=2` with PLAN-145 and PLAN-170 both
running. PLAN-145 is parked and doing no work, so **one slot is effectively free**.
The queue row still reads `running`; the orchestrator owns that row and should
decide whether to re-stamp it. Note the standing constraint is unchanged: PLAN-165
still collides with PLAN-145's tree, so it is only a safe filler while PLAN-145
stays parked, and pairing them on resume remains forbidden.

## 4. Stale premises corrected in this plan's own spec

Two spec claims were verified wrong at HEAD and corrected during refine/outline.
Both originate from PLAN-070's report, which routed "no seam" and "no CLI" to the
same remedy:

- D2's two named starting points — `effort_presets.py`, `manage_terminal_title.py` —
  publish no CLI, no argparse and no `main()` at all. That is D1's fourth class
  (no top-level CLI script), not `ParserSeamNotFound`.
- D3's three named no-CLI directories are all stale: `manage-lifecycle` and
  `q-gate-validation-agent` are test-directory names with no skill behind them (the
  real code is `manage-status.py`, which ships a full CLI), and `build-server` has
  split into `manage-build-server` + `build-server-client`, both already shipping
  argparse CLIs.

A derived enumeration of the no-CLI class (skills shipping no entry point) returns
**5 modules across 4 skills**, not the 2 the spec transcribed:
`manage_terminal_title.py`, `toon_parser.py`, `input_validation.py`,
`schema_validation.py`, `doc_references.py`. `effort_presets.py` is **not** in the
class — its skill ships `phase_handshake.py` as an entry point.

## 5. What remains in PLAN-145 if resumed

One deliverable, entirely additive, nothing under `marketplace/bundles/` modified:
a tree-wide seam-coverage guard (`test/test_parser_seam_coverage.py` plus one
`_ROUTING_GUARD_MODULES` row in `test/conftest.py`) that re-derives the census on
every run and carries the 10 D3 shape verdicts as two asserted rosters. Measured
cost: 0.3 s to probe all 113 seam-reaching scripts.

Resume with `/plan-marshall plan=plan-145-publish-the-missing-parser-seams`
(re-enters at 4-plan). Outline is complete and Q-Gate-clean (0 pending).
