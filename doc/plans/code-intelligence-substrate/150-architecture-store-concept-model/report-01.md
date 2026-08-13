# Run report — 150-architecture-store-concept-model (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/code-intelligence-substrate-arch-kopkuq` (harness-assigned)    **PR:** [#1216](https://github.com/cuioss/plan-marshall/pull/1216)    **Outcome:** completed (landing delegated to auto-merge / queue)

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

Implementation commit: `7219569` (feat: give the persisted store a concept model). Follow-up fix: `be98185` (path-boundary hardening — see Findings).

- **D1 — path is identity.** `key_packages` keys are now repo-relative paths.
  - Write gate: `enrich_package` → `validate_package_key` → `NonResolvingPathKeyError` (named error); the CLI handler surfaces `error: non_resolving_package_key`. `--package` switched from `validate_package_name` (dotted) to `validate_relative_path`. `package_key_resolves` refuses absolute, traversal, drive-letter, and root-escaping keys (containment check).
  - Read migration: `merge_module_data` rewrites legacy dotted keys to paths via `migrate_key_packages` (derived `packages` dotted→path bridge); unresolved keys → non-blocking WARNING, never silently dropped.
  - *Verified:* `test_concept_model.py` — refusal, acceptance, named-error, migration, merge-migration, and the root-escape containment tests.

- **D2 — a required, closed, validated `type`.** `CONCEPT_TYPES` declared once in `_architecture_core.py`.
  - Refused at write (`save_module_enriched`→`migrate_concept_document`→`validate_concept_type`, `InvalidConceptTypeError` naming the accepted set) and read (`load_module_enriched`). Absent type → deterministic migrate-on-read to `module`.
  - *Verified:* the three migration states (pre-field → module, valid → kept, unknown → refused at write AND read); vocabulary/message tests.

- **D3 — root index carries per-module descriptions.** `api_discover` builds `modules` as `{name: {description, generation}}`, mirroring each module's `responsibility` + generation header. NOT a discovery gatekeeper (`iter_modules` crawls the filesystem, unchanged).
  - *Verified:* index-description/generation tests, and the negative control `test_module_on_disk_absent_from_index_is_still_discovered`.

- **D4 — generation provenance and freshness.** `save_module_enriched` stamps `generation = {by, tree_sha}` on every write (`build_generation` → `compute_worktree_sha`, the shared freshness primitive). `derive_freshness` → `fresh`/`stale`/`unknown` from the tree identifier (not mtime); mirrored into the index so `info` surfaces per-module `description` + `freshness` without reading any concept body.
  - *Verified:* freshness verdict tests, `test_freshness_verdict_derived_from_header_alone`, `test_info_surfaces_freshness_from_index`, generation-stamp test.

Out-of-scope items (reasoning-field family, markdown/frontmatter serialization, leniency/broken-link tolerance, existence-marker question, writing new content) were respected — no change touches them.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (production scripts + tests), so the Python build gate applies.

- **Quality gate** (`./pw quality-gate`): clean at every commit — `mypy: Success: no issues found in 396 source files`, `ruff: All checks passed!`, `SPDX-header check passed`, `plugin-doctor: issues[0]`. EXIT=0.
- **Test suite** (`uv run pytest -n auto`, the `./pw` test tool): whole-tree **19531 passed, 14 skipped, 0 failed** (filterwarnings=error, no warnings). Affected manage-architecture tests re-run after each fix: green (109 after the path-boundary fix).

## Findings

Recorded per instance with source and disposition.

| # | Source | Finding | Disposition |
|---|--------|---------|-------------|
| 1 | Pre-PR sub-agent | `client-api.md:~1479` asserted the `_project.json` index is the "single source of truth for which modules exist" — false per D3 | **Fixed** (`f4937d2`) — rewritten to "discovery crawls the filesystem; index is a pre-flight surface" |
| 2 | Pre-PR sub-agent | `client-api.md` `info` worked example omitted the new `description`/`freshness` columns | **Fixed** (`f4937d2`) |
| 3 | Pre-PR sub-agent | `client-api.md` `module` default + `--full` examples showed dotted `key_packages` keys and no `type`/`generation` | **Fixed** (`f4937d2`) — path keys + concept header added |
| 4 | Pre-PR sub-agent | `_architecture_core.py:load_project_meta` docstring claimed "source of truth for module discovery" — false | **Fixed** (`f4937d2`); the two borderline items (`manage-api.md`, module docstring) tightened in the same commit |
| 5 | Pre-PR sub-agent (pre-existing, surfaced adjacent to the D1 edit) | `client-api.md` derived `packages` example used module-relative paths, inconsistent with the canonical repo-relative schema and the adjacent corrected `key_packages` path | **Fixed** as a declared collateral coherence correction (`f4fef2e`) |
| 6 | `cuioss-review-bot` (PR review) | `package_key_resolves` — Incomplete Path Boundary Check: a Windows drive-letter key (`C:/…`) bypasses the leading-`/` guard, and `Path/'C:/…'` discards `project_dir` and resolves to the drive-absolute target, so an out-of-tree absolute path could validate | **Fixed** (`be98185`) — containment check refuses any candidate that resolves outside the project root (also catches escaping symlinks); regression test added |

