# Gaps — 340-derive-verification-emits-a-build-class-phase-5-cannot-route

**Source:** verification.md (same directory)   **Open items:** 4

All four are statement-accuracy items. The three code deliverables (router carve-out, provenance split,
matched-pair tests) are implemented, correct, registry-derived, and non-vacuous under mutation — no
behavioural gap was found. Two of the four (G2, G4) are defects in **shipped runtime error text**, not
only in prose; G1 is maintainer-facing and G3 is documentation precision.

An independent adversarial review re-derived every figure below and added G4 — see
`verification.md` § "Adversarial review" for what was and was not re-checked.

## G1 — Correct the compose call-site comment that still claims the unresolvable_step error names the marshal.json key

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2296-2306` — the comment block immediately above the `check_emitted_steps_resolvable(...)` call in `cmd_compose` (the call itself is at `:2307-2312`; the offending naming clause is at `:2300-2302`)
- **What is wrong:** The comment states the gate "fails the compose loud, naming the offending ORIGINAL
  marshal.json key and the phase (mapped back from the boundary-normalized emitted id via
  marshal_phase_{5,6}_map)". D3 replaced that universal behaviour with a three-way provenance split
  (`_manifest_validation.py:783-832`): only a step present in the marshal step map is named by the
  author's key; a phase-5 step absent from the map is attributed to `architecture derive-verification`
  routing, and phase-6 gets a neutral composer-injected note. Executing the function confirms all three
  wordings. `report-01.md:206-208` claims "no OTHER consumer of the retired universal contract
  remains" and `report-01.md:317-318` claims "all documentation stale-claims are resolved" — this site
  contradicts both.
- **Why it matters:** This is the comment a maintainer reads while working on the gate itself. It sends
  them looking for a marshal.json key that, on the routed branch, deliberately does not exist — the exact
  diagnosability failure D3 exists to end, restated one function above D3's own code.
- **Fix:** Rewrite the comment's naming clause to describe the provenance split, mirroring the wording
  already agreed in `manage-execution-manifest/SKILL.md:181`: an authored step is named by the original
  marshal.json key (mapped back via `marshal_phase_{5,6}_map`); a phase-5 step absent from that map is
  named as routed from a derived `verification.commands` entry by `architecture derive-verification`; a
  phase-6 step absent from the map gets the neutral composer-injected note; the CSV-fallback path reports
  the emitted id. While there, extend the `_build_step_marshal_key_map` docstring
  (`_manifest_validation.py:724-733`) to mention the routed branch alongside the CSV-fallback degradation
  it already documents.
- **Done when:** No comment or docstring in `manage-execution-manifest/scripts/` states that the
  `unresolvable_step` message names the marshal.json key unconditionally; a grep for
  `offending ORIGINAL marshal.json key` returns nothing.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — compose resolution gate.

## G2 — Stop asserting "in marshal.json" on the CSV-fallback branch, where no marshal step map exists

- **Kind:** stale-statement
- **Severity:** medium (raised from `low` during adversarial review — the branch is exercised by a
  passing test today, so the false message is shipped, not hypothetical)
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py:822-832` — the `marshal_map is None` return in `check_emitted_steps_resolvable`
- **What is wrong:** When `marshal_map` is `None` — `_read_marshal_phase_step_map`
  (`_manifest_rules.py:29-46`) returns `None` when marshal.json is missing, unparseable, or carries no
  such key, and `_read_merged_phase_6_step_map` (`_manifest_rules.py:134-164`) propagates that `None`
  on the CSV-fallback compose path its own docstring names — the message still reads
  ``phase_5 step `X` in marshal.json is unresolvable``. Executed at HEAD:
  `check_emitted_steps_resolvable(['verify:compile'], [], None, None)['message']` is **byte-identical**
  to the genuinely-authored `marshal_map={'verify:compile': {}}` message (compared by equality at
  runtime, not by eye). The step is asserted to be in a file the composer just failed to read.
- **Why it matters:** D3's whole purpose was to stop the error misattributing a routed step to
  marshal.json. On this branch the misattribution survives, and it is the branch that fires precisely when
  marshal.json is absent — so the reader is sent to a file that may not exist at all. This is not
  hypothetical: the existing passing test
  `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_compose.py:4854`
  (`test_compose_rejects_unresolvable_bundle_skill_step`) runs under a `plan_context` fixture that points
  `MARSHAL_PATH` at a non-existent `tmp_path/marshal.json`, so **both** marshal maps are `None`; the
  message it produces today reads ``phase_6 step `plan-marshall:ghost-review` in marshal.json is
  unresolvable: step `plan-marshall:ghost-review` referenced by `marshal.json` …`` — two false
  marshal.json attributions in one line, with no marshal.json anywhere. (The inner half of that line is
  **G4**; this gap covers the outer wrapper clause only.)
