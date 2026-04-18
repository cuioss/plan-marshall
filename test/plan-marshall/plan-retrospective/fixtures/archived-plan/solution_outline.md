# Solution Outline: collect-fragments add/finalize should infer mode from bundle

plan_id: lesson-2026-04-18-13-001
compatibility: breaking
compatibility_description: Clean-slate approach, no deprecation nor transitionary comments

## Summary

The `collect-fragments.py` script currently requires `--mode {live|archived}` on every subcommand (`init`, `add`, `finalize`). Since the mode determines the on-disk path of the bundle and `init` creates the bundle, the mode is part of the bundle's identity and should be persisted inside it. This plan moves mode from a per-call argument to a bundle property: `init` writes mode into the bundle; `add`/`finalize` read it from the bundle and drop `--mode` from their argparse. This is a clean breaking change — `compatibility=breaking`, no downstream consumers outside this repo.

## Overview

**Scope:** 3 files in the `plan-marshall` bundle:

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-fragments.py` — script change (init persists mode, add/finalize read from bundle, argparse restructure)
- `test/plan-marshall/plan-retrospective/test_collect_fragments.py` — drop `--mode` from add/finalize test calls, add regression test for missing-mode-key error
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — drop `--mode` from Step 3/4 add/finalize example commands

**Key design decisions:**

- **Reserved key**: mode is stored under `_meta.mode` inside the bundle TOON (top-level key `_meta` with nested `mode`). Underscore prefix signals "internal metadata, not an aspect". `add` rejects aspects matching any reserved `_meta*` key.
- **Error path**: If `add` or `finalize` reads a bundle that is missing `_meta.mode`, raise `ValueError('Bundle missing _meta.mode — was it created by a compatible init?')`. No silent fallback.
- **argparse restructure**: split `_add_common_args` into `_add_init_args` (keeps `--mode`) and `_add_add_finalize_args` (no `--mode`). `--plan-id` and `--archived-plan-path` remain on all three subcommands.
- **Test surface**: existing tests drop `--mode live` / `--mode archived` from every `add`/`finalize` invocation (both subprocess-based CLI tests and direct `cmd_add`/`cmd_finalize` calls with `_ArgsNS`). `_ArgsNS` instances for add/finalize no longer carry a `mode` field.

## Deliverables

### 1. Persist mode in bundle and drop --mode from add/finalize

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: plan-marshall
- depends: none

**Profiles:**
- implementation
- module_testing

**Affected files:**
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/collect-fragments.py`
- `test/plan-marshall/plan-retrospective/test_collect_fragments.py`

**Verification:**
- Command: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "module-tests plan-marshall"`
- Criteria: All tests in `test_collect_fragments.py` pass. New regression tests for missing-meta and reserved-aspect-key pass.

---

### 2. Drop --mode from SKILL.md add/finalize example commands

**Metadata:**
- change_type: enhancement
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- module: plan-marshall
- depends: 1

**Affected files:**
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md`

**Verification:**
- Command: `grep -nE 'collect-fragments.*(add|finalize).*--mode' marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md`
- Criteria: Command returns no matches (exit code 1).