CI: `verify / gate`, `dependency-review`, `generate-check` reported success; `verify / verify` re-runs on each push and is the required build check the merge queue re-verifies on `merge_group`.

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`), read at run time, never transcribed. Verdicts derived from the stored comment bodies across all three surfaces (issue comments, review summaries, inline threads).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted the "PR Reviewer Guide" issue comment with one finding (Incomplete Path Boundary Check), fixed in `be98185`. |
| `coderabbitai` | `rate-limited` | Published only a commit status "Review rate limited" (context `CodeRabbit`) — engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Published a review-summary body only: "you have reached your weekly rate limit of 500000 diff characters"; the `Sourcery review` check concluded `skipped`. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure fired: "Review coverage 1-of-3 — `cuioss-review-bot` reviewed (finding fixed); `coderabbitai` rate-limited; `sourcery-ai` weekly-quota rate-limited." Rate limits are routine and outside our control, so this is disclosed, not blocked (conditions 1–3 are the only gates on the merge).

## Cost

- **Tokens:** not available to the agent in this session (the harness does not expose a per-session token counter to the run). Two verification sub-agents reported their own usage (~136k and ~158k subagent tokens); the main-loop figure is not surfaced.
- **Wall-clock:** single interactive cloud session; build gate ≈ full test suite 382s + quality gate ≈ 2 min per run; two sub-agent passes ≈ 426s + 178s.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary this session does not share. The figures above cannot be made commensurable, so no combined total is asserted.

## Contract check (Step 9)

| Step | Verdict |
|------|---------|
| 1 Skills loaded | Done — named above; loaded by bundle path (plugin absent). |
| 2 Branch | Done — harness-assigned `claude/code-intelligence-substrate-arch-kopkuq`, kept as-is, present on `origin` (pushed before any work). |
| 3 Plan directory | Done — `doc/plans/code-intelligence-substrate/150-architecture-store-concept-model/plan.md` exists and opens with the first-instruction block. |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | Done — every `*.py` commit preceded by a clean quality gate. |
| 4 Pushed | Done — no unpushed commit remains except the report commit (this file), pushed as the last pre-merge commit. |
| 5 Build gate | Done — Python changed → `./pw` quality gate + full suite; results above. |
| 6 Verification sub-agent | Done — dispatched, all four deliverables PASS; findings 1–5 fixed and re-verified clean. |
| 7 PR cycle | Done — PR #1216; all comment surfaces read (issue/review-summary/inline); the one actionable finding (#6) fixed. |
| 8 Merge gate | Conditions 1–3 met; auto-merge armed (SQUASH). Landing delegated to the merge queue; recorded to the operator, not embedded here. |
| 8 Bridge | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number + per-deliverable outcome. |
| 9 This check | Appended here. |
| 9 What have we learned | Recorded below. |

GitHub access path used: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned** (`claude/*`). A cloud run owes no `/sync-plugin-cache` (machine-local build step).

## What have we learned (Step 9)

**None proposed.** The run exercised the contract end to end and every gate functioned as designed: the pre-PR verification sub-agent caught documentation drift the local build gate cannot detect (the `client-api.md` staleness), and the PR-review cycle surfaced a real cross-platform boundary defect the sub-agent did not — exactly the layered coverage the contract intends. The one execution weakness — the first-pass beyond-diff sweep did not open `client-api.md` — is a shortfall in *my application* of the existing Step 6 "sweep beyond the diff across the owning bundle" instruction, not a gap in the instruction itself; the re-dispatch loop the contract mandates caught it. This is an autonomous run with no reachable operator mid-run, so no contract-change proposal is escalated.

## Residue

- The landing itself is delegated to auto-merge + the merge queue (a cloud session cannot block-until-landed); the orchestrator's collect step reads `state: MERGED` from the PR. If the queue rejects on a `merge_group` verify failure, that becomes a drive-to-green follow-up on this PR.
- `coderabbitai` and `sourcery-ai` did not review this diff (both rate-limited); a re-review could be requested when their windows reopen, but the merge is not held on it.
