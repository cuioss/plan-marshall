# Run report — surface-every-knob-in-marshal-json (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/marshal-json-surface-knobs-3iptyb` (harness-assigned, kept as-is)    **PR:** [#1155](https://github.com/cuioss/plan-marshall/pull/1155)    **Outcome:** completed (conditions 1–3 met; auto-merge armed; landing delegated to the merge queue)

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

- **D1 (GATE) — done.** All verdicts recorded above (§ "D1 GATE decisions"). (a) value-materialisation; (b) `effort: {}`; (c) invariant confirmed, named tests `test_materialised_effort_resolves_identically_to_unset` + `test_materialised_scope_resolves_identically_to_unset`. D4 split decision: no split. Mutates nothing. Commit: n/a (analysis).
- **D2 — done** (commit `5d45dbd`). `DEFAULT_ORCHESTRATOR` now `{'auto_emit': False, 'effort': {}, 'parallelization_scope': 1}` (`_config_defaults.py`). `get_default_config()` deep-copies it (S1). `sync-defaults`' `_deep_merge_missing` back-fills existing projects (S2) with no merge-path change. Config-surface enumeration recorded above (§ D2). Verification: `test_seed_surfaces_every_orchestrator_knob`, `test_get_default_config_seeds_orchestrator_block_with_every_knob`, `test_sync_defaults_backfills_orchestrator_block`, `test_sync_defaults_backfills_new_knobs_into_legacy_block`.
- **D3 — done** (commit `5d45dbd`). Both defending comments rewritten (`_config_defaults.py` block comment before `DEFAULT_ORCHESTRATOR`; the comment before `validate_orchestrator_block`; the `get_default_config` inline comment) to state the default-surfacing rule + cross-reference recipe Aspect 1 / `config-design-principles.md`; the "(empty)" self-validate comment corrected. Cold-read (Step 6): PASS — see Findings. Verification: cold-read sub-agent.
- **D4 — done** (commit `5d45dbd`, analysis). Sweep across all 17 module-level `DEFAULT_*` constants; population + trace recorded above (§ D4). Sole gap = the orchestrator block (closed by D2). `BUILD_SYSTEM_DEFAULTS` = documented runtime-only exclusion. No split. Independently corroborated by the verification sub-agent (the orchestrator block is the only one whose settable-field whitelist is decoupled from its seed dict).
- **D5 — done** (commit `5d45dbd`). (a) `test_seed_surfaces_every_orchestrator_knob` + `test_get_default_config_seeds_orchestrator_block_with_every_knob` — both fail against the old `{'auto_emit': False}` seed (pin the fix). (b) `test_materialised_effort_resolves_identically_to_unset` (uses non-default `plan.effort=level-5` to prove the fall-through coupling survives) + `test_materialised_scope_resolves_identically_to_unset` (ask-prefill `value if set else 1` contract, both yield 1). (c) `test_validation_accepts_both_seeded_and_legacy_shapes` (genuine `{'auto_emit': false}` legacy fixture) + `test_sync_defaults_backfills_new_knobs_into_legacy_block`.
- **Docs — done** (commit `5d45dbd`). `configuration.adoc`: new `[#orchestrator-knobs]` section for the two newly-materialised keys + `orchestrator` added to the top-level surface list.
- **Declared collateral truthfulness fixes** (in-scope for a "truthful-signals" change; my change falsified these statements):
  - `data-model.md` (commit `5d45dbd`) — the section intro's "slots stay unset until written", the "block carrying only the seeded `auto_emit`" phrasing, and the Validation section's "seeded shape (`{"auto_emit": false}`)" all corrected to the surfaced three-key shape (legacy block still noted valid). Beyond the plan's literally-declared doc surface (`configuration.adoc`), but required: leaving them would reproduce the D3 defect in the canonical reference doc.
  - `_cmd_orchestrator.py` (commit `d711e88`) — `cmd_orchestrator_get` comment + docstring that said `parallelization_scope` "carries no seeded default, so its fallback is `None`" corrected (fallback is now `1`). Found by the verification sub-agent; the same misleading-comment archetype D3 targets.

## Build gate

Python changed (`git diff --name-only origin/main...HEAD -- '*.py'` → `_config_defaults.py`, `_cmd_orchestrator.py`, and four test files), so the gate took its full path.

