# Verification — surface-every-knob-in-marshal-json

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1155, commit `8f23d7d2`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding list is distinguishable from an unexamined one:

- Read `plan.md` and `report-01.md` in full; extracted all five deliverables with their *Done when* conditions, the out-of-scope list, the Expected surface, the claim-label table and the Verification section.
- Located the landed change: `git log --oneline --all --grep '#1155'` → `8f23d7d2`. Read the full landed diff (`git show 8f23d7d2 --stat`, and per-file for `_config_defaults.py`, `doc/user/configuration.adoc`). Confirmed the PR was squash-merged, so the report's branch SHAs `5d45dbd` / `d711e88` / `72f754e` do not exist in the mainline (`git cat-file -t` → absent for all three); only `8f23d7d2` does.
- Opened at HEAD: `_config_defaults.py` (lines 202–277 — the rewritten block comment, `DEFAULT_ORCHESTRATOR`, `ORCHESTRATOR_KNOWN_KEYS`; 1164–1182 — the second commentary site; 1185+ — `validate_orchestrator_block`; 1322–1325 and 1363–1369 — the two `get_default_config` comments), `_cmd_orchestrator.py` (`cmd_orchestrator_get`, `ORCHESTRATOR_SCALAR_FIELDS`, `_validate_parallelization_scope`), `_cmd_effort.py` (`_resolve_orchestrator_level`), `manage-config/standards/{api-reference,data-model,config-design-principles}.md`, `manage-config/SKILL.md`, `extension-api/standards/marshal-json-reference.md`, `plan-orchestrator/workflow/init.md` Step 4, `doc/user/configuration.adoc`, and `.claude/skills/recipe-marshal-json-config-audit/SKILL.md` § Aspect 1.
- Re-derived the D4 population by symbol: `grep -nE '^[A-Z_][A-Z0-9_]*(\s*:[^=]*)?\s*='` over `_config_defaults.py` filtered to `DEFAULT`/`_DEFAULTS` → **17** constants at HEAD, exactly the 17 the report names. (The pattern must tolerate a type annotation: `DEFAULT_SYSTEM_DOMAIN: dict[str, list[str]] = {` at `:35` is one of the 17, and an unannotated `^[A-Z_][A-Z0-9_]* =` pattern returns 16.)
- Re-derived the "only the orchestrator whitelist is decoupled from its seed" corroboration: every `reject_unknown_provisioning_field` call site (`_cmd_system_plan.py:80`, `:182`, `_cmd_orchestrator.py:95`, `:135`) — `system.retention` and `project` pass their own default dict as the whitelist, so they cannot drift; only `orchestrator` passes a separate tuple.
- Ran the tests: `UV_HTTP_TIMEOUT=600 uv run python -m pytest test/plan-marshall/manage-config/{test_orchestrator_seed,test_orchestrator_scope,test_sync_defaults,test_config_defaults}.py -o addopts="" -q` → **326 passed** in 39.7s.
- **Mutation check 1 (absence).** Restored `DEFAULT_ORCHESTRATOR` to the pre-plan `{'auto_emit': False}` and re-ran the same four files: **6 failed, 320 passed** — `test_seed_surfaces_every_orchestrator_knob`, `test_get_default_config_seeds_orchestrator_block_with_every_knob`, `test_seeded_orchestrator_leaves_effort_and_scope_resolution_unchanged`, `test_orchestrator_get_unset_reports_canonical_default`, `test_sync_defaults_backfills_orchestrator_block`, `test_sync_defaults_backfills_new_knobs_into_legacy_block`. D5(a) genuinely pins the fix.
- **Mutation check 2 (non-inert values).** Set the seed to `{'auto_emit': False, 'effort': {'default': 'level-3'}, 'parallelization_scope': 2}` and ran `-k materialised`: **both** D5(b) equivalence tests failed (`assert 2 == 1`; and the effort surfaces resolved to `orchestrator.effort.default` instead of `plan.effort`). The load-bearing invariant test is not vacuous.
- Both mutations were reverted by copying back the byte-identical file saved beforehand (md5 `306dd787a7414e489f0a1963734401e8` before and after); `git status --porcelain` shows no modification to any tracked file.
- Executed the config seed against the repo's own committed config: `uv run python -c` importing `_config_defaults.get_default_config()` and walking it against `.plan/marshal.json` → **3 keys missing from the committed file**: `orchestrator.effort`, `orchestrator.parallelization_scope`, and (unrelated, from another plan) `plan.phase-6-finalize.steps.default:emit-landing`.
- Checked sequencing: the epic's key-order plan (#1156, `10de4d12`, committed 09:46:46Z) is an ancestor of `8f23d7d2` (10:06:09Z) — the plan's "serialize, do not parallelize" note was honoured.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: settle what "expose every knob" means | three verdicts recorded, (c) names a test | yes (analysis) | yes | yes | yes | `report-01.md` § "D1 GATE decisions": (a) value-materialisation, (b) `effort: {}`, (c) invariant + two named tests. Both named tests exist and pass (`test_orchestrator_scope.py:283`, `:313`). |
| D2 | Surface the orchestrator block's knobs | a freshly seeded `marshal.json` carries all three | yes | yes | yes | **no** | `_config_defaults.py:255-259` = `{'auto_emit': False, 'effort': {}, 'parallelization_scope': 1}`; `get_default_config` deep-copies it at `:1369`. But the ⛔ "migrate ALL config surfaces" clause is unmet: Rule 4 surface 2 — the **tracked** `.plan/marshal.json` — still holds `{"auto_emit": false}` at HEAD (`git show HEAD:.plan/marshal.json`). See G1. |
| D3 | Correct the comments that defend the gap | neither comment can be read as authorising an unsurfaced knob | yes | yes | yes | yes | Four sites rewritten and present at HEAD: `_config_defaults.py:202-254` (block comment), `:1164-1182` (pre-validator comment), `:1322-1323` (self-validate, "(empty)" removed), `:1363-1368` (`get_default_config` inline). Each states the surfacing rule and cross-references recipe Aspect 1 / `config-design-principles.md`. |
| D4 | Sweep for other code-default-but-not-in-file gaps | gap list exists with its population; each gap closed or reasoned | yes | partially | yes for the denominator used | **narrow** | Population re-derived at HEAD = **17** `DEFAULT_*`/`*_DEFAULTS` constants, matching the report exactly. Corroborated independently: only `orchestrator` passes a whitelist decoupled from its seed dict. But the trace was run against `get_default_config()`, not against `.plan/marshal.json` — which is what recipe Aspect 1 (`.claude/skills/recipe-marshal-json-config-audit/SKILL.md:76`) actually names. Running it against the file finds 3 unmaterialised keys. Folded into G1. |
| D5 | Tests (a) surfacing, (b) no-behaviour-change, (c) legacy compatibility | all three hold; (c) against a legacy-shaped fixture | yes | yes | yes | yes | All seven named tests exist and pass (326 passed). Mutation 1: D5(a) tests go RED against the old seed. Mutation 2: both D5(b) tests go RED against a non-inert seed. D5(c) `test_validation_accepts_both_seeded_and_legacy_shapes` (`test_orchestrator_seed.py:208`) uses the literal `{'auto_emit': False}` — confirmed by the landed diff to be the exact pre-change seed, so it is a genuine legacy fixture, not a synthesised omission. |

