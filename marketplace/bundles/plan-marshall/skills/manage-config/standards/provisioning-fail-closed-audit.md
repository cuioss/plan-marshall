# Provisioning fail-closed audit

An enumeration of every provisioning write site and status-producing read across
the steward / manage-config / executor-provisioning surface, each carrying a
fix-or-justify disposition against two failure shapes:

- **Shape (a) — silent-success write.** An unknown or invalid write returns
  `status: success` instead of refusing, so a typo'd key or an out-of-schema
  value persists silently to `marshal.json` where no reader ever consults it.
- **Shape (b) — vacuous-safe verdict.** A missing or degraded input yields a
  vacuously-safe positive verdict (`fresh` / `ok`) instead of failing closed
  with an explicit `unknown` / `error`, so a caller mistakes "could not
  determine" for "confirmed good".

The governing decision is ADR-009 (`Status reporting fails closed with an
explicit unknown state`): a surface reporting a positive property must model the
third, evidence-absent state as a first-class value — never fold it into the
positive.

This is an enumeration (not a sample): every write + status handler under the
surveyed scope appears below with a disposition.

## Shared write choke point (the D4 encoding anchor)

Every `manage-config` write ultimately persists through
`_config_core.save_config(config)`, but `save_config` itself stays unvalidated —
it writes ANY config dict with no per-field validation. The fail-closed
provisioning-write invariant is instead encoded by `_config_core`'s
`reject_unknown_provisioning_field`, a shared guard each provisioning-write
handler invokes against its caller-supplied field BEFORE `save_config` (deliverable
4). The invariant to generalize already exists at one sibling:
`_cmd_system_plan.cmd_project set` rejects unknown fields, invalid values, and
bad types before persisting (the PLAN-07 pattern). The one enumerated write that
did NOT yet share that guard was `cmd_system retention set`.

## Surveyed sites

### manage-config/scripts/_cmd_system_plan.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `cmd_system` retention `set` (lines 61-83) | (a) | **FIX (D4).** Writes `retention[field] = value` with NO whitelist check on `field`, then returns `success_exit`. A typo'd or retired retention key persists silently. This is the one concrete silent-success write the sweep found; deliverable 4 routes it through the validated-write seam / generalizes the `cmd_project set` whitelist. |
| `cmd_project set` (lines 120-177) | (a) | **JUSTIFY.** Already fails closed: rejects unknown fields (`unknown_field`), invalid `pr_strategy` / `pr_compact_max_changed_files` values (`invalid_value`), and non-list/non-string `working_prefixes` (`invalid_type`, `invalid_json`) before `save_config`. This is the pattern D4 generalizes. |
| `cmd_project get` (lines 112-118) | (b) | **JUSTIFY.** Returns `field_not_found` for an unknown field rather than a vacuous value; falls back to `DEFAULT_PROJECT` only for known fields. |
| `cmd_project pr-decision` (lines 179-211) | (b) | **JUSTIFY.** Re-validates the resolved knobs at the read boundary and rejects a negative `--changed-files`; a corrupt marshal.json fails loud here rather than producing a wrong verdict. |
| `cmd_system` unknown sub-noun / verb (line 85); `cmd_project` unknown verb (line 213); `cmd_plan` unknown sub-noun (line 227) | — | **JUSTIFY.** All terminate in `error_exit`, never a silent success. |

### manage-config/scripts/_config_core.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `save_config` (lines 113-117) | (a) | **JUSTIFY (D4 anchor is the sibling guard).** The shared write choke point — writes any config dict unvalidated; `save_config` itself is NOT where deliverable 4 encodes the invariant. Instead, `reject_unknown_provisioning_field` (this module) is the shared guard each provisioning-write handler calls against its caller-supplied field before reaching `save_config`, so the invariant is encoded once at the call-site boundary rather than re-derived per handler or inside `save_config`. |
| `merge_build_map` (lines 615-653) | (b) | **JUSTIFY.** Fails closed: raises `BuildMapMissingError` on an absent or corrupt `build.map` rather than returning an empty dict (which would read as a silent no-build). The fail-closed exemplar this audit generalizes. |
| `get_build_map` (lines 399-412) | (b) | **JUSTIFY.** Returns `{}` on absent `build.map`, but it is a read-only helper; every caller that REQUIRES the map routes through `merge_build_map`, which fails closed. |
| `require_initialized` (lines 52-59); `load_config` (lines 62-68) | (b) | **JUSTIFY.** Raise `MarshalNotInitializedError` / `ValueError` on a missing or unparseable `marshal.json` — no vacuous success. |
| `ext_defaults_set` / `ext_defaults_set_default` (lines 320-358) | (a) | **JUSTIFY.** Write arbitrary extension-default keys by design — the extension-default keyspace is open by contract (each extension owns its keys), so there is no whitelist to enforce. Not a provisioning-schema write; out of the D4 invariant's scope. |

### manage-config/scripts/_cmd_sync_defaults.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `cmd_sync_defaults` (lines 386-481) | (a)/(b) | **JUSTIFY.** Only ADDS keys missing from the canonical `get_default_config()` (never writes an unknown key) and unconditionally refreshes the provisioning stamps; persists through `save_config`. On a missing marshal.json it returns `error_exit` (line 428); on unparseable JSON `load_config` raises. No silent-success, no vacuous verdict. |

