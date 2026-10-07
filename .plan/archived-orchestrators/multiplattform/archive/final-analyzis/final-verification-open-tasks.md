= Final Verification — Open Tasks
:toc: macro

*DISPOSED — all 12 items below were closed by operator rulings recorded in
`final-verification-analysis.md` § "Operator Rulings". This document remains
as the record of what was asked, not of what is owed. Do not stage work from
it without re-opening a ruling.*

_Extracted from `final-verification-analysis.md` — only partially-implemented and still-open rows. +
Refuted rows excluded (see analysis for rationale)._

== Partially Implemented

=== 030-D2 — Settings-path reads delegate

*Source*: `030/plan.md` +
*Original requirement*: `_plugin_cache_root()` has exactly one permission-surface owner; the script no longer hardcodes the plugin path. +
*What was found*: Delegation exists — `permission_common.py` routes through `_active_runtime().permission_ensure_defaults()` and `layout_bundle_cache_root()` serves as the layout-op surface owner. The architectural intent (delegate to runtime, no caller-side hardcoding) is realized. +
*Missing*: The plan's named artifacts (`_plugin_cache_root_permission_surface.py`, `plugin_cache_root` constant) were never created. `extension_discovery.py:29-41` `get_plugin_cache_path()` still composes the cache root independently (env override + layout op) rather than sharing a single named owner with the permission scripts.

*Action*: Decide whether the current architecture (layout op is the implicit single owner; `get_plugin_cache_path()` duplicates the resolution logic) satisfies the intent, or consolidate `get_plugin_cache_path()` to use the same layout op path as `layout_bundle_cache_root()`.

---

=== 030-D5 — Display and filter strings stop naming `.claude/`

*Source*: `030/plan.md` +
*Original requirement*: The display string no longer contains `.claude/` and tests pass; `filter_keys` no longer contains `["commands"]`. +
*What was found*: `filter_keys` does not exist anywhere in the tree (grep: zero matches) — it was either renamed or removed entirely and cannot be verified. `.claude/` literals remain in plugin-doctor display code: `_claude_runtime_impl.py:2148-2149, 2204-2205, 2216-2224` contain `Path('.claude') / 'settings.json'` in display/detail strings emitted to the operator. +
*Missing*: (a) The `filter_keys` symbol's fate is unknown — search git history for PR #1319 to confirm whether it was implemented under a different name or dropped. (b) The `.claude/` display literals in `_claude_runtime_impl.py` remain.

*Action*: (a) Check git history / PR #1319 diff for `filter_keys` to determine whether the feature landed under a new name. (b) Evaluate whether the `_claude_runtime_impl.py` display strings are in scope (they live in the Claude runtime's plugin-doctor, which is Claude-target-specific by nature), and if they are, route them through a layout op or a label constant.

---

=== 040-D4 — distribution.adoc states the live matrix

*Source*: `040/spec.md` +
*Original requirement*: Distribution matrix includes both `claude` and `opencode` rows; opencode row carries `-✓-` across columns. +
*What was found*: Both rows exist in `distribution.adoc:84-98` with real values. However the `-✓-` token and `bundle-install` column from the spec's done-when were never adopted — the matrix documents distribution-target configuration, not a feature-support matrix.

*Action*: Decide whether the current matrix (both rows, real values, explicit verification status in prose at lines 100-109) satisfies the informational intent, or add a `bundle-install` column with `-✓-` status per target.

---

=== 050-D4 — Remaining normative tool-prose sites

*Source*: `050/spec.md` +
*Original requirement*: Zero `On Claude` / `On OpenCode` hits across the bundle. +
*What was found*: 13 distinct sites across 7 files remain. Approximately 10 are platform-runtime behavioral descriptions (session_id no-op, cache root, transcript behavior) — arguably legitimate target-aware contract prose. Approximately 3 name specific tool/directive targets (`/reload-plugins` directive in marshall-steward, tool calls `Edit / Write / Read / git -C` in ext-point-execution-context-workflow, `SessionStart` hook in contract.md).

*Action*: Triage the 13 remaining sites: (a) confirm which are legitimate per-target behavioral docs (keep), (b) convert which are tool-instruction prose to target-neutral directive language (rewrite), (c) update the done-when count to reflect the final clean state.

---

=== 060-D3 — Rule-pack declaration closed

*Source*: `060/spec.md` +
*Original requirement*: Canonical rule-pack list is a single source, referenced by `generate.py`, `plugin_doctor`, and `plugin-create`. +
*What was found*: Canonical list IS single-sourced in `rule-provenance.md:14-25`; `plugin_doctor` (19 references) and `plugin-create` (`cmd_validate.py`) reference it. `generate.py` does not reference the rule-pack — it manages target generation, not linting.