**D2 (not a clean pass).** The code-side change is right and the fresh-seed path is right, but the deliverable carries an explicit ⛔ requiring that a default-shape change migrate ALL config surfaces, enumerated explicitly. The run enumerated them (report § "D2 config-surface enumeration") and dismissed Rule 4 surface 2 — the self-hosting repo's own `.plan/marshal.json` — on the stated ground that it is "git-ignored and absent from this clone". That premise is false: `.gitignore:45-47` ignores `.plan/*` but re-includes `!.plan/marshal.json`, the file is in `git ls-files`, `test/conftest.py:35` comments `.plan` as the "Tracked config sub-directory inside the repo", and `test_config_defaults.py:1865` already resolves `_COMMITTED_MARSHAL_PATH` for two committed-file regression tests (`:1995`, `:2016` — both key-order guards, neither a content guard). At HEAD the committed block is still `{"auto_emit": false}` and `git log -S 'parallelization_scope' -- .plan/marshal.json` returns nothing — the key has never been written there. The plan's own Goal ("a user reading their own config") and recipe Aspect 1 ("materialised in `.plan/marshal.json`") both point at exactly this file. See G1.

**D4 (narrow, not wrong).** The sweep is honest about its denominator — the report says "Trace against `get_default_config()`" in so many words — and every claim it makes about that denominator re-derives correctly. The narrowness is that Aspect 1's question is "does the code-side default reach the *file*", and answering "does it reach the seed dict" cannot detect a surface that was seeded once and never re-synced. Substituting the right denominator turns up the same gap G1 names, plus one key owed by a different plan (`plan.phase-6-finalize.steps.default:emit-landing`).

