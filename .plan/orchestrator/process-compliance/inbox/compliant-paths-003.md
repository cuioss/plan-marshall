envelope_version=1
sender_type=plan
sender_id=compliant-paths
epic=process-compliance
kind=finding
created=2026-09-19T15:15:20Z

# PLAN-03 implementation outcome (plan compliant-paths)

Epic: process-compliance
Kind: finding (implementation report; no PR cut — commit/PR left to operator)

## What shipped (working tree, uncommitted)

Deliverable 1 — sanctioned orchestrator-spec read path:
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`: new `corpus read --slug SLUG --plan PLAN-NN` verb (`cmd_corpus_read` + `read` subparser + module/group docstrings). Main-anchored, read-only, exact-or-prefix stem match with hyphen boundary. Refusals: `invalid_slug`, `invalid_plan` (traversal), `spec_not_found` (with `available_specs`, never an empty body), `unreadable`, `not_found`.
- `plan-orchestrator/SKILL.md`: canonical `corpus read` block.
- Verified live: `corpus read --slug process-compliance --plan PLAN-03` returns the 114-line spec body; `PLAN-99` returns `spec_not_found` with 8 available specs.

Deliverable 2 — generator-bootstrap exception + template-content staleness:
- `tools-script-executor/templates/execute-script.py.template`: new embedded `TEMPLATE_SHA256` stamp (empty = pre-stamp unknown, never fresh).
- `tools-script-executor/scripts/generate_executor.py`: hash computation + substitution, `read_executor_template_sha()`, `current_template_sha256()`, new `bootstrap` verb (absent → generate/`executor_absent`; invalid → generate/`executor_invalid`; hash mismatch → generate/`template_stale`; fresh → refuse `not_needed`; unstampable → `unknown` + refuse), module-docstring exception record, `bootstrap` subparser registration.
- `tools-script-executor/SKILL.md`: canonical `bootstrap` block; broken-executor recovery + case table repointed from bare direct `generate` to `bootstrap`.
- Verified live: fresh executor → `not_needed`/`fresh`; pre-stamp executor state → `unknown` + refuse (observed during rollout before regen).

Deliverable 3 — wrapper filter passthrough for fast targeted signal:
- `build.py`: `module-tests` gains `--filter EXPR` forwarded as pytest `-k` (list argv, no shell); empty `--filter` refused with exit 1; docstring + epilog examples.
- `build-pyproject/scripts/pyproject_build.py` + `build-pyproject/SKILL.md`: sanctioned form `run --command-args "module-tests {dir} [--no-parallel] [--filter {expr}]"` documented with the whitespace-split constraint (single-token filters only via command-args).
- Dogfooded: all verification below ran through the new passthrough; direct `.venv` pytest never invoked.

Deliverable 4 — tests:
- `test/plan-marshall/plan-orchestrator/test_orchestrator_corpus_read.py` (15 tests: verbatim body + populations, prefix match, read-only snapshot, 4 refusal classes, hyphen-boundary PLAN-1/PLAN-10 control).
- `test/plan-marshall/tools-script-executor/test_generate_executor_template_bootstrap.py` (11 tests: stamp shape/round-trip, 6 bootstrap decisions incl. unknown-never-regenerates).
- `test/default/test_build_module_tests_filter.py` (7 tests: -k argv, xdist coexistence, absence-is-not-empty, empty-refused, --help carries flag).

## Verification (all via executor-mediated wrapper, plan=compliant-paths)

- `module-tests plan-marshall --filter corpus_read`: green, 15 run.
- `module-tests plan-marshall --filter template_bootstrap`: green, 11 run.
- `module-tests default --filter test_build_module_tests_filter`: green, 7 run.
- `module-tests plan-marshall` (full): green, 22373 run.
- `module-tests default` (full): green, 76 run.
- `quality-gate` (whole tree: mypy + ruff + plugin-doctor): green.

## Hypothesis settlement (for orchestrator `corpus set-verdict`; not stamped — spec writes are orchestrator-owned per Write-Boundary)

- HYPOTHESIS corpus-seam: CONFIRM — `cmd_corpus_read` built in the corpus group; recommend `corroborated`.
- HYPOTHESIS wrapper-passthrough-at-command-args: CONFIRM with one scoping correction — command-args is the forwarding mechanism, but the terminal block was `build.py` argparse (no filter slot), so the fix spans `build.py` (`--filter`) + wrapper-layer documentation; recommend `corroborated` with that evidence.
- AGENTS.md carve-out alternative for D1: NOT needed — sanctioned path built, strict scripts-only rule stands.

## Notes for finalize

- `uv.lock` shows a ruff 0.16.6→0.16.8 bump produced by the build daemon's `uv run` resolution, not by this change. Left untouched per the no-restore-without-snapshot rule; exclude from the landing commit.
- `.plan/` (plan `compliant-paths`, now in `5-execute`) and `.plan/temp/` payloads are gitignored — no ledger files ride the PR.
- Preflight at session start reported `marshal_status: stale` (advisory) — operator to run `/marshall-steward` per the branch contract.
- New process-rule finding filed separately: `compliant-paths-002.md` (phase-1-init doc invents `--request-text` for `domain-detect`; live `--help` rejects it).
