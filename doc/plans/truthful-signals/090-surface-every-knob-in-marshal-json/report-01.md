# Run report — surface-every-knob-in-marshal-json (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/marshal-json-surface-knobs-3iptyb` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (working contract; loaded first).
- `plan-marshall:ref-code-quality` (always).
- `pm-plugin-development:plugin-script-architecture` (always).
- `plan-marshall:persona-implementer` (production-code work identity).
- `pm-dev-python:python-core` (Python production code).
- `pm-dev-python:pytest-testing` (Python tests).

All loaded by reading the bundle-source path (the `plan-marshall` plugin is not installed in this cloud session). `pm-documents:ref-asciidoc` was NOT loaded as a separate skill read — the AsciiDoc change is a single additive section following the file's existing table conventions; noted here for transparency.

## Claim-label verification (every claim was HYPOTHESIS at authoring; verified this run)

| Claim | Verdict | Evidence |
|---|---|---|
| `DEFAULT_ORCHESTRATOR == {'auto_emit': False}` | CONFIRMED | `_config_defaults.py:221-223` (by symbol). |
| `parallelization_scope` validated, settable, consumed, yet `get` returns `set:false` | CONFIRMED | validator `validate_orchestrator_block` + `_validate_parallelization_scope`; settable via `ORCHESTRATOR_SCALAR_FIELDS`/`cmd_orchestrator_set`; consumed by marshall-orchestrator init ask pre-fill (`init.md` Step 4) and the `next` verb; `cmd_orchestrator_get` falls back to `DEFAULT_ORCHESTRATOR.get('parallelization_scope')` = `None` today → `value:null, set:false` (existing `test_orchestrator_get_unset_reports_none`). |
| `effort` is a legal writable key never seeded | CONFIRMED | `validate_orchestrator_block` `known_keys` `{effort, parallelization_scope, auto_emit}`; writer `_set_orchestrator_effort` + `ORCHESTRATOR_EFFORT_SET_KEYS`; absent from `DEFAULT_ORCHESTRATOR` (asserted absence — verified). |
| Two code comments present unset-ness as deliberate design | CONFIRMED | `_config_defaults.py:1105-1118` ("the `effort` sub-block and the `parallelization_scope` scalar stay unset (implicit defaults) so … every orchestrator reader falls through to today's values") and `:1296-1300` ("effort + parallelization_scope stay unset (implicit defaults)"). |
| Recipe Aspect 1 requires materialising code-side defaults | CONFIRMED (read before relying) | `.claude/skills/recipe-marshal-json-config-audit/SKILL.md:74-76` — "flag any that exists in code but is absent from the file … The deliverable materialises the missing defaults." |
| Fall-through values are `plan.effort`, unset-`max` no-op, hard-coded scope `1` | CONFIRMED, must preserve | `_resolve_orchestrator_level` (`_cmd_effort.py:270-333`): absent `effort` → `plan.effort`; `_clamp_level` no-op when `max` unset. `parallelization_scope` fall-through: `init.md` Step 4 Branch A — `set:false` ⇒ ask keeps hard-coded `1`. |
| A consumer at an older version carries `{"auto_emit": false}` | ACCEPTED as motivation; also corroborated | Not reachable from clone. Corroborated as a genuine legacy shape: the pre-change seed WAS exactly `{'auto_emit': False}` (old `test_orchestrator_seed.py` assertion). D5(c) covers the compatibility requirement. |
| Further code-default-but-not-in-file gaps beyond orchestrator | REFUTED (no further gaps) | D4 sweep below. |
| No existing mechanism already materialises these defaults | CONFIRMED (asserted absence verified) | `get_default_config()` copies `DEFAULT_ORCHESTRATOR` verbatim; `sync-defaults` deep-merges from `get_default_config()` — both only ever surface what `DEFAULT_ORCHESTRATOR` contains. No other seeding path. |

## D1 GATE decisions