## Report accuracy

Re-derived every figure and checked every asserted absence:

- **Contradicted — the Rule 4 surface-2 disclaimer.** Report § "D2 config-surface enumeration" states: "(2) the self-hosting repo's own `.plan/marshal.json` — **git-ignored and absent from this clone**, picked up by a local `sync-defaults` (nothing to edit here)". Both halves are false. `.plan/marshal.json` is un-ignored by `.gitignore:46`, tracked (`git ls-files .plan` lists it), present in this clone, and already asserted against by two tests in the very file the run edited (`test_config_defaults.py:1995`, `:2016`). The conclusion drawn from the false premise ("nothing to edit here") is what left G1 open.
- **Imprecise — the closure grep's scope.** Report § Findings claims "an exhaustive post-edit grep across the `manage-config` **bundle** returns zero surviving 'stay unset' / 'null-fallback for parallelization_scope' / 'seeded shape {auto_emit: false}' claims". Those three literal phrases are indeed gone tree-wide (re-grepped: `stay unset|stays unset|implicit defaults` → 0 hits outside `doc/plans/`; `no seeded default` → only the correct hypothetical phrasings). But `manage-config` is a *skill*, not a bundle; the bundle is `plan-marshall`, and its sibling skill `extension-api` carries the canonical `marshal.json` reference, which still describes the two knobs as unseeded. See G2.
- **Verified — every other claim-label verdict.** `DEFAULT_ORCHESTRATOR` was `{'auto_emit': False}` before the change (landed diff), `parallelization_scope` was and is validated (`_validate_parallelization_scope`), settable (`ORCHESTRATOR_SCALAR_FIELDS = ('parallelization_scope', 'auto_emit')`) and consumed (`init.md` Step 4 Branch A, `orchestrate.md:50`); `effort` is a legal writable key absent from the old seed; recipe Aspect 1 says what the report quotes (`SKILL.md:76`, read directly); the fall-through values are as claimed (`_resolve_orchestrator_level` returns `plan.effort` when `orch_effort` is an empty dict, `max` unset ⇒ `_clamp_level` no-op; `init.md` Step 4 says "when `set` is `false`, keep today's hard-coded default suggestion of `1`").
- **Verified — the D4 population count.** 17 constants, re-derived by symbol at HEAD; the named list matches one-for-one.
- **Verified — the doc edits.** `configuration.adoc` `[#orchestrator-knobs]` section and the top-level surface list both present at HEAD (`:49`, `:56-67`); `data-model.md:222`, `:284`, `api-reference.md:157`, `:163`, `:170`, `SKILL.md:1066` all state the surfaced three-key shape and note the legacy block stays valid; `_cmd_orchestrator.py:82-83`, `:104-108` no longer claim a `None` fallback.
- **Not re-derived.** The build-gate figures ("15881 passed, 1 skipped", mypy "274 / 389 source files"), the CI check states, the reviewer-participation table and the token figures are run-time observations that cannot be reconstructed from the tree; nothing in the tree contradicts them.
- **Unresolvable, not contradictory.** The three branch SHAs cited per deliverable (`5d45dbd`, `d711e88`, `72f754e`) do not exist in the mainline because the PR was squash-merged into `8f23d7d2`. Expected for this lane; noted so a later reader does not chase them.

## Out-of-scope compliance

The landed diff stays inside the declared boundaries. No knob's semantics or default value changed — `parallelization_scope: 1` and `effort: {}` are the pre-existing effective defaults, proven inert by two independent routes (code read of `_resolve_orchestrator_level` + `init.md` Step 4; and mutation check 2, which shows the tests fail the moment a materialised value is *not* the effective default). The only documentation touched is for the keys this plan materialises. The key-ordering contract was not touched (`CANONICAL_TOP_LEVEL_KEY_ORDER` is untouched by `8f23d7d2`; it landed in #1156, an ancestor).

