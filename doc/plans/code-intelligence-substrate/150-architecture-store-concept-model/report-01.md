# Run report — 150-architecture-store-concept-model (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/code-intelligence-substrate-arch-kopkuq` (harness-assigned)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by path from the bundle tree (the plan-marshall plugin is not installed in this cloud session):

- `plan-marshall:ref-code-quality` — always.
- `pm-plugin-development:plugin-script-architecture` — always.
- `plan-marshall:persona-implementer` — production code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.
- `pm-plugin-development:plugin-architecture` — SKILL.md / bundle structure.

The `cloud-plan-lane` skill was loaded first, as the run's first action.

## Deliverables

The persisted store maps to: `_project.json` = root index; per-module `enriched.json` = concept documents; `key_packages` = inner package entries. All store-shape claims were verified against the WRITERS (the live store lives under the git-ignored `.plan/` tree and is unreachable from the clone) and against fixtures.

Implementation commit: `7219569` (feat: give the persisted store a concept model).

- **D1 — path is identity.** `key_packages` keys are now repo-relative paths.
  - Write gate: `enrich_package` calls `validate_package_key` → `NonResolvingPathKeyError` (named error) for a non-resolving key; the CLI handler surfaces `error: non_resolving_package_key`. The `--package` argparse arg switched from `validate_package_name` (dotted) to `validate_relative_path`.
  - Read migration: `merge_module_data` rewrites legacy dotted keys to paths via `migrate_key_packages` using the derived `packages` map (dotted→path bridge); unresolved keys are surfaced as a non-blocking WARNING (never silently dropped).
  - *Verification:* `test_concept_model.py` — `test_enrich_package_refuses_non_resolving_key`, `test_enrich_package_accepts_resolving_path_key`, `test_cmd_enrich_package_returns_named_error_for_non_resolving_key`, `test_migrate_key_packages_*`, `test_merge_module_data_migrates_dotted_key_packages`. Plus `test_cmd_enrich.py` enrich_package tests migrated to path keys, and the `--package` input-validation axis re-based on path-shaped rejections.

- **D2 — a required, closed, validated `type`.** `CONCEPT_TYPES` (`module/skill/script/standard/decision_record`) declared once in `_architecture_core.py`.
  - Refusal at write time (`save_module_enriched` → `migrate_concept_document` → `validate_concept_type`, `InvalidConceptTypeError` naming the accepted set) and on read (`load_module_enriched`). Absent type migrates deterministically to `module` (named migrate-on-read, never a silent default).
  - *Verification:* the three migration states pinned in `test_concept_model.py` — pre-field → module, valid → kept, unknown → refused (write and read); plus vocabulary/message tests.

- **D3 — root index carries per-module descriptions.** `api_discover` builds the `modules` index as `{name: {description, generation}}`, mirroring each module's `responsibility` + generation header.
  - NOT a discovery gatekeeper: `iter_modules` crawls the live filesystem, unchanged.
  - *Verification:* `test_discover_index_carries_description_and_generation`, `test_discover_index_description_defaults_empty_for_fresh_module`, and the negative control `test_module_on_disk_absent_from_index_is_still_discovered`.

- **D4 — generation provenance and freshness.** `save_module_enriched` stamps `generation = {by, tree_sha}` on every write (`build_generation` → `compute_worktree_sha`, the shared freshness primitive). `derive_freshness` returns `fresh`/`stale`/`unknown` from the tree identifier (not mtime). The header is mirrored into the index, so `info` surfaces per-module `description` + `freshness` without reading any concept body.
  - *Verification:* `test_derive_freshness_*`, `test_freshness_verdict_derived_from_header_alone`, `test_info_surfaces_freshness_from_index`, `test_save_stamps_generation_header`.

Out-of-scope items (reasoning-field family, markdown/frontmatter serialization, leniency/broken-link tolerance, existence-marker question, writing new content) were respected — no change touches them.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production scripts + tests changed), so the Python build gate applies.

- **Quality gate** (`./pw quality-gate`): clean — `mypy: Success: no issues found in 396 source files`, `ruff: All checks passed!`, `SPDX-header check passed`, `plugin-doctor: issues[0]` (zero findings, incl. `broken-relative-link`, `scan_manage_invocation`). EXIT=0.
- **Test suite** (`uv run pytest -n auto`, the `./pw` test tool): whole-tree **19531 passed, 14 skipped, 0 failed** (filterwarnings=error, no warnings). Affected manage-architecture tests re-run after the final type fixes: 144 passed.

## Findings

_Pending — verification sub-agent dispatched (Step 6); PR review to follow (Step 7). Each finding will be recorded per instance with source and disposition._

## Reviewer participation

_Pending — populated after the PR review cycle (Step 7)._

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| _pending_ | | |

## Cost

- **Tokens:** not available to the agent in this session (the harness does not expose a per-session token counter to the run).
- **Wall-clock:** single interactive cloud session; build gate ≈ full test suite 382s + quality gate ≈ 2 min.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary this session does not share.

## Contract check (Step 9)

_Pending — completed as the last pre-merge commit._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
