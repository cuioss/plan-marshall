# Run report — 050-migration-shims-have-no-expiry (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/migration-shims-expiry-3nidnh` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded by path from the bundle source (the repo *is* the marketplace; the `plan-marshall` plugin
notation route was not relied on):

- `cloud-plan-lane` (working contract — first action)
- `plan-marshall:ref-code-quality` + `standards/code-organization.md` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)
- `pm-plugin-development:plugin-architecture` (bundle/SKILL structure — plugin-doctor rule home)

## Deliverables

- **D0 — GATE: re-derive the inventory** — **DONE.** See "D0 inventory" below. STOP CONDITION fired;
  operator directed continue → autonomous fallback (scope on D0's output, all 24 sites).
- **D1 — shim-marker convention** — **DONE.** Convention documented at `pm-plugin-development:
  plugin-script-architecture/standards/shim-marker-convention.md` (+ SKILL pointer), commit `bcc084d`.
  All 5 category-A sites carry a conforming `# SHIM(A):` marker (commit `be8e1e4`).
- **D2 — plugin-doctor rule flagging an unmarked shim** — **DONE.** `shim-marker-missing` rule
  (`_analyze_shim_marker.py`), population-derived over `bundles/*/skills/*/scripts/**/*.py`, publishes
  `population_size` (386 on the real tree), both-direction tests, empty-population guard, wired
  build-failing into quality-gate + analyze, provenance + catalog rows, firing fixture. Commit `80a56a9`.
- **D3 — retirement sweep over surviving category-B sites** — **DONE.** All 19 category-B sites carry a
  conforming `# SHIM(B):` marker with a concrete floor + removal trigger (commit `be8e1e4`). **No
  deletions:** for every surviving site the tolerated shape is persisted state (archived plans,
  in-flight status.json, machine-global queue state, on-disk credential files, un-resynced configs)
  that cannot be shown extinct in this clone — so the plan's "delete only against extinction evidence"
  rule mandates marking, not deletion. Each site's removal trigger records the (often long-horizon)
  extinction condition, which is exactly the recorded-what-and-since-when the plan wants.

### D2 detector design note (false-positive boundary)

Prose vocabulary cannot cleanly separate a shim from defensive code — "legacy", "written before",
"backward compatibility", and "pre-dating" all appear in BOTH the 24 shims and the ~18 negatives. So
the detector is **precision-first**: the marker is the membership signal (it suppresses findings over
its enclosing function), and the unmarked-shim half fires only on a narrow, corpus-calibrated
indicator set. Calibration against the real marked tree drove **0 findings** — after dropping two
over-broad indicators (a bare `retired key/knob` phrase, which hit write-side *rejection* guards in
`_cmd_system_plan.py`; and `pre-home-root`, which hit a *caller* comment in `_cred_list.py`) and
widening marker coverage to reach a leading comment block. The `_read_status_created` defensive-`None`
case and the rejection/caller/external cases are the load-bearing negative tests.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (markers on 16 scripts + the new
analyzer + 2 test files) → **full path taken.** `./pw quality-gate`: `status: pass`, `total_issues: 0`,
387 source files, ruff + SPDX + mypy clean. `./pw module-tests` (whole tree): **18808 passed, 14
skipped.** The plugin-doctor static-analysis pass runs the new `shim-marker-missing` rule over the real
tree and reports zero findings — the D1 + D2 regression anchor.

## D0 inventory (GATE deliverable)

### Derivation method (population-derived, first-party)

Population = every Python script under `marketplace/bundles/*/skills/*/scripts/**/*.py` (the
executable-tooling source tree — the enumerable inventory analog). Candidate sites were surfaced by
content sweeps for version-boundary vocabulary (`legacy`, `back-?compat`, `backward(s)`, `migrat`,
`pre-migration`, `old (format|shape|style|key|column|schema|on-disk)`, `older (version|orchestrator|
plan|format)`, `written before`, `pre-dates`, `tolerate`), then **each candidate was read by symbol
and classified against a precise discriminator** by four independent read-only sub-agents plus
first-party reads of the two anchor files.

**Discriminator.** A site is a **version shim** iff it reads persisted state/config/data and
accommodates a shape an *earlier version of this tooling* once wrote and the current version no
longer writes (tell: "written before X existed", "legacy key", "pre-migration", "older format",
"retired key"). **Category A** migrates the old shape and deletes/pops it (self-disarming; a second
run is a no-op). **Category B** tolerates the old shape on the read path permanently (never disarms).
Explicitly **NOT** a shim: ordinary defensive handling of missing/malformed/absent data any version
can produce (the `_read_status_created` negative), CLI-flag/env-var/API-signature call-site
compatibility, module re-export aliases (governed by the existing `SIMPLICITY_BACKWARD_COMPAT_REEXPORT`
rule), and tolerance of an *external* system's shape variance (GitHub login casing, LSP protocol
variants).