Collateral beyond the plan's declared surface: `_cmd_orchestrator.py`, `data-model.md`, `api-reference.md` and `SKILL.md`. All four are declared in the report with a reason, and each is a statement the seed change falsified. One rename in the diff (`090-...md` → `090-.../plan.md`) is the lane's plan-directory step. No undeclared collateral change found.

## Residue carried forward

- **`license/cla` pending (non-required).** Not verifiable from the tree; the PR merged, so it did not block.
- **Reviewer rate limits (`coderabbitai`, `sourcery-ai`).** Historical; nothing open in the tree.
- **Local plugin-cache sync owed to a developer machine.** Still applies to whoever pulls; unverifiable from the tree, and per CLAUDE.md the lane neither performs nor owes it.
- **Landing confirmation delegated.** Settled — the change landed as `8f23d7d2` and survives at HEAD unchanged in substance.
- **New residue, not declared by the report:** the committed `.plan/marshal.json` still carries the legacy orchestrator block. The report treated this surface as unreachable; it is reachable and still open. Raised as G1.
- **Superseded, not a gap:** the seed-completeness test now derives its expected key set from `ORCHESTRATOR_KNOWN_KEYS` (`_config_defaults.py:277`), introduced later by #1159 (`4faacf1b`, "derive orchestrator field-set guard from one authoritative source"). This strengthened, not weakened, D5(a) — the mutation check confirms it still fails against the old seed.

## What could NOT be verified

- The build-gate and CI figures quoted in the report (test counts, mypy file counts, plugin-doctor rule counts, check-run conclusions) — run-time observations with no tree artifact.
- The cold-read sub-agent verdict for D3. I read the rewritten comments myself and judge that they cannot be read as authorising an unsurfaced knob; the one clause a hostile reader could stretch — "the leaf sub-keys are surfaced in the documentation rather than the seed, because materialising them with values is what would break the fall-through" — is bounded by an objective test (does materialising change the effective default) and the leaves are in fact documented at `configuration.adoc:66`. I did not reproduce the cold read as an independent-reader experiment.
- The motivating claim that a consumer at an older version carries exactly `{"auto_emit": false}` — off-machine, as the plan itself says. Note the tree supplies an equivalent instance anyway: this repo's own committed config is in exactly that state.
- Whether any external consumer repo has since run `sync-defaults` — outside this clone.
- The token/wall-clock figures in § Cost.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap (G1), every clean-pass row (D1, D3, D5), and every "swept, clean" claim.
Specifically re-verified, by opening files and running code rather than by re-reading this document:

- **The tracked-ness of `.plan/marshal.json`** — `git ls-files .plan` lists it; `.gitignore:45-47`
  (`.plan/*` then `!.plan/marshal.json`) re-includes it; `test/conftest.py:35` carries the
  "Tracked config sub-directory inside the repo" comment verbatim.
- **The committed orchestrator block** — `git show HEAD:.plan/marshal.json` line 182-184 is
  `"orchestrator": {"auto_emit": false}`; the working copy is byte-identical at those lines;
  `git log -S 'parallelization_scope' -- .plan/marshal.json` returns no commit.
- **The three-missing-keys figure** — re-derived by *executing* `get_default_config()` (all bundle
  `scripts/` dirs on `sys.path`) and walking the result against the committed file. Output:
  `plan.phase-6-finalize.steps.default:emit-landing`, `orchestrator.effort`,
  `orchestrator.parallelization_scope`. Independently confirmed the seed carries
  `{'auto_emit': False, 'effort': {}, 'parallelization_scope': 1}`.
- **The `emit-landing` attribution** — the step is seeded dynamically by `_seed_finalize_steps()`
  (no literal in `_config_defaults.py`), is present in `get_default_config()`'s finalize step map,
  and is introduced by plan 302's report-01 § deliverables. The "owed by a different plan" clause is
  supported, not assumed.
- **The behavioural-inertness claim, by running the function.** `_resolve_orchestrator_level` was
  executed against both blocks with a non-default `plan.effort = level-5`, for `subkey = None` and
  each of `analyze` / `decompose` / `reader`: all eight calls return
  `('level-5', 'plan.effort', None)`. The seeded `effort: {}` is inert by execution, not by reading.
- **Mutation check 1, reproduced independently.** `git diff --quiet` on `_config_defaults.py` first
  (exit 0, md5 `306dd787a7414e489f0a1963734401e8` — the same md5 this document reports). Seed
  reverted to `{'auto_emit': False}`; the four test files gave **6 failed, 320 passed** with exactly
  the six test names listed above. Restored from the byte copy saved beforehand; md5 unchanged and
  `git status --porcelain` clean of it.