- **Fix:** In the `marshal_map is None` branch (`_manifest_validation.py:824-832`), drop the "in
  marshal.json" clause and state the actual situation: ``phase_5 step `X` is unresolvable: {reason}. No
  marshal.json step map was available for this phase, so the step's origin (authored vs routed) could not
  be determined.`` Add a test beside `test_marshal_authored_step_error_names_marshal_json`
  (`test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py:1031`) asserting the
  `marshal_map=None` message does **not** contain `in marshal.json`.
- **Done when:** `check_emitted_steps_resolvable(['verify:compile'], [], None, None)['message']` no longer
  claims marshal.json origin, and a test pins that.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — compose resolution gate.

## G3 — Say that the carve-out covers seven canonicals, not the two it names

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:523`; `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:798`; the `_VERB_TO_PHASE_5_STEP` comment at `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py:900-904`
- **What is wrong:** Each of these three renders the general predicate with an inline, unqualified
  parenthetical — "a verb that is a known canonical build command (`compile` / `test-compile`) with no
  phase-5 verify gate" — which reads as the exhaustive carve-out set. The predicate is
  `verb in ALL_CANONICAL_COMMANDS and not _check_step_resolvable(f'verify:{verb}', 'phase_5')`.
  Evaluating `_check_step_resolvable` over every entry of `ALL_CANONICAL_COMMANDS`
  (`script-shared/scripts/extension/_extension_constants.py:31`, 14 entries) at HEAD gives **seven**
  unresolvable canonicals — `clean`, `compile`, `test-compile`, `benchmark`, `install`, `clean-install`,
  `package` — against seven resolvable ones (`module-tests`, `integration-tests`, `e2e`, `coverage`,
  `quality-gate`, `arch-gate`, `verify`). All seven are kept with the task, not two.
  ⚠ Two further sites originally listed here are **accurate and are excluded** — see § "Refuted during
  adversarial review".
- **Why it matters:** The general predicate *is* stated alongside the parenthetical, so behaviour is not
  in doubt — but a reader sizing the change, or writing a test that expects an orchestrator-tier `package`
  to route to `verify:package` and fail loud, will get it wrong. The set is also not static: it moves
  whenever a canonical gains or loses a phase-5 verify gate.
- **Fix:** In the three sites above, mark the pair as illustrative rather than exhaustive — e.g. "a known
  canonical build command with no phase-5 verify gate (today: `clean`, `compile`, `test-compile`,
  `benchmark`, `install`, `clean-install`, `package` — the deriver emits `compile` and `test-compile`)" —
  and state that the set is derived, so it follows the registry and the gate set without a doc edit. Do
  not hard-code the seven-item list as the contract; the derived predicate stays the authority.
- **Done when:** None of `decision-rules.md:523`, `phase-4-plan/SKILL.md:798`, or the
  `_VERB_TO_PHASE_5_STEP` comment presents `{compile, test-compile}` as the complete carve-out set; each
  names the derived predicate as the authority and the two deriver-emitted verbs as examples.
- **Module/topic:** `plan-marshall:manage-execution-manifest` (+ `phase-4-plan` SKILL.md) — execution_tier
  routing documentation.

## G4 — The unresolvable-step *reason* still hard-codes "referenced by `marshal.json`", so D3's provenance note contradicts its own message

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py` — four message literals that D3 did not touch: `:480` (`_check_step_loadable`, phase-6 built-in), `:668` (`_check_step_resolvable`, `project:` step), `:683` (phase-5 external `bundle:skill`), `:706` (phase-6 external `bundle:skill`). Each begins ``step `X` referenced by `marshal.json` …``. `check_emitted_steps_resolvable` (`:743-833`) concatenates one of these as `base_reason` with the D3 provenance note.
- **What is wrong:** D3 split provenance in the **wrapper** only. The `base_reason` it wraps still asserts
  the step is "referenced by `marshal.json`" unconditionally. `git log -S` places those literals at
  `a11f6a7f` ("feat(manifest): fail-loud compose-time step-resolution gate"), well before PR #1222, and
  `git show ebd00186 -- _manifest_validation.py` shows only two hunks, both inside
  `check_emitted_steps_resolvable`. The composed message therefore contradicts itself. Captured by
  execution at HEAD:
  - ``phase_6 step `bogus-finalize-step` is unresolvable: step `bogus-finalize-step` referenced by `marshal.json` is missing standards file … . This step is not authored in marshal.json (composer-injected)``
  - ``phase_6 step `project:ghost-skill` is unresolvable: step `project:ghost-skill` referenced by `marshal.json` resolves to no project-local skill … . This step is not authored in marshal.json (composer-injected)``
  - ``phase_5 step `plan-marshall:ghost-verify` is unresolvable: step `plan-marshall:ghost-verify` referenced by `marshal.json` is not a discovered ext-point-build-verify-step implementor … . This step was appended by execution_tier COMMAND routing … — it is NOT authored in marshal.json``

  The first of those is produced by the very test D3's round-1 remediation added,
  `test_phase_6_absent_step_is_not_attributed_to_derive_verification`
  (`test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py:1041`), which passes
  today: it asserts `'composer-injected' in message` and never notices that the same message says
  `referenced by 'marshal.json'`.
