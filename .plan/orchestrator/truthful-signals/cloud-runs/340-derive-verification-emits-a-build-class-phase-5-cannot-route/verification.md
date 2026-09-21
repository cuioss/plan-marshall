# Verification — 340-derive-verification-emits-a-build-class-phase-5-cannot-route

**Verified against:** commit `2402b02bf5bc64b5ece468b6d2a3e884b5f0b30d`   **Landed as:** PR #1222, commit `ebd001860f536a60b07bc712844a1a4146107cc1`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and `report-01.md` in full. Located the squash-merge commit
(`git log --oneline --all --grep '#1222'` → `ebd00186`, contained in `main`), read its
`--numstat --find-renames` footprint (9 paths) and the full diff of the router
(`manage-execution-manifest.py`) and the provenance gate (`_manifest_validation.py`).

Files opened at HEAD (by symbol, not by grep-hit alone):

- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` —
  `_resolve_verbs_for_build_class` (L396), `cmd_derive_verification` (L416, return at L476, `status` at L477).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` —
  `_route_task_verification_commands` (docstring L1197-1235, carve-out L1288-1314), the
  `check_emitted_steps_resolvable` call site (comment L2296-2306, call L2307-2312, error return
  L2313-2327).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` —
  `_build_step_marshal_key_map` (L724), `check_emitted_steps_resolvable` (L743-836).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py` —
  `_VERB_TO_PHASE_5_STEP` (L920) and its preceding comment block (L893-919), `_verb_to_phase_5_step` (L991).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py` —
  `_CANONICAL_TO_ROLE` (L332).
- `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py` —
  `_compute_execution_tier_fields` (L359-381).
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/_extension_constants.py` —
  `ALL_CANONICAL_COMMANDS` (L31), `BUILD_CLASSES` (L69).
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py` —
  `ExtensionBase.classify_build_class` (L1342-1393).
- `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/extension.py` — `classify_globs` (L219).
- Docs: `manage-execution-manifest/SKILL.md` (L181, L543, L681-690), `standards/decision-rules.md` (L523),
  `phase-4-plan/SKILL.md` (L762, L798), `phase-5-execute/SKILL.md` (L991).
- Test: `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` (L858-1055).

Commands run:

- `uv run python -m pytest test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py -o addopts="" -q`
  → **44 passed** (the report's post-fix figure of 43 predates its own round-1 remediation test).
- `uv run python -m pytest test/plan-marshall/manage-execution-manifest -o addopts="" -q` → **869 passed**.
- **Executed** `check_emitted_steps_resolvable` on real input for all three provenance branches and read the
  actual returned message strings (see "Deliverable-by-deliverable → D3").
- **Executed** `_route_task_verification_commands` against a live fixture, with
  `extension_base.ALL_CANONICAL_COMMANDS` temporarily extended by `'perf-suite'` at runtime, to test the
  plan's own D1 verification recipe ("adding a class to the registry makes it accept it without a second
  edit"): before → `mutated=1, phase_5=['verify:perf-suite']`; after the registry addition →
  `mutated=0, phase_5=[]` and the keep-decision log line; after reverting → back to routing. **Derived,
  not copied — confirmed at runtime.**
- **Executed** `_check_step_resolvable(f'verify:{c}', 'phase_5')` over every entry of
  `ALL_CANONICAL_COMMANDS` to derive the exact carve-out coverage (see G3).

Mutations applied (each: `git diff --quiet` checked clean first, byte-copy snapshot into the scratchpad,
mutate, run, restore from the snapshot, re-check `git diff --quiet` → clean; never `git checkout`):

1. `manage-execution-manifest.py` — disabled the carve-out predicate
   (`if verb in ALL_CANONICAL_COMMANDS …` → `if False and …`). Result: **3 failed, 41 passed**;
   `test_mixed_task_composes_without_unresolvable_step` reproduced exactly the pre-fix state the report
   claims (`phase_5 == ['verify:compile', 'verify:module-tests']`). Restored.
2. `_manifest_validation.py` — disabled the phase-5 provenance gate (`if phase == 'phase_5':` →
   `if False and …`). Result: **1 failed, 43 passed** — `test_routed_step_error_names_routing_origin`
   went red. Restored.
3. *(added at adversarial review)* `manage-execution-manifest.py` — widened the carve-out to accept every
   verb (`if verb in ALL_CANONICAL_COMMANDS and …` → `if True or …`), to test whether the D4 routable
   control actually guards against an over-broad fix. Result: **4 failed, 40 passed** —
   `test_custom_verb_still_routes_and_fails_loud` plus the three `TestRouteUnmappedOrchestratorVerbs`
   tests. `test_module_tests_still_routes` stayed **green**. Restored.

Both guards are therefore **non-vacuous**. No file other than this one and `gaps.md` was left modified.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: re-derive the defect at HEAD by symbol | emission + compose sites read by symbol; defect confirmed or refuted | yes | yes | yes | yes | Every symbol the report names exists and says what the report says: `_resolve_verbs_for_build_class` (`_cmd_client_handlers.py:396`), `cmd_derive_verification` (`:416`), `_VERB_TO_PHASE_5_STEP` (`_manifest_rules.py:920`, 4 keys), `_CANONICAL_TO_ROLE` (`_manifest_core.py:332`, 6 keys, no `compile`/`test-compile`), `_compute_execution_tier_fields` (`_cmd_client_build.py:381` — `tier = 'per_task' if (measured and not exceeds) else 'orchestrator'`). Defect reproduced empirically by mutation 1. |
| D1 | Constrain the emitter to routable classes only, registry-derived | validates against the registered route set derived from that registry | **superseded** (re-scoped, operator-approved) — the equivalent fix landed on the router | yes | yes | yes | Emitter unchanged. Router carve-out `manage-execution-manifest.py:1301` gates on `verb in ALL_CANONICAL_COMMANDS` imported from `extension_base` (`_extension_constants.py:31`) — no hand-listed `{compile, test-compile}` anywhere (`grep ALL_CANONICAL_COMMANDS` → 2 hits, both this predicate + its import). Registry-derivation confirmed at runtime (see Method). |
| D2 | Make the emitter's status honest | status reflects the payload | **superseded / moot** | n/a | n/a | yes, by construction | `cmd_derive_verification` still returns `status: 'success'` unconditionally (`_cmd_client_handlers.py:476-477`). This is now truthful: `BUILD_CLASSES` is the closed set `{compile, module-tests, verify, none}` (`_extension_constants.py:69`), `_resolve_verbs_for_build_class` emits only `compile` / `test-compile` / `module-tests` / `verify`, and each of those four now has a route (fast path for `module-tests`/`verify`, carve-out keep for `compile`/`test-compile`). No emittable payload is unroutable. |
| D3 | Compose error names its provenance | next instance diagnosable at the point of failure | yes | yes | yes | **no — see G4** | `_manifest_validation.py:783-832`. Real message read by execution, not by inspection (below). Non-vacuous per mutation 2. The split itself is correct; the `base_reason` it wraps is not — see **G4**. |
| D4 | Matched control pair | both pass; each seen to fail pre-fix | yes (with a disclosed deviation) | mostly | yes | yes | `test_compose_execution_tier.py:858` `TestBuildPhaseCanonicalCarveOut` (5 tests) + `:1004` `TestUnresolvableStepProvenance` (3 tests). 44 passed; mutation 1 turns the unroutable half red; mutation 2 turns the provenance test red. |

**D1 / D2 — superseded, not implemented as written.** The plan's out-of-scope section explicitly flagged
this case ("If D0 finds [the emitted class is legitimate and the router is wrong], say so and re-scope"),
and the report says so, records an `AskUserQuestion` escalation and the operator's answer
("Router fix + provenance"), and the landed commit message repeats it. The emitter
(`_cmd_client_handlers.py::cmd_derive_verification`) is byte-unchanged by this plan. The plan's stated
**goal** — "an emitter cannot produce a `build_class` that has no route" — is satisfied from the other
side: every class the closed `BUILD_CLASSES` enum permits now has a route. The `AskUserQuestion`
exchange itself is not verifiable from the tree.

**D3 — provenance verified by reading actual errors.** Executing
`check_emitted_steps_resolvable(['verify:compile'], [], marshal_map, None)` at HEAD returns:

- `marshal_map={}` (routed): ``phase_5 step `verify:compile` is unresolvable: … This step was appended by
  execution_tier COMMAND routing from a derived `verification.commands` entry (architecture
  derive-verification) — it is NOT authored in marshal.json``. A reader gets both the emitter
  (`architecture derive-verification`) and the class (embedded in the step id, `verify:compile`).
- `marshal_map={'verify:compile': {}}` (authored): ``phase_5 step `verify:compile` in marshal.json is
  unresolvable: …`` — the control message, with no routing attribution.
- `marshal_map=None` (CSV fallback): identical to the authored wording — see G2.

**D4 — the "each seen to fail pre-fix" clause is met only in part, and the report discloses this.** The
routable control (`test_module_tests_still_routes`, `test_custom_verb_still_routes_and_fails_loud`,
`test_marshal_authored_step_error_names_marshal_json`) passes both pre- and post-fix by design; it is an
over-broad-fix guard, not a regression witness. That is the correct shape under the router-fix direction
and the report states it plainly rather than claiming otherwise. The plan's stronger requirement — *"the
routable half is not optional"* — is met, but by ONE of the two controls, not both. Mutation 3 below
(carve-out widened to accept every verb) turns **`test_custom_verb_still_routes_and_fails_loud`** red;
`test_module_tests_still_routes` stays **green**, because `module-tests` resolves through the
`_VERB_TO_PHASE_5_STEP` fast path (`_manifest_rules.py:920-925`) and never reaches the carve-out branch
at all. An earlier revision of this document claimed both would break — that claim was made by reading
the tests rather than by running the mutation, and it is wrong.

## Report accuracy

Re-derived at HEAD:

- **Symbol claims — all accurate.** Every symbol and every quoted mapping in the report's D0 section
  exists and reads as stated. Report line numbers carry `≈` and have drifted by ~13 lines in
  `_cmd_client_handlers.py` (383→396, 403→416, 463→478) because of a *later* commit (`c0b4f3e8`, PR #1252)
  — not a report error. `_CANONICAL_TO_ROLE` at `≈L332` is exact.
- **Empirical pre-fix claim — reproduced.** The report says the pre-fix phase-5 list was
  `['verify:compile', 'verify:module-tests']`. Mutation 1 produced exactly that list.
- **"`ALL_CANONICAL_COMMANDS` … derived from the vocabulary registry, not a hand-listed
  `{compile, test-compile}`" — confirmed**, and confirmed by *behaviour* (runtime registry-extension
  experiment), not only by reading the import.
- **Test counts.** The report's "43 passed" post-fix figure is superseded by its own round-1 remediation
  (which added `test_phase_6_absent_step_is_not_attributed_to_derive_verification`); the file collects
  **44** at HEAD. Not a contradiction — the report's own narrative explains the increment.
- **Two contradictions found** (the second added at adversarial review). Report § Findings round 2: *"Round 2's second tree-wide sweep confirmed no
  OTHER consumer of the retired universal contract remains"*, and § Residue: *"all documentation
  stale-claims are resolved"*. The in-code comment at
  `manage-execution-manifest.py:2296-2306` (the naming clause at `:2300-2302`), immediately above the
  `check_emitted_steps_resolvable` call at `:2307-2312`, still states the gate names *"the offending
  ORIGINAL marshal.json key and the phase (mapped back from the boundary-normalized emitted id via
  marshal_phase_{5,6}_map)"* — the exact pre-D3 universal claim the SKILL.md fix retired. See **G1**.
- **A second contradiction, found at adversarial review.** The same two report claims are also
  contradicted from inside `_manifest_validation.py` itself: the four `base_reason` literals at
  `:480`, `:668`, `:683` and `:706` still read ``step `X` referenced by `marshal.json` …``, which D3
  concatenates with its own *"NOT authored in marshal.json"* / *"composer-injected"* note. `git log -S`
  places those literals at `a11f6a7f`, and `git show ebd00186 -- _manifest_validation.py` shows only two
  hunks, both inside `check_emitted_steps_resolvable` — so the sweep never reached them. See **G4**.
- Report figures I could **not** re-derive: the full-suite counts (16448 / 16449 passed), the sub-agent
  wall-clock durations, the CI/bot review outcomes on PR #1222, and the branch commits `2430747` /
  `53c9926` / `a272be5` (squashed away by the merge; absent from this clone, as expected).

## Out-of-scope compliance

Clean. The landed footprint is 9 paths: the plan-file→plan-directory rename (0/0), the new `report-01.md`,
four `manage-execution-manifest/**` files, `phase-4-plan/SKILL.md` (1 line), and the test file — every one
inside the plan's declared Expected surface. `manage-architecture/**` was listed as expected surface but
**not touched**, which is the correct consequence of the re-scope, not a scope violation. The two declared
out-of-scope items were respected: the build-class vocabulary (`BUILD_CLASSES`, `ALL_CANONICAL_COMMANDS`)
is unchanged, and the routing *table* (`_VERB_TO_PHASE_5_STEP`, `_CANONICAL_TO_ROLE`) was not widened to
accept `compile`/`test-compile` — the fix carves those verbs *out* of routing instead. No collateral
change, no `uv.lock` churn in the diff.

## Residue carried forward

| Report residue item | Status in today's tree |
|---|---|
| Corpus lessons to retire by a local run (the duplicate cluster against `derive-verification` / `manage-execution-manifest` / `phase-4-plan`) | **Not verifiable** — the lessons store lives under the git-ignored `.plan/`; the plan itself forbade looking. Still open as far as this clone can tell. |
| Landing: auto-merge armed, merge commit not embedded | **Closed.** PR #1222 landed as `ebd00186`, contained in `main`. |
| "No open code or documentation items" | **Contradicted** by G1 and G4 (both inside `manage-execution-manifest/scripts/`, both restatements of the retired universal contract the round-2 sweep declared clean), and by G2; more marginally by G3. |

## What could NOT be verified

- The `AskUserQuestion` re-scope exchange and the operator's answer — no tree artifact records it; only
  the report and the commit message assert it.
- The `.plan/`-resident lessons corpus, the cluster record, and the "five lessons / eight instances"
  counts — unreachable from this clone by design.
- The full `./pw verify plan-marshall` figures and the three verification sub-agent passes — re-running
  the full build was out of proportion to this check; the targeted suites (44 and 869 tests) were run
  instead and are green.
- PR #1222's CI checks and reviewer participation (`cuioss-review-bot` reviewed, `coderabbitai` and
  `sourcery-ai` rate-limited) — not derivable from the tree.
- **Adjacent observation, deliberately not scored as a gap for this plan.** `manage-config`'s
  `per_deliverable_build` default is `['default:verify:compile', 'default:verify:module-tests']`
  (`_config_defaults.py:875`), i.e. the same `verify:compile` step id that
  `_check_step_resolvable(…, 'phase_5')` reports **unresolvable**. That list is consumed directly by
  `phase-5-execute` Step 10b (`architecture resolve --command compile --module M`), never fed through the
  composer's resolution gate, so it does not fail a compose today. It is nonetheless a second, differently
  resolving meaning for one step-id vocabulary — squarely inside this plan's declared out-of-scope
  ("Redesigning the build-class vocabulary"), and recorded here so a later plan can pick it up.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Re-verified at `e71e96a1` (no `marketplace/` or `test/` change between `2402b02b` and this
HEAD — `git diff --stat 2402b02b HEAD -- marketplace/ test/` is empty, so every figure below is
comparable to the original run).

*Re-derived by execution* (not by reading):

- `_check_step_resolvable(f'verify:{c}', 'phase_5')` over all 14 entries of `ALL_CANONICAL_COMMANDS`
  → 7 unresolvable (`clean`, `compile`, `test-compile`, `benchmark`, `install`, `clean-install`,
  `package`) / 7 resolvable. **G3's arithmetic reproduces exactly.**
- `check_emitted_steps_resolvable` on six inputs covering all four provenance branches; the authored and
  CSV-fallback messages compared by `==` at runtime → **byte-identical** (G2), and the three
  routed / composer-injected messages carry a `referenced by \`marshal.json\`` reason (G4, new).
- `_route_task_verification_commands` with `extension_base.ALL_CANONICAL_COMMANDS` extended by
  `'perf-suite'` at runtime: before → `mutated=1, phase_5=['verify:perf-suite']`; after → `mutated=0,
  phase_5=[]` + the keep-decision log line; after revert → back to routing. **The D1 registry-derivation
  claim reproduces exactly.**
- `pytest test_compose_execution_tier.py` → **44 passed**; `pytest .../manage-execution-manifest` →
  **869 passed**. Both figures reproduce.
- `test_compose_rejects_unresolvable_bundle_skill_step` re-run under an out-of-tree pytest plugin that
  wraps `check_emitted_steps_resolvable` and prints its arguments and return: both marshal maps are
  `None` and the shipped message contains two false marshal.json attributions. This is what raised G2
  from `low` to `medium`.

*Mutations applied* (each: `git diff --quiet` clean first, byte-copy snapshot to the scratchpad, mutate,
run, restore from the snapshot, `git diff --quiet` clean after — never `git checkout`): mutation 1
(carve-out disabled) → **3 failed, 41 passed**, `test_mixed_task_composes_without_unresolvable_step`
reproducing `['verify:compile', 'verify:module-tests']`; mutation 2 (provenance gate disabled) →
**1 failed, 43 passed**; **mutation 3, new** (carve-out widened to accept everything) → **4 failed,
40 passed**. All three reproduce or correct a claim in this document. Both touched files verified clean
afterwards.

*Verified by reading at symbol:* `_resolve_verbs_for_build_class` (:396) and `cmd_derive_verification`
(:416, return :476) in `_cmd_client_handlers.py`; `BUILD_CLASSES` (:69, 4 members) and
`ALL_CANONICAL_COMMANDS` (:31, 14 members) in `_extension_constants.py`; `_VERB_TO_PHASE_5_STEP` (:920,
4 keys) and `_verb_to_phase_5_step` (:991); `_CANONICAL_TO_ROLE` (`_manifest_core.py:332`, 6 keys, no
`compile`/`test-compile`); `_compute_execution_tier_fields` (`_cmd_client_build.py:359`, tier line :381);
`classify_globs` (`build-pyproject/scripts/extension.py:219`); `classify_build_class`
(`extension_base.py:1342`); `per_deliverable_build` (`_config_defaults.py:875`) and its sole consumer
(`phase-5-execute/SKILL.md:751-768`, `standards/canonical_verify.md:43-46`).

*Sweeps re-run with broader patterns than the original:* `grep -rn 'ALL_CANONICAL_COMMANDS'` over
`marketplace/` + `test/` → 9 hits, 2 of them in `manage-execution-manifest` (the predicate + its import),
confirming the "no hand-listed `{compile, test-compile}`" claim — and `grep -rn "'test-compile'"` over
`manage-execution-manifest/scripts/` and `phase-4-plan/` → **zero** hits, so no hand-list exists anywhere
on the routing surface. `grep -rn -i 'marshal.json key|marshal_key|offending .*marshal'` over
`marketplace/` + `test/` (broader than the original phrase sweep) → the only surviving universal claim is
G1's; `grep -rn -i 'no leaf ever runs an orchestrator-tier command inline|every orchestrator-tier build
command is hoisted'` → 2 hits, both in the router where the next sentence states the exception.
`grep -rn 'referenced by \`marshal.json\`'` → the 4 sites that became **G4**.

*Provenance of the landing:* `git log --all --grep '#1222'` → `ebd00186`, contained in `main`;
`git show --numstat --find-renames` → exactly the 9 paths this document lists, `_manifest_rules.py`
comment-only, `_VERB_TO_PHASE_5_STEP` / `_CANONICAL_TO_ROLE` unwidened, no `uv.lock` churn. The
report's `≈` line drift in `_cmd_client_handlers.py` is explained by `c0b4f3e8` (PR #1252), whose
numstat on that file is `+17/-4` — net `+13`, matching the observed 383→396 / 403→416 drift.

**NOT re-checked.** The full `./pw verify plan-marshall` figures (16448 / 16449); the sub-agent wall-clock
durations; PR #1222's CI checks and reviewer participation; the `AskUserQuestion` re-scope exchange (no
tree artifact records it — the D1/D2 supersession still rests on the report's and commit message's own
assertion, which is one source, not two); the `.plan/`-resident lessons corpus and the "five lessons /
eight instances" counts; `test_compose_execution_tier.py`'s other 36 tests beyond the 8 in the two D4
classes; the phase-5-execute leaf's actual runtime handling of a carve-out-kept orchestrator-tier command
(the documented rule exists at `persona-plan-marshall-agent/SKILL.md:71-78`, but no test was run against
it).

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| D0 | Symbols exist and say what the report says; defect reproduced | **upheld** | Every symbol re-read at HEAD; mutation 1 reproduces `['verify:compile', 'verify:module-tests']` |
| D1 | Superseded by an equivalent registry-derived router fix; "derived, not copied" | **upheld** | Runtime registry-extension experiment reproduced independently; 2 `ALL_CANONICAL_COMMANDS` hits; zero `'test-compile'` literals on the routing surface |
| D2 | Superseded / moot — no emittable payload is unroutable | **upheld** | `BUILD_CLASSES` (4 members) × `_resolve_verbs_for_build_class` (4 verbs) × route coverage re-checked at HEAD; line ref corrected `:478` → `:476-477` |
| D3 | Provenance split verified by reading actual errors | **re-scored `Complete? = no`** | The split is right; the `base_reason` it wraps is not — **G4** |
| D4 | Both controls guard against an over-broad fix | **rewritten** | Mutation 3: only `test_custom_verb_still_routes_and_fails_loud` goes red; `test_module_tests_still_routes` never reaches the carve-out (fast path, `_manifest_rules.py:920-925`) |
| G1 | Call-site comment still claims the universal marshal.json-key contract | **upheld**, line refs corrected | Comment is `:2296-2306` (clause `:2300-2302`), call `:2307-2312`; broader sweep found no other instance |
| G2 | CSV-fallback branch still asserts "in marshal.json" | **upheld, re-severitied `low` → `medium`** | Runtime `==` comparison shows byte-identity with the authored message; the branch is exercised today by a passing test whose fixture points `MARSHAL_PATH` at a non-existent file |
| G3 | Five sites render the carve-out as `{compile, test-compile}`; seven canonicals qualify | **upheld on the count, narrowed on the sites** | 7/7 split re-derived by execution; 2 of the 5 sites scope the pair to the deriver and are accurate → moved to § Refuted; `phase-4-plan/SKILL.md:797` → `:798`, router comment `:1289` → `:1290` |
| G4 | *(new)* `base_reason` hard-codes "referenced by `marshal.json`", contradicting D3's own note | **added, `medium`** | Three composed messages captured by execution; `git log -S` → `a11f6a7f`; `git show ebd00186` touches only `check_emitted_steps_resolvable` |
| Adjacent observation (`per_deliverable_build`) | `default:verify:compile` is unresolvable but never reaches the composer's gate | **upheld** | `_config_defaults.py:875` exact; consumer confirmed at `phase-5-execute/SKILL.md:751-768` and `canonical_verify.md:43-46` — a separate list from `verification_steps` |
| Verdict | `implemented-with-gaps` | **upheld** | See below |

**Verdict — upheld, with the reasoning made explicit.** Two of five deliverables (D1, D2) are not
implemented as written: `cmd_derive_verification` is byte-unchanged. That would normally make the plan
`partially-implemented`. It does not here, because the plan *pre-authorized* the reversal it took
("If D0 finds [the router is the wrong component], say so and re-scope") and the plan's **goal** — "an
emitter cannot produce a `build_class` that has no route" — is satisfied from the router side, which was
re-derived at runtime rather than argued. The load-bearing weakness in that reasoning is that the
operator approval for the re-scope has no tree artifact; a reviewer who declines to take the report's
word for it should read the verdict as `partially-implemented`.

**Documents corrected.** *verification.md*: mutation 3 added and the D4 over-broad-fix claim rewritten
(it was wrong); D3's `Complete?` re-scored to `no` with a pointer to G4; a second report contradiction
recorded; six line references corrected (`_cmd_client_handlers.py:478`→`:476-477`;
`_verb_to_phase_5_step` `L993`→`L991`; `_VERB_TO_PHASE_5_STEP` comment `L895`→`L893`; call site
`L2295-2326`→ comment `L2296-2306` / call `L2307-2312` / return `L2313-2327`; docstring
`L1200-1225`→`L1197-1235`; `phase-4-plan/SKILL.md L797`→`L798`; `SKILL.md L684-692`→`L681-690`); the
residue row now names G1+G4. *gaps.md*: G4 added; G2 re-severitied to `medium` with runtime evidence;
G3 narrowed from five sites to three and its two wrong line references fixed; a
`## Refuted during adversarial review` section added holding the two refuted G3 sites and the refuted D4
claim; open-item count 3 → 4.

**Residual doubt — what a third reviewer should look at first.**

1. **The leaf side of the carve-out.** The fix keeps an *orchestrator-tier* `compile` in a task's
   `verification.commands`, and the router comment justifies that as "the per_task fallback the leaf
   re-resolves live". The leaf-side rule exists in prose
   (`persona-plan-marshall-agent/SKILL.md:71-78`: an orchestrator-tier command must not be run inline;
   return control), but nothing in this plan's diff tests it, and `phase-5-execute/SKILL.md:991` says
   flatly that "per-task verification runs each task's pre-stamped `verification.commands`". If a leaf
   does *not* re-resolve, the carve-out has moved an orchestrator-tier build into a leaf — a behavioural
   regression this verification did not exclude.
2. **Whether G4 should be four rows rather than one.** Four literals, one predicate, one edit — recorded
   as one gap here, but a strict per-instance reading would split it.
3. **`await-long-running.md:13`** states the build consumer routes through the `marshalld` build server
   and explicitly does *not* use the detach-and-notify seam, while `canonical_verify.md:86` and
   `manage-execution-manifest/SKILL.md:698` both say orchestrator-tier steps go to `await-long-running`.
   Unrelated to this plan and deliberately not filed here, but it is the same class of defect.