- **The 326-test figure** — re-run, `326 passed`.
- **The D4 population of 17** — re-derived by symbol, and the named list matches one-for-one.
- **The whitelist-decoupling corroboration** — all four `reject_unknown_provisioning_field` call
  sites re-read (`_cmd_system_plan.py:80`, `:182`, `_cmd_orchestrator.py:95`, `:135`);
  `ORCHESTRATOR_KNOWN_KEYS` is the only known-key constant in the whole `manage-config/scripts/`
  tree, so "only `orchestrator` is decoupled from its seed" holds.
- **The cited rule text, at the cited symbols** — recipe Aspect 1 (`SKILL.md:74-76`), Rule 4's three
  surfaces (`config-design-principles.md:109`, `:118`, `:123-126`, `:127-131`) and its
  "two most-forgotten surfaces" close (`:137-138`), `init.md` Step 4 Branch A, `orchestrate.md:50`.
  The report's Rule-4 enumeration maps surfaces 1 and 3 correctly — **only** surface 2 was dismissed
  on a false premise.
- **A broader closure sweep than the one this document ran.** Re-grepped the whole tree (not just
  `manage-config`) for `stay unset|stays unset|implicit defaults|no seeded default|not seeded|
  unseeded`, and separately for every `orchestrator` line in `marketplace/`, `doc/user/`,
  `doc/developer/` and `.claude/` matching `empty {}|hard-coded|unset|reserved|future|null`, and for
  every `auto_emit` mention in every `.md`/`.adoc`. The sweep confirms G2's three sites and G3's four
  sites and turns up **no further** stale statement: `effort-roles.md:84`,
  `orchestration-model.md:140`, `:199`, `status-lifecycle.md:143`, `data-model.md:253`, `:270` and
  `init.md` Step 4 all describe the *unset* case, which remains accurate for a legacy block.

