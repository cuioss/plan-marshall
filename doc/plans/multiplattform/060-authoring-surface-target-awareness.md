> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The pm-plugin-development authoring surface is target-aware and rule-pack-declared

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper)
**Branch prefix:** chore — closing coupling residue in the authoring toolchain

## Problem

The `pm-plugin-development` bundle authors, validates, and fixes components — and much of that
surface is Claude-only or undeclared: the creator's generator emits Claude frontmatter with no
target resolution while the doctor's fixer is target-aware; validators and fix payloads carry
Claude schema/tool/model enums outside the declared rule-pack; the flagship frontmatter standard
states Claude parser rules, mounts, and settings paths as THE authoring standard; layout and
settings literals bypass the layout helpers; permission grammar is rendered in doc bodies; and an
outline-classification predicate table is written as Claude paths and keys. The full registry is
`doc/plans/multiplattform/reference/marketplace-audit.md` §M3–§M4.

## Goal

An author on any registered target gets correct frontmatter generation, validation, and fixes;
every Claude-specific rule in the bundle is either target-resolved or declared in the rule-pack;
and no pm-plugin-development file resolves or names the Claude layout outside the layout helpers.

## Deliverables

1. **D1 — Target-aware generation and validation** — `cmd_generate.py` resolves the target as
   `_cmd_apply.py` does; `cmd_validate.py`'s format/field/tool enums become per-target (or
   rule-pack-declared) and its skill-field enum is reconciled with `frontmatter-standards.md` and
   `fix-templates.json` (one schema, three surfaces agreeing); `fix-templates.json` drops its dead
   entries and its live payloads become target-keyed; `apply_array_syntax_fix` gates on the
   resolved target.
   *Done when:* generation/validation/fix tests pass per target (red-first for the new
   behaviour); the dead template entries are gone; the three-surface schema disagreement is gone.
2. **D2 — `frontmatter-standards.md` split** — the target-agnostic field semantics stay; the
   Claude parser rules, tool set, model aliases, color enum, mount paths, and settings-permission
   sections move to (or are marked as) Claude target material, with the doctor's
   `_analyze_skill_mode.py` pointer still resolving.
   *Done when:* the document separates agnostic semantics from per-target format, and the doctor
   passes.
3. **D3 — Rule-pack declaration closed** — `rule-provenance.md` names the undeclared members
   (`tool-coverage.md`'s 13-name vocabulary — single-sourced with `_KNOWN_TOOLS` as data —
   `askuserquestion-reachability`, `agent-glob-resolver-workaround`, the bash-chain /
   shell-substitution / tmp-redirect rules); `_BUILD_OUTPUT_PREFIXES` reads the prefix from the
   target's own mapping data instead of a core-owned table; `doctor-agents.md` stops stating the
   `target/claude/` literal; `resolve_runtime_target`'s fallback consumes the single default the
   epic's plan `010` establishes.
   *Done when:* the rule-pack row covers every rule keyed on Claude tools/runtime facts
   (re-derive by sweeping analyzers for tool names), and no core-owned per-target prefix table
   remains.
4. **D4 — Layout and store literals routed** — `_dep_index.py` project scope through
   `get_project_skill_roots()` (duplicate helper deleted; the orphan `--scope global` flag fixed
   or removed; `plugin-cache` CLI vocabulary renamed target-neutrally with an alias);
   `extension.py` Axis-D prefix supplied by layout resolution; `plugin-doctor` SKILL/commands-guide
   discovery prose names the layout op; `_plugin_pin_trap.py` consumes normalized store
   observations from a runtime query while its oracle stays put; the `lspServers` placeholder
   section is declared Claude-target material.
   *Done when:* no `.claude` literal or segment-wise construction remains in the bundle outside
   declared Claude-target material, verified by sweep.
5. **D5 — Settings/permission prose normalized** — the `ext-outline-workflow` human-gated
   classification keeps its intent but takes its predicate table from a per-target runtime query
   (change-types restatement folded); `plugin-task-plan`'s hook-semantics rationale reworded to
   the observable constraint; the permission-grammar doc twins (M4 list) state intent or are
   declared Claude examples; `harness` terminology replaced per principles §7.
   *Done when:* the M4-listed sites are reworded/routed and a `harness` sweep of the bundle is
   clean.

## Out of scope

- **`askuserquestion-patterns.md` scoping** — a §D target-specific-component candidate blocked on
  plan `020`'s mechanism plus its file-level extension; excluded so this plan does not invent a
  second scoping mechanism.
- **The doctor frontmatter validation of `targets:`** — plan `020` D4 owns it.
- **plan-marshall-bundle surfaces** — plan `070`'s surface.

## Expected surface

- `marketplace/bundles/pm-plugin-development/**` (the M3/M4-named skills and scripts)
- `test/pm-plugin-development/**`
- `marketplace/bundles/plan-marshall/skills/platform-runtime/**` only if D4/D5's runtime queries
  need a schema addition — recorded, made minimally

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `cmd_generate.py` has no target resolution while `_cmd_apply.py` is target-aware | OBSERVED | both files — re-read before D1 |
| `fix-templates.json`'s `missing-frontmatter`/`array-syntax-tools` entries are ignored by their consumer | OBSERVED | `_cmd_apply.py` — verify the ignore before deleting |
| The seven analyzer anchors are the complete segment-wise `.claude` set in the bundle | OBSERVED, set is a lead | re-derive by segment-wise probe over both quote styles |
| `--scope global` crashes in `_dep_index.get_base_path` | OBSERVED | run it; red-first test pins the fix |
| The runtime queries D4/D5 need fit existing ops | HYPOTHESIS | `platform-runtime/standards/contract.md` — a needed addition is recorded, not silent |

## Verification

- `./pw verify`; red-first tests for D1 and the `--scope global` fix.
- The bundle-wide `.claude`/`harness` sweeps from D4/D5, re-run at verification time.
- The pre-PR sub-agent **cold-reads** the split `frontmatter-standards.md` and reports whether a
  third-target author can tell which sections bind them — the split failed if not.

## Notes

- Not concurrent with `020` (plugin-doctor surface), `030` (`scan-marketplace-inventory.py`
  sits beside `_dep_index.py`), or `070` (both conditionally touch platform-runtime docs);
  concurrent with `040` and `050` (the `ext-triage-plugin` disposition standard is `050`'s,
  excluded here); `010` lands first so D3's default consumes its single source. Evidence:
  `doc/plans/multiplattform/reference/marketplace-audit.md` §M3–§M4.
