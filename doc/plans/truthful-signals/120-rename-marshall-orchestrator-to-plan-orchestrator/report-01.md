# Run report — 120-rename-marshall-orchestrator-to-plan-orchestrator (run 01)

**Date (UTC):** 2026-08-11    **Branch:** claude/rename-marshall-plan-orchestrator-sz8x37 (harness-assigned)    **PR:** _pending_    **Outcome:** in progress

## Skills loaded

Read directly by bundle path (the plugin notation was not attempted; direct read is the always-works route in a fresh clone):

- `plan-marshall:ref-code-quality` — always-load work identity.
- `pm-plugin-development:plugin-script-architecture` — always-load (script/notation surface).
- `pm-plugin-development:plugin-architecture` — bundle/skill-directory structure surface.
- `pm-documents:ref-asciidoc` — `.adoc` concept-doc surface.

No skill was unreachable by both routes.

## Deliverables

**D0 — GATE: re-derive the surface at HEAD (mutates nothing).**
- Derivation population: `Grep` over the whole working tree (ripgrep, which honours `.gitignore`, so `.plan/` is excluded — consistent with D6).
- Hyphen token `marshall-orchestrator`: **265 matching lines across 74 files**. Underscore form `marshall_orchestrator`: **0** (no Python identifier uses it). Other-cased variants found in the initial sweep: the single uppercase identifier `_MARSHALL_ORCHESTRATOR_SKILL` (3 uses, one test file). ⚠ **The initial variant sweep was incomplete** — it did not cover the **space-separated title-case display form** `Marshall Orchestrator`, which survived in two `SKILL.md` H1 headings and was caught by the verification sub-agent (findings #1/#2 below, fixed). A later exhaustive `Marshall.Orchestrator` sweep confirmed exactly those two and no others.
- **Subset relation confirmed** (claim-label check): `persona-marshall-orchestrator` is a strict substring of `marshall-orchestrator`, so a single exact-token replace `marshall-orchestrator` → `plan-orchestrator` transforms BOTH skills and the 3-part notation, and the file count is the union (74), not a sum.
- **Classification** (rename-target vs must-not-touch): rename-target = all `marketplace/**`, `test/**`, `plugin.json`, `README.md`, live docs (`doc/concepts/**`, `doc/user/**`, `doc/adr/016`), living orientation doc `doc/plans/README.md`, and governance docs `CLAUDE.md` + `.claude/skills/cloud-plan-lane/SKILL.md` (each carried a now-stale `/marshall-orchestrator` command reference). Must-not-touch = records and other-plan specs under `doc/plans/**` (the 6 other pending specs + the 090 historical report + this plan's own `plan.md`/`report-01.md`) and the exclusion set.
- **Exclusion set derived, not assumed** — each confirmed to exist under its own name via `git ls-files`: `marshall-steward/` skill, `marshalld.py`/`_marshalld_*.py`, `marshal.json`, `plan-marshall` bundle. None contains the substring `marshall-orchestrator`, so the exact-token replace structurally cannot touch them.

**D1 — Rename the three directories** (commit `bd1f1cf`). `git mv` with history preserved; git detected all renames at 81–99 % similarity.

**D2 — Update every in-tree reference incl. 3-part notation** (commit `bd1f1cf`). Applied by an exact-token substitution over `git ls-files` (tracked files), excluding `doc/plans/**` except `README.md`. 65 files changed, 270 occurrences replaced. New notation `plan-marshall:plan-orchestrator:orchestrator` verified present (47 occurrences / 16 files); third segment `orchestrator` unchanged. Uppercase `_MARSHALL_ORCHESTRATOR_SKILL` → `_PLAN_ORCHESTRATOR_SKILL` (3×, one file).

**D3 — Cross-referencing skills + concept docs** (commit `bd1f1cf`). Updated: `platform-runtime`, `manage-logging`, `manage-status`, `manage-terminal-title`, `manage-config`, `extension-api`, `phase-6-finalize`, `manage-lessons`, `plan-retrospective`, `plan-marshall` (effort-roles); `plugin.json` + bundle `README.md`; concept docs `orchestration.adoc`, `personas.adoc`, `README.adoc`, `planning-workflow.adoc`, `doc/user/configuration.adoc`, `doc/adr/016`. (Concept-doc re-check pending sub-agent confirmation of `link:`/`xref:` targets.)

**D4 — Regenerate the executor.** Not performable in this cloud clone: the generated executor lives under `.plan/` (git-ignored, absent). The SOURCE of truth — skill directory names and every documented 3-part notation string — is updated, so a local regeneration (`/marshall-steward` / `/sync-plugin-cache`) will resolve `plan-marshall:plan-orchestrator:orchestrator`. Recorded as a local step owed (see Residue).

**D5 — Acceptance, each check verified.**
- **Zero remaining** `marshall-orchestrator` in rename-target scope: `marketplace/` → 0, `test/` → 0. Every surviving occurrence (9 files) is under `doc/plans/` (records + this plan's own docs).
- **Matched positive control** (the plan's single most important check): planted `marshall-orchestrator` in `marketplace/_positive_control_tmp.txt`; the sweep found it (and only it) → proves non-vacuity and correct tree targeting; removed it; `marketplace/` returned to 0.
- **Plugin-doctor gate clean**: `test_real_marketplace_quality_gate_has_zero_findings` PASSED inside `./pw verify`.
- **Full test suite green**: `./pw verify` → `18957 passed, 14 skipped`, `verify: SUCCESS`, no failure markers anywhere in output.
- **Exclusion set genuinely untouched, by name**: no `marshall-steward`/`marshalld`/`marshal.json` file appears in `git diff --name-only`; `plan-marshall` bundle name preserved (it is the first notation segment, unchanged). No double-replacement artifact (`plan-plan` → 0 real matches).

**D6 — `.plan/` ledger explicitly NOT rewritten.** Asserted as a non-goal: `.plan/` is git-ignored and absent from this clone, so its hundreds of historical orchestrator references are untouched and unreachable. In-tree records under `doc/plans/**` (other-plan specs + the 090 report) were likewise left as records, not source.

## Build gate

`git diff --name-only origin/main...HEAD` includes `*.py` (test files + `plan_logging.py`, `_cmd_orchestrator.py`, `_config_defaults.py`, `_orchestrator_inbox.py`, `orchestrator.py`), so the gate takes its full path: `./pw verify` → **SUCCESS, 18957 passed / 14 skipped**, plugin-doctor quality gate zero findings. No `uv.lock` or generated-file churn appeared (session interpreter met the project floor).

## Findings

Recorded per instance; source, description, disposition.

**Pre-PR verification sub-agent (run 1)** — verified against the plan's D0–D6; independently reproduced the zero-in-scope sweep, exclusion-set integrity, and the "purely cosmetic" store-key guarantee (`ORCHESTRATOR_STORE = 'orchestrator'` unchanged). Four findings:

1. **[MEDIUM → FIXED]** `plan-orchestrator/SKILL.md:8` H1 heading was still `# Marshall Orchestrator Skill` (space-separated title-case form the exact-token substitution did not match). Fixed → `# Plan Orchestrator Skill`.
2. **[MEDIUM → FIXED]** `persona-plan-orchestrator/SKILL.md:10` H1 heading was still `# Persona: Marshall Orchestrator`. Fixed → `# Persona: Plan Orchestrator`. After fixing, an exhaustive `Marshall.Orchestrator` sweep across the whole tree (excluding `doc/plans/`) returned **zero**, confirming #1/#2 were the complete title-case residue.
3. **[LOW → FIXED]** The report's D0 completeness claim understated the variant coverage (missed the title-case form). Corrected in the Deliverables §D0 above.
4. **[LOW/informational → DEFERRED, deliberate]** `plugin.json` skill arrays: the two renamed entries kept their old array positions, so they no longer sit in local alphabetical order. plugin-doctor does not gate ordering (gate clean), and the array is not strictly alphabetical to begin with (`ref-code-quality` already sits among `build-*`). Left un-re-sorted per the plan's minimal-collateral / "report-not-fix" posture — re-sorting would add review burden to a PR whose budget is verifying nothing changed. Recorded here transparently rather than silently fixed.

**False positives ruled out (not findings):** `plan-marshall orchestrator` (a space-separated descriptive phrase = bundle name + generic "orchestrator") in `manage-metrics/SKILL.md`, `extension-api/.../marshal-json-reference.md`, `doc/concepts/token-management.adoc`, and four `doc/resources/diagrams/*.svg` — pre-existing prose, NOT the renamed skill identifier, correctly untouched.

**Scope decision (recorded, not a defect):** `doc/plans/**` records/other-plan specs left untouched (29 occurrences preserved across 8 tracked files + this run's own docs), on the plan's "records are not source" (D6) / "report-not-fix" / "re-grounds exactly one spec" principles. `doc/plans/README.md` (living doc) and governance docs `CLAUDE.md`, `cloud-plan-lane/SKILL.md` updated. Sub-agent assessed this as "defensible, with one honest caveat: D5's literal 'zero under doc/' is not met" — the D5-vs-D6 tension was resolved in favor of D6 and recorded, not asserted as literal D5 compliance.

**Post-fix build:** `./pw quality-gate` after the heading fixes → mypy/ruff/SPDX clean, plugin-doctor `status: pass, total_issues: 0` (35 rules), including `broken-relative-link: 0` and `readme-skill-registration-drift: 0`.

- CI / PR review: _pending (post-PR)._

## Reviewer participation

_pending (post-PR)._

## Cost

_pending._

## Contract check (Step 9)

_pending (finalized as the last pre-merge commit)._

## What have we learned (Step 9)

_pending._

## Residue

- **Local regeneration owed (not a debt this cloud run can pay):** after this lands, the orchestrator command path is `plan-marshall:plan-orchestrator:orchestrator` and the old path stops resolving. Any local machine holding the old string needs the executor regenerated and the plugin cache synced (`/marshall-steward`, `/sync-plugin-cache`) before it works again.
- **Other-plan specs under `doc/plans/`** still name `marshall-orchestrator` in their expected-surface sections. Each such plan carries its own D0 gate and will re-ground against the settled surface when it runs; not this plan's to rewrite.
