# Gaps — 340-derive-verification-emits-a-build-class-phase-5-cannot-route

**Source:** verification.md (same directory)   **Open items:** 3

All three are statement-accuracy items. The three code deliverables (router carve-out, provenance split,
matched-pair tests) are implemented, correct, registry-derived, and non-vacuous under mutation — no
behavioural gap was found.

## G1 — Correct the compose call-site comment that still claims the unresolvable_step error names the marshal.json key

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:2295-2302` — the comment block immediately above the `check_emitted_steps_resolvable(...)` call in `cmd_compose`
- **What is wrong:** The comment states the gate "fails the compose loud, naming the offending ORIGINAL
  marshal.json key and the phase (mapped back from the boundary-normalized emitted id via
  marshal_phase_{5,6}_map)". D3 replaced that universal behaviour with a three-way provenance split
  (`_manifest_validation.py:783-822`): only a step present in the marshal step map is named by the
  author's key; a phase-5 step absent from the map is attributed to `architecture derive-verification`
  routing, and phase-6 gets a neutral composer-injected note. Executing the function confirms all three
  wordings. `report-01.md` § Findings round 2 claims "no OTHER consumer of the retired universal contract
  remains" and § Residue claims "all documentation stale-claims are resolved" — this site contradicts both.
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
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py:823-834` — the `marshal_map is None` return in `check_emitted_steps_resolvable`
- **What is wrong:** When `marshal_map` is `None` — `_read_marshal_phase_step_map` returns `None` when
  marshal.json is missing, unparseable, or carries no such key — the message still reads
  ``phase_5 step `X` in marshal.json is unresolvable``. Executed at HEAD:
  `check_emitted_steps_resolvable(['verify:compile'], [], None, None)` returns exactly that string, byte
  for byte identical to the genuinely-authored case. The step is asserted to be in a file the composer
  just failed to read.
- **Why it matters:** D3's whole purpose was to stop the error misattributing a routed step to
  marshal.json. On this branch the misattribution survives, and it is the branch that fires precisely when
  marshal.json is absent — so the reader is sent to a file that may not exist at all.
- **Fix:** In the `marshal_map is None` branch, drop the "in marshal.json" clause and state the actual
  situation: ``phase_5 step `X` is unresolvable: {reason}. No marshal.json step map was available for this
  phase, so the step's origin (authored vs routed) could not be determined.`` Add a test beside
  `test_marshal_authored_step_error_names_marshal_json` in
  `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` asserting the
  `marshal_map=None` message does **not** contain `in marshal.json`.
- **Done when:** `check_emitted_steps_resolvable(['verify:compile'], [], None, None)['message']` no longer
  claims marshal.json origin, and a test pins that.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — compose resolution gate.

## G3 — Say that the carve-out covers seven canonicals, not the two it names

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:688`; `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:523`; `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:797`; the router comment at `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:1289-1300`; the `_VERB_TO_PHASE_5_STEP` comment at `_manifest_rules.py:901-903`
- **What is wrong:** Every one of these renders the carve-out set as "(`compile` / `test-compile`)". The
  predicate is `verb in ALL_CANONICAL_COMMANDS and not _check_step_resolvable(f'verify:{verb}',
  'phase_5')`. Evaluating `_check_step_resolvable` over every entry of `ALL_CANONICAL_COMMANDS` at HEAD
  gives **seven** unresolvable canonicals — `clean`, `compile`, `test-compile`, `benchmark`, `install`,
  `clean-install`, `package` — against seven resolvable ones (`module-tests`, `integration-tests`, `e2e`,
  `coverage`, `quality-gate`, `arch-gate`, `verify`). All seven are kept with the task, not two.
- **Why it matters:** The general predicate *is* stated alongside the parenthetical, so behaviour is not
  in doubt — but a reader sizing the change, or writing a test that expects an orchestrator-tier `package`
  to route to `verify:package` and fail loud, will get it wrong. The set is also not static: it moves
  whenever a canonical gains or loses a phase-5 verify gate.
- **Fix:** In the five sites above, mark the pair as illustrative rather than exhaustive — e.g. "a known
  canonical build command with no phase-5 verify gate (today: `clean`, `compile`, `test-compile`,
  `benchmark`, `install`, `clean-install`, `package` — the deriver emits `compile` and `test-compile`)" —
  and state that the set is derived, so it follows the registry and the gate set without a doc edit. Do
  not hard-code the seven-item list as the contract; the derived predicate stays the authority.
- **Done when:** No prose or comment presents `{compile, test-compile}` as the complete carve-out set; each
  site names the derived predicate as the authority and the two deriver-emitted verbs as examples.
- **Module/topic:** `plan-marshall:manage-execution-manifest` (+ `phase-4-plan` SKILL.md) — execution_tier
  routing documentation.