- **(a) Value vs placeholder:** VALUE-materialisation. `parallelization_scope: 1` (its effective default). No null placeholder.
- **(b) `effort` sub-block surfacing:** materialised as an **empty object `{}`** — the *only* behaviourally-inert option. The effort surfaces fall through to `plan.effort` (operator-configurable); seeding concrete effort leaves (e.g. `default: level-3`) would sever that coupling and change behaviour whenever `plan.effort` ≠ the baked-in value. An empty `{}` surfaces the KEY (a reader sees the sub-block exists) while `_resolve_orchestrator_level` finds no surface/`default`/`max` and falls through to `plan.effort` exactly as an absent key does. The leaf sub-keys (analyze/decompose/reader/default/max) cannot be value-materialised without a behaviour change, so they are surfaced in documentation (data-model.md already; configuration.adoc added this run) rather than in the seed.
- **(c) No-behaviour-change invariant + named test:** CONFIRMED preservable. Named tests: `test_materialised_effort_resolves_identically_to_unset` (effort half — asserts the seeded block and a legacy `auto_emit`-only block resolve every surface identically, using a **non-default** `plan.effort=level-5` to prove the fall-through coupling survives) and `test_materialised_scope_resolves_identically_to_unset` (scope half — encodes the ask-prefill `value if set else 1` contract, asserts both worlds yield `1`).
- **D4 split decision:** D4 does NOT split. Gap list beyond this plan's instance is empty (sweep below).

## D4 sweep — population and result

**Population:** every module-level `DEFAULT_*` / `*_DEFAULTS` constant in `_config_defaults.py` (17 constants): `DEFAULT_SYSTEM_DOMAIN`, `DEFAULT_SYSTEM_RETENTION`, `DEFAULT_PROJECT`, `DEFAULT_ORCHESTRATOR`, `DEFAULT_OPEN_IN_IDE`, `DEFAULT_PLAN_COVERAGE`, `DEFAULT_FINDING_RAW_INPUT_MAX_BYTES`, `DEFAULT_LANE_PRUNE_THRESHOLDS`, `DEFAULT_PLAN_EFFORT`, `DEFAULT_PLAN_INIT`, `DEFAULT_PLAN_REFINE`, `DEFAULT_PLAN_OUTLINE`, `DEFAULT_PLAN_PLAN`, `DEFAULT_PLAN_EXECUTE`, `DEFAULT_PLAN_FINALIZE`, `BUILD_SYSTEM_DEFAULTS`, `DEFAULT_BUILD_QUEUE`.

**Trace against `get_default_config()`:** 15 constants are fully seeded into the returned config (each key materialised, including the lazily-seeded `phase-5-execute.verification_steps` and `phase-6-finalize.steps`). `BUILD_SYSTEM_DEFAULTS` is an **intentional, documented runtime-only exclusion** ("build_systems is NOT included — determined at runtime via extension discovery"; the constant is "detection reference only") — not a gap. `DEFAULT_ORCHESTRATOR` is the **sole code-default-but-not-in-file gap**: the block was seeded but two settable inner knobs (`effort`, `parallelization_scope`) were omitted.

**Result:** one gap (the orchestrator block, closed by D2 this run). No other `DEFAULT_*` block leaves a settable knob unseeded. D4 stays in this plan.

## D2 config-surface enumeration (config-design-principles.md Rule 4)

- **S1 — init/setup seed:** `get_default_config()['orchestrator'] = copy.deepcopy(DEFAULT_ORCHESTRATOR)` — flows automatically from extending the constant. Covered by D5(a).
- **S2 — sync-defaults back-fill (existing projects):** `_deep_merge_missing` recurses the `orchestrator` block and back-fills absent `effort:{}` + `parallelization_scope:1` non-destructively, preserving user overrides. No code change to the merge path. Covered by the sync-defaults tests.
- **Rule 4's three materialised-copy surfaces:** (1) external consumer repos' `.plan/marshal.json` — migrated by each repo's own local `sync-defaults` (the mechanism ships; no per-repo edit is possible or owed from here); (2) the self-hosting repo's own `.plan/marshal.json` — git-ignored and absent from this clone, picked up by a local `sync-defaults` (nothing to edit here); (3) any in-flight execution manifest — the change is behaviourally inert (D1(c)), so a stale snapshot resolves identically and there is nothing to reconcile.

## Deliverables

_(filled as implementation proceeds)_

## Build gate

_(pending)_

## Findings

_(pending — verification sub-agent, CI, PR review)_

## Reviewer participation

_(pending)_

## Cost

_(pending)_

## Contract check (Step 9)

_(pending)_

## What have we learned (Step 9)

_(pending)_

## Residue

_(pending)_