- `./pw verify plan-marshall` (implementation commit): **clean** — mypy "no issues found in 274 source files", ruff "All checks passed!", SPDX passed, second lint pass clean; **15881 passed, 1 skipped** in 277.83s.
- `./pw quality-gate` (comment-fix commit): **clean** — mypy "no issues found in 389 source files" (only pre-existing `[annotation-unchecked]` informational notes), ruff "All checks passed!", SPDX passed, plugin-doctor `status: pass, total_issues: 0` across 33 rules.

## Findings

- **Cold read (Step 6, D3) — PASS.** Source: dedicated cold-read sub-agent, given ONLY the rewritten `DEFAULT_ORCHESTRATOR` comment + a hypothetical new settable-but-unseeded knob. Verdict: **SEED** ("a knob that is settable in code but absent from the seeded file is a default-surfacing gap, never an intentional omission"). The rewrite does not reproduce the defect. Disposition: no action needed.
- **Verification sub-agent (Step 6) — 1 finding, FIXED.** `_cmd_orchestrator.py` `cmd_orchestrator_get` comment/docstring said `parallelization_scope` "carries no seeded default, so its fallback is `None`" — false after D2 (fallback is now `1`). Low severity, comment-only. Disposition: **fixed** in commit `d711e88` (the load-bearing `set`-flag semantics preserved; behaviour unchanged). All other deliverables: PASS (D1–D5, docs, behaviour-preservation confirmed inert — the ask pre-fill keys off `set`, still `False` for a legacy unset field).
- **Verification note (not a defect) — `data-model.md` beyond declared doc surface.** Disposition: accepted and declared (see Deliverables § collateral fixes) — required to avoid reproducing the D3 defect in the canonical reference.
- **Re-verification (Step 6, post-fix) — 2 further findings, FIXED.** The focused re-verify confirmed the `_cmd_orchestrator.py` fix AND surfaced two more stale statements the seed change falsified in bundle docs **outside the original diff** (same misleading-signal archetype): `api-reference.md` (the "orchestrator" noun's "slots stay unset (implicit defaults)", the `get`-verb "or `null` when the field carries no seeded default", and the Fields-table `unset` default for `parallelization_scope`) and `SKILL.md` (the `get` "or `null` … (`parallelization_scope`)"). Disposition: **fixed** in commit `72f754e`. Both files document exactly the keys this plan surfaces, so they are in-scope per the plan's own out-of-scope wording. Closure verified two ways: an exhaustive post-edit grep across the `manage-config` bundle returns **zero** surviving "stay unset" / "null-fallback for parallelization_scope" / "seeded shape {auto_emit: false}" claims, and `./pw quality-gate` plugin-doctor reports `total_issues: 0` (`broken-relative-link: 0`, `literal-count-drift: 0`).
- **CI — clean.** `verify / conclusion` (the required check) = **success** on head `72f754e`; `verify/verify`, `verify/gate`, `review/review`, `dependency-review`, `generate-check` all success. `mergeable_state: unstable` (all required contexts passed; only the non-required `license/cla` is pending).
- **PR review — no actionable findings.** Inline review threads: 0. `cuioss-review-bot`: "PR contains tests; No security concerns identified; No major issues detected" (clean). `sourcery-ai` / `coderabbitai`: rate-limit notices only (no review of this diff). `cla-assistant`: CLA-not-signed notice — a **non-required** status (see Reviewer participation + the merge-gate disclosure). Nothing required a fix or a reply.

## Reviewer participation

Population derived from `author_login` in the registry docs (`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{sourcery,coderabbit,pr-agent}.md`), cross-named by `.github/workflows/pr-agent.yml`: `sourcery-ai`, `coderabbitai`, `cuioss-review-bot`.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "PR Reviewer Guide 🔍 — PR contains tests; No security concerns identified; No major issues detected" against the diff (a clean review over the diff). |
| `coderabbitai` | `rate-limited` | Published only a refusal notice: "Review limit reached … we couldn't start this review. Next review available in 59 minutes." No review of this diff. |
| `sourcery-ai` | `rate-limited` | Published only a refusal notice: "you have reached your weekly rate limit of 500000 diff characters." The review artifact carried no findings. |

**Coverage: 1 of 3.** Step 8 shortfall disclosure fired (see below). Rate limits are routine and outside our control — they change what the run **says**, never whether it merges.

## Cost

- **Tokens:** the main-session total is not exposed to the agent in this session. Observed sub-agent usage (from task-completion `<usage>`): deliverable-verification 118,322; cold-read 36,105; re-verification 77,708 subagent_tokens.
- **Wall-clock:** PR opened 2026-08-11T08:41:51Z; this check-in fired ~2026-08-11T09:48Z. Session start precedes PR creation; end is when the merge queue lands (delegated).
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does not share. The figures cannot be made comparable, so no parity is implied.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named in § Skills loaded (bundle-path reads; plugin not installed). |
| 2 Branch | Done — harness-assigned `claude/marshal-json-surface-knobs-3iptyb`, published on `origin`, kept as-is. |
| 3 Plan directory | Done — `doc/plans/truthful-signals/090-surface-every-knob-in-marshal-json/plan.md` exists and opens with the first-instruction block (verified present; no repair needed). |
| 4 Implement | Done — 5 commits, all carry the `Co-Authored-By: Claude` trailer; deliverables addressed. |
| 4 Per-commit gate | Done — each `*.py`-touching commit preceded by a clean gate (`./pw verify plan-marshall` for the implementation commit; `./pw quality-gate` for the comment fix), each confirmed `total_issues: 0` / empty `errors[]`. |
| 4 Pushed | Done — no unpushed commit remained before the report commit. |
| 5 Build gate | Done — Python changed → `./pw verify plan-marshall` clean (15881 passed, 1 skipped; mypy/ruff/SPDX/plugin-doctor clean). |
| 6 Verification sub-agent | Done — deliverable-verification + cold-read + focused re-verification; all findings fixed and recorded in § Findings. |
| 7 PR cycle | Done — PR #1155; both comment surfaces read; every comment dispositioned (none actionable). |
| 8 Merge gate | Conditions 1–3 met; reviewer shortfall disclosed (condition 4); auto-merge armed (SQUASH). Session cannot self-wake to watch the queue (send_later fired once as this check-in; further self-wake not guaranteed) → landing delegated to the orchestrator collect / merge queue. Completed, not partial. |
| 8 Bridge | Done — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | Done — this table. |
| 9 What have we learned | Proposal recorded below (headless run — no reachable operator to approve; not shipped). |

GitHub access path used: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/*`. A `/sync-plugin-cache` is **not owed** (machine-local build step; a cloud run neither performs nor owes it).

## What have we learned (Step 9)

**Proposal (recorded for operator consideration; not self-approved, not shipped — this is a headless cloud run with no reachable operator to approve a contract change).**

*Evidence from this run:* the Step 6 verification sub-agent, as the contract specifies it, is given "the diff under review" and checks the deliverables and collateral changes **within the diff**. But a change to a seeded default (or any value that documentation restates) can falsify prose in files the diff never touches. This run's seed change left three now-false statements standing — one in a touched file (`_cmd_orchestrator.py`, caught by the first sub-agent) and **two in untouched bundle docs** (`api-reference.md`, `SKILL.md`), which surfaced only because the *re-dispatch* prompt was widened to "scan for sibling stale statements bundle-wide." The contract's own Step 6 wording would not have caught the untouched-file cases.

*Proposed edit:* add a line to cloud-lane Step 6 — when the change alters a value, default, constant, or schema that documentation describes, instruct the verification sub-agent to sweep **beyond the diff** (the owning bundle/skill) for statements the change falsifies, not only the diff's own hunks. This generalises the "no undeclared collateral change" check into "no collateral statement the change made false, wherever it lives."

*Counter-consideration:* the contract's existing fix-then-re-dispatch loop did ultimately catch it, so this is a sharpening, not a hole. Presented for the operator to weigh; not shipped as a separate `chore/` PR because no operator is reachable in this run to approve it.

## Residue

- **`license/cla` pending (non-required).** `mergeable_state: unstable` confirms it does not block the merge queue. If the org intends the CLA to gate merges, a human (the PR author `cuioss-oliver`) may need to sign or trigger a recheck at cla-assistant; this is outside what the agent can do. Disclosed at the merge gate; does not hold the merge.
- **Reviewer rate limits.** `coderabbitai` (window reopens ~59 min) and `sourcery-ai` (weekly quota) did not review this diff. A future push would re-trigger them, but none is needed — `cuioss-review-bot` reviewed clean and CI is green. No re-request made.
- **Local plugin-cache sync owed to a developer machine.** This run edited `marketplace/bundles/**`; a local developer should run `/sync-plugin-cache` after this lands so their `~/.claude/` cache reflects the change. The cloud run neither performs nor owes it (§ Contract check).
- **Landing confirmation delegated.** Auto-merge is armed on a green required check; the merge queue lands it and the orchestrator's collect step reads `state: MERGED` from the PR merge event. The squash-merge SHA does not exist until then, so it is reported to the operator, not embedded here.