*Action*: Evaluate whether `generate.py` actually needs to reference the rule-pack (it does not run lint rules). If not, update the spec's done-when to match the current correct architecture: `plugin_doctor` + `plugin-create` only.

---

=== 060-D4 — Layout and store literals routed

*Source*: `060/spec.md` +
*Original requirement*: Layout literal policy pinned to one authoritative list constant; scripts read that list. +
*What was found*: Layout resolution IS routed through platform-runtime ops (`layout skill-roots` / `layout bundle-cache-root`); `marketplace_paths.get_project_skill_roots()` uses the layout op. No `STORE_LITERAL` constant exists (grep: zero matches).

*Action*: Evaluate whether the implicit single-sourced layout resolution (through the runtime op) is sufficient, or whether an explicit `STORE_LITERAL` constant is needed for documentation and for scripts that currently hardcode layout segments.

---

=== 060-D5 — Settings/permission prose normalized

*Source*: `060/spec.md` +
*Original requirement*: Permission rule authoring docs reflect current runtime; no lingering Claude-only settings references. +
*What was found*: Claude-only permission docs are properly scoped via "Provenance: Claude rule-pack" headers. The platform-neutral routing through `platform_runtime permission analyze` is in place. No OpenCode permission-architecture equivalent exists.

*Action*: Decide whether an OpenCode permission-architecture document is needed (the OpenCode permission model is honest no-ops, which is documented in `opencode_runtime.py:334-363` and pinned by tests). If yes, create the complementary document; if no, update the done-when to reflect the current state.

---

=== 080-D3 — Skills route through the registry

*Source*: `080/spec.md` +
*Original requirement*: Per-skill domain resolution via the registry working and documented; grep for `claude_runtime` across permission scripts returns zero. +
*What was found*: The architectural goal is fully met — `permission_common.py` imports `_runtime_for_target` from `platform_runtime`, not `claude_runtime`; OpenCode honest no-ops for every permission op; tests pin the no-op property. However, 4 `claude_runtime` mentions remain: 3 in docstrings and 1 function-local `isinstance` type check in `permission_common.py:49` (architecturally necessary for the truthful `is_claude_target()` gate).

*Action*: Evaluate whether the 3 docstring mentions and 1 isinstance check are acceptable type-level necessities (I believe they are — the isinstance check is the correct way to gate Claude-specific behavior at the type level). If acceptable, update the done-when to reflect "no settings-binding coupling" rather than "zero grep hits".

== Still Open

=== 050-D2 — Call-schema block neutralized

*Source*: `050/spec.md` +
*Original requirement*: The step-schema block reading "On Claude — `call git ...` / On OpenCode — `call bash ...`" replaced by target-neutral directive language. +
*What was found*: The target artifact does not exist in the tree and has no git history (`git log -S` returns empty for `call-schema`, `Call-schema`, `call git`, `call bash` step-schema patterns). The done-when cannot be verified against a concrete before-state.

*Action*: Determine whether the artifact ever existed (check PR history for 050-era commits) or whether the spec referenced a pre-existing artifact that was removed before the spec was authored. If it never existed, the done-when is vacuously satisfied (no block to neutralize). If it existed and was removed, confirm the replacement is target-neutral directive language and mark as complete.

---

=== 050-D3 — ext-triage escalation lines neutralized

*Source*: `050/spec.md` +
*Original requirement*: `plugin-escalation-from-triage` and `triage-escalation-to-plugin` blocks no longer carry `On Claude` / `On OpenCode` labels. +
*What was found*: The named blocks do not exist and have no git history. Current ext-triage SKILL.md files are already target-neutral. Same situation as 050-D2.

*Action*: Same as 050-D2 — determine whether the blocks ever existed, and if not, confirm the done-when is vacuously satisfied.

---

=== 080-D1 — The crossing inventory, and the stop condition

*Source*: `080/spec.md` +
*Original requirement*: A defined crossing inventory exists and a stop condition is stated. +
*What was found*: `coupling-inventory.md` does not exist in the version-controlled tree. `doc/plans/multiplattform/reference/` directory does not exist. The stop condition (grep for `claude_runtime` across permission scripts returns zero) is not met — 4 matches remain.

*Action*: Create the crossing inventory artifact and enumerate all runtime-crossing points in the permission skill scripts. Resolve the remaining 4 `claude_runtime` mentions (3 docstrings, 1 isinstance) — either document them as acceptable type-level necessities in the inventory or refactor them away.

---

=== 080-D4 — Retire the inventory rows by re-derivation

*Source*: `080/spec.md` +
*Original requirement*: Inventory rows retired after re-derivation. +
*What was found*: The inventory artifact does not exist; without it, no rows to retire.

*Action*: Blocked on 080-D1 — the inventory must be created first, then rows can be retired by re-deriving each crossing through the runtime registry.