- **Why it matters:** D3's done-when is *"the next instance is diagnosable at the point of failure"*. A
  message that says both "referenced by marshal.json" and "NOT authored in marshal.json" is not
  diagnosable — the reader must decide which half to believe, which is the same hunt-for-a-key-that-does-
  not-exist failure D3 was written to end. It is also the half of the message that is quoted verbatim into
  `decision.log` and the `compose` error TOON (`manage-execution-manifest.py:2314-2327`).
- **Fix:** In `_manifest_validation.py`, make the four reason literals origin-neutral — replace
  ``step `X` referenced by `marshal.json` …`` with ``step `X` …`` (`:668`, `:683`, `:706`) and
  ``step `X` referenced by `marshal.json` is missing standards file …`` with ``step `X` is missing
  standards file …`` (`:480`), leaving the "the plan likely renamed/removed … without sweeping
  `marshal.json`" remediation hints in place (they are advice, not an origin claim). The wrapper in
  `check_emitted_steps_resolvable` is then the single place origin is stated, which is what D3 intended.
  Extend `TestUnresolvableStepProvenance`
  (`test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py:1006`) with an assertion
  that a routed / composer-injected message contains no `referenced by \`marshal.json\`` substring.
- **Done when:** For every input on which `check_emitted_steps_resolvable` returns a message containing
  `NOT authored in marshal.json` or `composer-injected`, that message contains no occurrence of
  ``referenced by `marshal.json` ``; a test in `TestUnresolvableStepProvenance` pins it.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — compose resolution gate.

## Refuted during adversarial review

Nothing recorded here is an open item. It is kept so the next reader knows it was considered.

- **G3, two of its five originally-cited sites — refuted.**
  `manage-execution-manifest/SKILL.md:688` and the router comment at
  `manage-execution-manifest.py:1290-1300` both attribute the pair explicitly to what the **deriver**
  emits — SKILL.md:688 reads "`derive-verification` legitimately emits `compile` and `test-compile`" and
  the router comment reads "A build-phase canonical the deriver legitimately emits (``compile`` /
  ``test-compile``)". Both statements are true: `_resolve_verbs_for_build_class`
  (`manage-architecture/scripts/_cmd_client_handlers.py:396`) emits exactly
  `compile` / `test-compile` / `module-tests` / `verify`, and of those only `compile` and `test-compile`
  are unresolvable. Neither site presents the pair as the carve-out's complete set, so neither is drift.
  The router **docstring** (`manage-execution-manifest.py:1211-1214`) carries the same explicit
  deriver-scoping and is likewise accurate. G3's original line references were also wrong at two sites:
  `phase-4-plan/SKILL.md:797` is blank (the text is at `:798`) and the router comment starts at `:1290`,
  not `:1289`. Both corrected above.
- **verification.md § D4, the over-broad-fix claim — refuted and rewritten.** The document asserted that
  "mutating the carve-out to accept everything would break `test_module_tests_still_routes` and
  `test_custom_verb_still_routes_and_fails_loud`". Applied as a mutation
  (`if verb in ALL_CANONICAL_COMMANDS and not _check_step_resolvable(…)` → `if True or …`), the suite
  reports **4 failed, 40 passed**, and `test_module_tests_still_routes` is **not** among the failures:
  `module-tests` resolves through the `_VERB_TO_PHASE_5_STEP` fast path
  (`_manifest_rules.py:920-925`), so `step_id is not None` and the carve-out branch is never reached for
  it. The genuine over-broad guard in the D4 pair is `test_custom_verb_still_routes_and_fails_loud`
  alone. Corrected in verification.md.
