# Landing Analysis: PLAN-03 — Claude-literal residuals

epic: multiplattform
workstream: WS-03
pr: #1319 (squash `bd107c38`, "chore(multiplattform): render Claude permission grammar and layout only in the runtime")

> Landing record for one shipped plan. Lives at `landings/PLAN-03.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Ingestion note.** This plan shipped in the standalone `doc/plans/multiplattform/` lane before this
epic ledger existed. This record was written at ingestion from a ground-truth verification against
HEAD `2cd1a19c` — the run report (`report-01.md`, 1113 lines, 9 verification rounds plus 2 external
reviews, archived at `archive/030-claude-literal-residuals/`) was treated as a claim set, and an
independent tree-wide Claude-literal sweep was run rather than trusting the report's own sweep.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Default permissions render in the runtime | shipped-as-specified | `permission_fix.py` no longer carries `DEFAULT_PERMISSIONS`; `cmd_apply_fixes` → `permission_common.ensure_default_permissions` → `claude_runtime.ensure_default_permissions` (`claude_runtime.py` 2613–2666), which renders, merges, writes, and returns only counts (`defaults_added`, `defaults_added_count`, `defaults_removed`, `defaults_removed_count`, `applied`). No rendered `Read(...)`/`Bash(...)` string crosses back. No `.claude/` literal in the file. |
| D2 — Settings-path reads delegate | shipped-as-specified | `permission_common.py::get_project_settings_path` (97–105) delegates to `claude_runtime._claude_project_settings_read_path`; no `.claude/settings` literal anywhere in the file; the docstring is now true. |
| D3 — Credential deny rules render in the runtime | shipped-as-specified | `_cred_ensure_denied.py` builds and receives no rule text — no `Read(`, no `Bash(`, no `_BASH_VECTORS`. It resolves via `_make_runtime(_read_runtime_target())` and calls `runtime.permission_fix(target, 'protect-path', …)`, forwarding `no-op`/`error`/`success` faithfully and reporting only counts. |
| D4 — Implementor scan routes through layout resolution | shipped-as-specified | `extension_discovery.py` 1289–1373: `_scan_project_for_implementors` iterates `get_project_skill_roots()` via `_project_skill_trees`; no segment-wise `.claude` construction. The one new `.claude/skills/` occurrence (line 1312) is an illustrative docstring literal, disclosed in the report. |
| D5 — Display/filter strings stop naming `.claude/` | shipped-modified (partly a no-op, disclosed) | `scan-marketplace-inventory.py::runtime_mount_prefix` (258–269) derives from `get_project_skill_roots()[0]` rather than a hardcoded value. The other half was already closed by earlier work: `_BOOKKEEPING_PREFIXES` now exists only in `_footprint_classification.py` as a historical-example comment, with zero hits in `check-manifest-consistency.py` / `check-routing-decisions.py`. The report names this divergence from its own OBSERVED claim as finding F22 rather than papering over it. |

**Descoped: none.** Every deliverable carries an explicit disposition. The plan's stated Out-of-scope
items were all honoured — `permission_doctor.py`'s analysis-rule knowledge stayed put with its own
inventory row, no `Runtime` operation was added (D3 extended the existing `protect-path` enum value,
so the op count stays 24).

⚠️ **Scope qualifier, and it matters for the epic.** "Zero Claude literals outside the sanctioned
homes" was **never this plan's actual claim**. The landed claim is narrower: zero literals in five
named clusters (three files fully, two where half was already done). Every literal found *beyond*
those clusters during the mandated sweep was registered as open work in the coupling inventory rather
than silently fixed or dropped. Independent re-derivation confirms that registry is accurate.

## Metrics and Anomalies

- Tokens: not available — standalone cloud plan lane, no `metrics.toon`.
- Duration: not instrumented in that lane.
- Anomalies: **9 verification rounds plus 2 external reviews.** Round 9 caught an *undisclosed
  regression* — a segment-wise `.claude/skills` construction reintroduced in
  `configurable_contract.py` — which was fixed. Later adversarial rounds added real security
  hardening beyond the brief (the `protect-path` refusal set covering filesystem-root, whitespace,
  control characters and `..`; a `_write_failed` fail-closed helper applied to all six mutating
  `permission_fix` branches; a tilde-form home-directory fix). All present in the current source.

## Routing and Merge Behavior

- Review: CodeRabbit proposed a `targets: [claude]` filter on the permission skills. **Declined with
  reason** — these skills are *mixed*: the platform-routed operations already work on a non-Claude
  target, and scoping the whole component would remove the working half to contain the broken half.
  The reviewer agreed registry routing is the correct fix and belongs to a separate plan. That plan
  is PLAN-08.
- CI/merge: merged as squash `bd107c38`.

## Reconciliation Actions

- [x] row `status` → `landed` — seeded at `decompose` (ingestion)
- [x] row `pr` stamped — `#1319`
- [x] row `landing` stamped — `landings/PLAN-03.md`
- [x] row `plan_marshall_plan_id` — `n/a` (standalone lane)
- [x] epic.md queue reconciled from status.json
- [x] Open Defects opened for the residual gaps below
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

**The central residue confirms PLAN-08's framing is accurate, not overstated.** `permission_common.py`
(32–41) and `permission_doctor.py` still carry `from claude_runtime import …` — a direct name import,
not a `platform_runtime._REGISTRY` route — so both resolve to the Claude implementation whatever
`runtime.target` says. `permission_fix.py` does *not* import it directly; it reaches the runtime
through `permission_common`. The Claude settings **mapping** still crosses into
`ensure_default_permissions` as an argument, violating principles §1 in both directions.
→ owned by **PLAN-08**, already staged, with both inventory rows pre-tagged `Drawn by: 080`.

Confirmed still open at HEAD and correctly registered, each owned elsewhere:

- `_dep_index.py`'s `CLAUDE_DIR` constant and project-scope resolution outside the layout op → **PLAN-06**.
- `marketplace_paths.py`'s fallback segment composition (`CLAUDE_DIR`, `_DEFAULT_SKILL_ROOTS`) → **PLAN-07**.
- `generate_executor.py::discover_local_scripts` still hardcodes `.claude/skills` → **unclaimed, PLAN-12** (new).
- A dozen `plugin-doctor` analyzer files carrying segment-wise `.claude/skills` anchors → **PLAN-06**.
- `permission_fix.py`'s residual permission-DSL knowledge (`EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`,
  the `Skill(...)`/`SlashCommand(...)` wildcard generators, `TIMESTAMP_PATTERN`, `normalize_path_perm`,
  `is_individual_script_permission`) → **PLAN-08**.

Confirmed **legitimate** and correctly *not* registered as open work: the illustrative "on Claude that
is X" docstring literals in `extension_discovery.py` (36, 1312) and `configurable_contract.py` (113);
`bootstrap_plugin.py`'s four `.claude/` literals (Claude-specific by design, in the inventory's
Confirmed-clean section — an earlier erroneous open-work registration of this site was caught and
withdrawn in round 3); and `generate_executor.py`'s embedded multi-root resolver.

Two further items:

- **`Grep` tool absence from the credentials-directory deny set** — still true at HEAD:
  `_EXFILTRATION_BASH_VECTORS` denies the Bash `grep` command, but no `Grep(...)` tool-permission rule
  exists. The report left this open as an operator policy question rather than deciding it.
  → **Open Defect** (needs an operator call, not a plan).
- **Report-01's "pinned three rules" prose is stale relative to HEAD, for a reason external to this
  plan.** `_default_permission_rules()` now returns **two** active rules (`plan-dir-edit`,
  `bundle-cache-read`); `plan-dir-write` moved to `_RETIRED_DEFAULT_RULES` and is actively pruned, and
  the test was renamed accordingly. This was done by the later, unrelated commit `2cd1a19c` (#1337).
  Recorded here so a reader comparing the archived report to HEAD does not mistake normal drift for a
  landing defect. → no action.