**Not re-checked.** The build-gate and CI figures, the reviewer-participation table, the token/cost
figures (all run-time observations, as this document already says); mutation check 2 (the non-inert
seed) was not re-run — instead the equivalence tests were read in full and the same invariant was
confirmed by directly executing `_resolve_orchestrator_level`; the D3 cold read was not reproduced as
an independent-reader experiment.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | Committed `.plan/marshal.json` still hides both knobs; the report dismissed the surface on a false premise; severity `high` | **upheld**, fix rewritten | Tracked-ness, block contents, empty `-S` history and the three-missing-keys walk all reproduced independently. `high` re-tested against the rubric and kept: a shipped false factual premise plus no guard over the committed block's contents. |
| G1 Fix | "Equivalently, run `manage-config sync-defaults` … and commit the result" | **rewritten** | Not equivalent. `_cmd_sync_defaults.py:462-478` re-stamps `system.provisioned_version` and `system.config_seed_fingerprint` unconditionally, and the deep-merge also back-fills `default:emit-landing` — three extra committed-file changes owed by other plans. The Fix now names the scoped hand-edit as the route and flags the sync route's side effects. |
| G1 Fix | The two committed-file tests "enforce canonical key order" | **clarified** | True but load-bearing in a way the wording hid: both assert **top-level key order only** (`:1995` order, `:2016` save-round-trip), so neither is a content guard — which is exactly why the proposed new guard is needed. Line ref `:2015` corrected to `:2016`. |
| G2 | `marshal-json-reference.md:121`, `:145`, `:149` still describe the block as unseeded; severity `medium` | **upheld**, Done-when tightened | All three lines re-read at HEAD and quoted verbatim. The Done-when's "grep for statements implying …" was unrunnable judgement; replaced with a literal `grep -rniE` that today returns exactly those three lines and nothing else in the bundle. |
| G3 | Four sites call the shipped `auto_emit` a reserved/future PLAN-48 knob; severity `low` | **upheld** | `grep -rn "PLAN-48" marketplace/` returns exactly the four cited sites at the cited line numbers. `auto_emit` shipped in `1fad0868` (#996, "add orchestrator.auto_emit knob"), and is in `ORCHESTRATOR_SCALAR_FIELDS` (`_cmd_orchestrator.py:43`), `ORCHESTRATOR_KNOWN_KEYS` (`:277`) and `DEFAULT_ORCHESTRATOR`. `low` kept: `auto_emit` is not a key this plan newly materialised, so the drift is adjacent evidence, not a debt this plan owes. |
| D2 row | "not a clean pass" on the ⛔ migrate-ALL-surfaces clause | **upheld** | The Done-when itself ("a freshly seeded `marshal.json` carries all three") *is* met — confirmed by executing the seed. It is the ⛔ clause, not the Done-when, that fails. |
| D4 row | Population = 17 constants | **upheld, method corrected** | 17 re-derives, but only with an annotation-tolerant pattern; the command as originally written returns 16 because `DEFAULT_SYSTEM_DOMAIN` (`:35`) is annotated. Command corrected in § Method. |
| D5 row | Seven named tests exist and pass; D5(c) is a genuine legacy fixture | **upheld** | `326 passed` re-run; the six D5 test names re-located by symbol (`test_orchestrator_scope.py:283`, `:313`; `test_orchestrator_seed.py:162`, `:208`); `test_validation_accepts_both_seeded_and_legacy_shapes` validates the literal `{'auto_emit': False}` — the exact pre-change seed. Mutation 1 reproduced. |
| Report accuracy | Line refs `_config_defaults.py:200-252`, `:1164-1183`, `test_config_defaults.py:2015` | **corrected** | Actual spans are `:202-254`, `:1164-1182`, and `:2016`. Every other cited line (`:255-259`, `:277`, `:1185`, `:1322-1323`, `:1363-1368`, `:1369`, `.gitignore:46`, `conftest.py:35`, `SKILL.md:76`) re-derives exactly. |
| Verdict | `implemented-with-gaps` | **upheld** | Every one of the five deliverables' *Done when* conditions is met — including D2's, by execution. What fails is D2's ⛔ side-constraint and D4's denominator, which is `implemented-with-gaps`, not `partially-implemented`. |

**One hypothesis raised and refuted during this review** (recorded so it is not re-raised): the
committed file's `system.config_seed_fingerprint` is `714f8058` while `compute_config_seed_fingerprint()`
returns `58fc3cfc` at HEAD, which looked like a shipped false signal. It is not. The field is
documented (`data-model.md:526`, `:531`) as the seed hash the file *was last provisioned against*, so a
value that lags a later seed change is the field working, not failing. The related mechanism was also
checked before being relied on: `generate_executor preflight` derives `marshal_status` from
`marshal_version < config_changed_at_version` (`generate_executor.py:2203`, `:2253`), **not** from a
fingerprint comparison — so no "the fingerprint detector is firing and being ignored" claim is made.

**Documents corrected.** In `verification.md`: the D4 re-derivation command (16 vs 17), three
line-span references, and this section. In `gaps.md`: G1's Rule-4 citation sharpened to the exact
surface-2 lines, G1's Fix rewritten (the sync-defaults "equivalently" is false; the two existing
committed-file tests are order-only guards; `:2015` → `:2016`), the `emit-landing` attribution given
its evidence, G2's Done-when replaced with a runnable grep, and a `## Refuted during adversarial
review` section added recording that nothing was refuted and why the two contested severities stand.
No gap was added, deleted, or renumbered; the open count remains **3**.

**Residual doubt — what a third reviewer should look at first.**

1. **The D3 cold read is still unreproduced.** Neither this document nor the adversarial pass ran the
   experiment the plan's Verification section mandates. The clause to aim at is "the leaf sub-keys are
   surfaced in the documentation rather than the seed" — it is the one sentence in the rewritten
   comment that grants an exception to the absolute rule stated four lines above it.
2. **`test_seeded_orchestrator_leaves_effort_and_scope_resolution_unchanged`
   (`test_config_defaults.py:1974`) does not test resolution.** Its body asserts only that the seeded
   values are `{}` and `1`. Its docstring is honest about this and points at
   `test_orchestrator_scope` for the real equivalence, and that test does bite (verified by
   execution), so this is a name-overreach rather than a false green — but a reader scanning names
   would over-credit it.
3. **Whether the D4 denominator should have been wider still.** Both this document and the adversarial
   pass used "module-level `DEFAULT_*` constants in `_config_defaults.py`". Recipe Aspect 1's wording
   is "every config default `setup` / `marshall-steward` is supposed to write", which could reach
   defaults defined outside that file. No such default was found, but no exhaustive search for one was
   run either.