**Volume vs coverage (kept separate, per the plan's warning).** Files examined (population): 400+
scripts swept for vocabulary; ~30 candidate sites read by symbol; **24 classified as version
shims**, ~18 classified as NOT-a-shim. The 24 is the hit count, not the volume.

### Result — 24 version-shim sites (5 category-A, 19 category-B)

**Category A — one-shot, self-disarming (5):**

| # | Site | Old shape retired |
|---|------|-------------------|
| A1 | `manage-config/scripts/_cmd_sync_defaults.py :: _migrate_retired_step_keys` (`RETIRED_STEP_KEY_RENAMES`) | renamed step ids a prior release emitted |
| A2 | `manage-config/scripts/_cmd_sync_defaults.py :: _migrate_run_at_all_to_lane` | retired `run_at_all` gate value → `lane` |
| A3 | `marshall-steward/scripts/upgrade.py :: migrate_bot_lists` | retired `enabled_bots` → `required_bots`/`optional_bots` (the sibling auto-map; per plan Notes, not a defect) |
| A4 | `marshall-steward/scripts/gitignore_setup.py :: consolidate_managed_blocks` | pre-PR#666 multi-block `.gitignore` → single block |
| A5 | `manage-providers/scripts/_providers_core.py :: _migrate_credentials_home_if_needed` | pre-home-root `~/.plan-marshall-credentials` dir → home-root path |

**Category B — permanent tolerate/detect read path (19):**

| # | Site | Old shape tolerated |
|---|------|---------------------|
| B1 | `manage-status/scripts/_cmd_mark_step.py :: cmd_mark_step_done` (`legacy_string_entry`) | pre-dict bare-string step storage (`--force` migrates) |
| B2 | `manage-status/scripts/_cmd_assert_step_recorded.py :: cmd_assert_step_recorded` | pre-migration `default:`-prefixed step key |
| B3 | `manage-config/scripts/_cmd_sync_defaults.py :: _deep_merge_missing` | legacy `{}` vs new `None` ownerless-step value ⚠ borderline |
| B4 | `marshall-steward/scripts/determine_mode.py :: _extract_step_ids` | legacy list-of-id-strings `steps` shape |
| B5 | `marshall-steward/scripts/gitignore_setup.py :: _MANAGED_RULE_LINES` | retained legacy managed-rule recognition |
| B6 | `marshall-steward/scripts/gitignore_setup.py :: check_gitignore_status_from_content` | older `.plan/` / `.plan` rule format |
| B7 | `plan-retrospective/scripts/analyze-logs.py :: resolve_footprint` | legacy `references.modified_files` (pre-ledger-removal) |
| B8 | `plan-retrospective/scripts/analyze-logs.py :: _parse_dispatch_boundary_file` | legacy 5-column dispatch rows (pre-context-load widening) |
| B9 | `plan-retrospective/scripts/check-artifact-consistency.py :: _resolve_footprint` | legacy `references.modified_files` (pre-ledger-removal) |
| B10 | `plan-retrospective/scripts/check-manifest-consistency.py :: run` | pre-manifest archived plans (no `execution.toon`) |
| B11 | `manage-run-config/scripts/_cmd_cleanup.py :: get_retention_settings` | marshal.json written before a retention key existed (in-memory backfill) |
| B12 | `plan-marshall/scripts/_invariants.py :: _capture_references_valid` | `references.json` predating the retired key ⚠ soft |
| B13 | `plan-marshall/scripts/_invariants.py :: phase_steps_complete` | bare-string step entry (detect-and-reject variant) |
| B14 | `manage-locks/scripts/build_queue.py :: _prune_dead_active` | queue entry lacking `project_root` |
| B15 | `manage-locks/scripts/build_queue.py :: validate_lock_queue` | queue entry lacking `active_since` |
| B16 | `script-shared/scripts/argparse_surface.py :: _node_from_dict` | pre-v4 surface cache lacking `flag_arity` |
| B17 | `workflow-permission-web/scripts/permission_web.py :: _extract_domain_names` | plain-string domain config (pre-enriched) ⚠ borderline |
| B18 | `manage-providers/scripts/_cred_configure.py` (URL fallback) | `url` in credential file (pre-marshal.json relocation) |
| B19 | `manage-providers/scripts/_providers_core.py` (URL fallback, 2nd read site) | `url` in credential file (same boundary as B18) |

None of the 24 carries a structured owner + version-floor + removal-trigger marker today; the
strongest existing anchors are prose-only ("pre-PR#666", "v4:", "written before this change shipped",
"predates the change").

### Survived / dropped / new vs the plan's 11-row lead table

- **Survived (confirmed shims from the plan's leads):** `_cmd_mark_step.py` (B1), `_cmd_sync_defaults.py`
  (A1/A2/B3), `_cmd_assert_step_recorded.py` (B2), `determine_mode.py` (B4), `gitignore_setup.py`
  (A4/B5/B6), `upgrade.py` auto-map (A3). The `manage-providers` lead resolved to `_cred_configure.py`
  + `_providers_core.py` (B18/B19 + A5) rather than only `_providers_core.py`.
- **Dropped (lead was wrong / not a shim):** `manage-metrics.py :: _read_status_created` — **confirmed
  defensive None-handling, not a shim** (both OBSERVED claims verified: the quoted "older orchestrator
  versions" phrase is absent; the real docstring names "missing status.json, malformed JSON, missing
  'created' key, non-string value → None"). Becomes D2's negative test case. `tools-permission-fix/
  permission_fix.py` surfaced no version-shim site.
- **New (not in the plan's leads):** B7–B10 (retrospective footprint/manifest readers), B11
  (`_cmd_cleanup` retention backfill), B12–B13 (`_invariants`), B14–B15 (`build_queue`), B16
  (`argparse_surface`), B17 (`permission_web`), A5 (`_providers_core` credentials-dir migration).

### High-value NOT-A-SHIM negatives (for D2's false-positive boundary)

`_read_status_created` (defensive None — the canonical negative); `manage-metrics cmd_generate`
pop-of-computed-keys (self-disclaimed "not a compatibility shim"); `_stamp_value_scope` (version-
flavoured honest default); WARN→WARNING and record-dispatch `unknown` (breaking *refusals* of the old
shape); `determine_mode resolve_doc_file` agents.md (external case variance); `file_ops PLAN_BASE_DIR`
(env-var knob); `_handshake_commands _coerce_path_list` (hand-edited comma string); `_config_core
order_config_keys` (defensive preserve-unknown); `retro_sections`/manifest `warn→info` (feature toggle
by artifact presence).

### STOP CONDITION assessment

Count 24 vs 11 (**> 2×**) and B-split 19 vs 6 (**~3×**) — **both STOP-CONDITION triggers fire.** Per
the plan ("this deliverable may re-scope the plan … halt and report") the finding was reported to the
operator (D0 inventory pushed, divergence stated). **Disposition:** the operator directed the run to
continue ("continue from where you left off"), so the run takes the plan's stated autonomous fallback
— **D1 and D3 scope on D0's output** (all 24 confirmed sites), not on the plan's presumed 11. The
finding *strengthens* the plan's thesis (category-B readers are the accumulating half) rather than
refuting it, so proceeding on the enlarged scope is consistent with the plan's goal.

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending PR_

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not
  surface a token counter to the running agent).
- **Wall-clock:** run start ~2026-08-10; end at finalize.
- **Population:** this single Claude Code cloud session's usage. NOT comparable to a plan-marshall
  `metrics.toon` total (different billing boundary — no orchestrator dispatch tree here).

## Contract check (Step 9)

_pending finalize_

## What have we learned (Step 9)

_pending finalize_

## Residue

_pending_