### manage-config/scripts/_config_defaults.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `stamp_provisioning_fields` (lines 1141-1173) | (b) | **JUSTIFY.** Non-destructive on an empty read: when `read_provisioned_version` returns `''` (unstamped/absent executor), a pre-existing `provisioned_version` is preserved rather than blanked — a known-good version is never lost merely because the executor could not be read. |
| `read_provisioned_version` (lines 1114-1138) | (b) | **JUSTIFY.** Returns `''` on an absent/unreadable executor. The empty string is the documented unstamped sentinel consumed as "fresh install", NOT a vacuous positive — downstream `_version_tuple('')` sorts lowest, so an unstamped surface is never treated as newer than a real version. |
| `validate_*` helpers (pr_strategy, gate_mode, lane_*, per_deliverable_build, cost_size_token_table, sonar_touched_file_cleanup, simplicity, domain invariants) | (a) | **JUSTIFY.** Each raises `ValueError` on an invalid value; the `cmd_*` callers convert that to `error_exit`, so an invalid value never persists. |

### marshall-steward/scripts/determine_mode.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `run_preflight` / `cmd_check_staleness` (lines 843-898) | (b) | **JUSTIFY.** Returns a structured `status: error` on a missing script, non-zero exit, timeout, or unparseable/empty output; otherwise a verbatim pass-through of `generate_executor preflight`, whose `marshal_status` is already `unknown` (never a vacuous `fresh`) when the manifest is unresolvable. |
| `check_worktree_plan_local` (lines 274-317) | (b) | **JUSTIFY.** Fails closed with `refuse` when a worktree lacks its own `.plan/local`, so executor generation cannot contaminate the main checkout. |
| `detect_working_prefixes_drift` (lines 755-811); `detect_missing_default_finalize_steps` (lines 616-647); `detect_missing_project_finalize_steps` (lines 698-716) | (b) | **JUSTIFY (with caveat).** These wizard-flow detectors degrade to `ok` / `[]` on an absent OR unparseable `marshal.json` so the pre-executor wizard never crashes. A corrupt marshal.json is surfaced by the steward's own JSON-validity health check, not by these drift detectors — "nothing to detect" against an unreadable config is the correct degraded answer for a detector whose job is drift, not validity. |
| `determine_mode` (lines 177-201); `cmd_mode` (lines 487-492); `check_structure` (lines 204-257) | (b) | **JUSTIFY.** Pure presence classification; `check_structure` returns `missing` (not a vacuous `exists`) on absent/corrupt `_project.json`. |
| `fix_docs` / `cmd_fix_docs` (lines 430-484) | (a) | **JUSTIFY.** Deterministic idempotent doc-content append; not a `marshal.json` provisioning write. |

### marshall-steward/scripts/upgrade.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `build_plan` / `cmd_plan` (lines 169-223) | — | **JUSTIFY.** Pure plan emitter — invokes no machinery, mutates no filesystem, makes no git/CI calls. Raises `ValueError` on an invalid `project_kind`. No write, no status read. |

### tools-script-executor/scripts/generate_executor.py

| Site | Shape | Disposition |
|------|-------|-------------|
| `find_installed_manifest_path` | (b) | **JUSTIFY (D1).** Returns `None` when no candidate is resolvable (→ `unknown` downstream) and now selects the highest-version candidate rather than first-hit, so a stale manifest cannot shadow a newer one. |
| `read_installed_manifest` | (b) | **JUSTIFY.** Returns `{}` on an absent/unreadable/non-dict manifest; callers treat `{}` as the `unknown` sentinel. |
| `read_executor_version` | (b) | **JUSTIFY.** Returns `'unknown'` on an undecodable executor rather than raising or reporting a fabricated version. |
| `cmd_preflight` | (a)/(b) | **JUSTIFY (canonical exemplar), re-justified against the pinned marking predicate.** Fails closed: reports `marshal_status: unknown` with a legible warning when the manifest is unresolvable (never a vacuous `fresh`); regenerates the executor (safe derived state, ADR-002) on staleness/pollution; surfaces a structured error when regeneration fails. Its deferral marking now excludes every retention-pinned version (newest-on-disk / provisioned / manifest-named — see `_retention_pinned_versions`), so the pollution signal still clears run-over-run WITHOUT the marker saturating to zero live dirs. The preflight's own verdict inputs are unchanged and remain local-only by design: it answers "is my executor consistent with my cache?", never "is my cache current?" — the cache-vs-upstream question is owned by `marshall-steward`'s `cache_freshness check`. |
| `_detect_multi_version_pollution` | (b) | **JUSTIFY, re-justified against the pinned marking predicate.** Returns `[]` on an unresolvable base_path — it makes no pollution claim it cannot substantiate — and excludes `.orphaned_at`-marked dirs from the live count. The prior justification silently rested on the marker being a currency signal; under saturation (every dir marked, zero live) the detector became **vacuous**, unable to return `>1` at all. The pinned marking predicate restores the premise structurally: the newest-on-disk dir is never marked, so every bundle with a version dir on disk contributes at least one live dir and the `>1` comparison stays meaningful. |
| `generate_executor` | (a) | **JUSTIFY.** Runs three deterministic guards (format-version handshake, placeholder-residue, `py_compile` self-check) and commits atomically; refuses with `status: error` (preserving the pre-existing executor byte-identical) rather than emitting a broken executor. |
| `cmd_generate` | (a) | **JUSTIFY.** Returns a structured `status: error` (not an unhandled exception) when the marketplace base path is unresolvable. |

## Summary

- **One silent-success write requires a fix:** `cmd_system retention set` (shape
  a), fixed by deliverable 4.
- **The shared guard deliverable 4 encodes at:** `_config_core`'s
  `reject_unknown_provisioning_field`, invoked by each provisioning-write call
  site before `save_config`, generalizing the `cmd_project set` whitelist
  pattern.
- Every other enumerated site already fails closed (structured `error` / raised
  exception / explicit `unknown` sentinel) or is out of the provisioning-schema
  invariant's scope (open extension-default keyspace, pure emitters, idempotent
  doc appends), each justified above.
