# Gaps — 160-empty-skill-resolution-indistinguishable-from-minimal

The shipped change is real and its tests are non-vacuous in both directions, but the new signal is
narrower than the plan and the report describe. The deterministic guard cannot fire for the shape the
enrichment writers actually produce for "nothing resolved" (they omit the profile rather than writing
an empty block), it is discarded on a fail-open branch whose own comment promises the opposite, and
its message never enters the command's structured output. The escape hatch has a second edge, and it
is the most consequential item here: **two supported CLI verbs in sequence — declare a profile
`minimal: true`, then run `enrich add-domain` / `enrich all` — persist a populated block that still
carries `minimal: true`, both steps returning `status: success` with no warning, and phase-4-plan then
reads it as "no skills" and discards every resolved skill silently.** That was reproduced by
execution, not inferred from reading; the run report's rejection of it as "nonsensical input" is
factually wrong about how the state arises. It is the same masking archetype this plan exists to
close, newly introduced by this plan. Fifteen gaps follow, one per instance.

## G1 — Stop discarding the unresolved-profile condition when the bundles root cannot be resolved

- **Kind:** bug
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:543-549` (`_emit_skills_by_profile_staleness_warning`), with the false claim at `:428-431`
- **Evidence:** the module comment states *"when the bundle root cannot be located … the stale-notation check is skipped, but the missing/empty and unresolved-profile checks still fire because they need no registry."* Measured with `marketplace_bundles.resolve_bundles_root` patched to raise and `plan_logging.log_entry` captured, four rows:

  | Input `merged` | root resolves? | emitted |
  |---|---|---|
  | populated `implementation` + empty undeclared `module_testing` | yes | unresolved-profile **and** stale-notation messages |
  | same | **raises** | **`[]`** |
  | `{'skills_by_profile': {}}` | raises | `"skills_by_profile is missing or empty"` |
  | `{}` (key absent) | raises | `"skills_by_profile is missing or empty"` |

  The pure core `detect_stale_skills_by_profile` on the row-2 map returned the unresolved-profile message, so the empty emission is the emitter's early return (`:549`), not the harness. **Only the unresolved-profile signal is lost**: the missing/empty signal is reachable only through a falsy map, which takes the `else` branch at `:553` and never enters the guarded `try`. The comment is therefore false about one of the two signals it names, not both.
- **Why it matters:** in any deployment layout `resolve_bundles_root` does not recognise, the one signal this plan added goes silent — a consuming project with an unresolved profile gets exactly the silence this plan set out to end, and the code comment tells the next maintainer the opposite.
- **Action:** restructure the emitter so `detect_stale_skills_by_profile` is always called: resolve the registry predicate defensively (fall back to `lambda _: True`, which disables only the stale-notation signal) instead of returning early. Correct the module comment at `:428-431` in the same change if the behaviour is instead deliberately narrowed.
- **Done when:** with `resolve_bundles_root` raising **and a non-empty `skills_by_profile` carrying an undeclared-empty profile**, the emitter logs the unresolved-profile condition and logs no stale-notation condition; a test asserts both halves. (The missing/empty condition already survives this branch — asserting it alone would not discriminate.)
- **Effort:** S
- **Risk if fixed:** modules in an unrecognised layout begin emitting per-profile WARNINGs that were previously suppressed — the intended behaviour, but new log volume.

## G2 — Clear `minimal` when enrichment populates a profile (or reject the contradictory pair)

- **Kind:** bug
- **Severity:** high
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py:332-348` (`enrich_add_domain`), consumed at `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:314-316`
- **Evidence — reproduced end-to-end, not inferred.** Against the repository's own `setup_test_project` fixture, two supported CLI verbs in sequence:
  1. `enrich_skills_by_profile('module-a', {'module_testing': {'defaults': [], 'optionals': [], 'minimal': True}})` → `status: success`, **no warnings**. This is the state `architecture-persistence.md:455-459` documents as "Declared minimal" and `test_cmd_enrich.py:469` pins as correct.
  2. `enrich_add_domain('module-a', 'general-dev')` → persisted block becomes
     `{'defaults': [4 entries incl. plan-marshall:persona-module-tester], 'minimal': True, 'optionals': []}`.
  3. `detect_stale_skills_by_profile('module-a', <that map>, all_live)` → **`[]`**.

  Mechanism: `existing = current.get(profile_name, {})` (`:332`), `merged = dict(existing)` (`:337`), `merged['defaults'].append(entry)` (`:344`) — the copy carries `minimal: true` across while skills are appended. `enrich_add_domain` never calls `_validate_skills_by_profile_structure` (it runs only in `enrich_skills_by_profile`, `:469`). phase-4-plan then reads `IF skills_by_profile.{P} is present AND declared minimal … Set task.skills = []` **before** any emptiness test.
- **Why it matters:** a profile legitimately declared minimal, later populated by `enrich add-domain` / `enrich all`, produces tasks with `skills: []` although the inventory resolved real skills — and the read-path guard is silent because it sees a populated block. Skills vanish with no signal at all: strictly worse than the defect this plan fixed, and **this plan is what introduced the state**, since `minimal` did not exist before it. The run report dismissed it as "nonsensical input"; no step in the reproduction above involves hand-written data, and no step warns.
- **Action:** in `enrich_add_domain`, drop the `minimal` key whenever at least one entry is appended to a profile; and have `_validate_skills_by_profile_structure` flag `minimal: true` on a profile that carries any `defaults`/`optionals` as malformed.
- **Done when:** enriching a `{"defaults": [], "optionals": [], "minimal": true}` profile with a domain that supplies skills yields a block with the skills and **no** `minimal` key; a test asserts both the persisted shape and the validator warning for the hand-written contradictory pair.
- **Effort:** S
- **Risk if fixed:** a project that deliberately kept `minimal: true` on a populated profile (no known use) loses it on the next enrichment.

## G3 — Make the guard able to fire for an ABSENT profile, not only a present-but-empty one

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:502-511` (`detect_stale_skills_by_profile`), against the writers at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/extension_base.py:1190` and `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_enrich.py:329`
- **Evidence:** both writers skip a profile that resolves nothing — `if merged_defaults or merged_optionals:` and `if not new_entries: continue` — so enrichment never persists an empty block. The guard walks only `skills_by_profile`'s present keys, so a module missing `module_testing` entirely (the originating observation's shape) yields no message. `manage-architecture/SKILL.md:306` nevertheless asserts every module should have both `implementation` and `module_testing`.
- **Why it matters:** the deterministic half of the fix covers a state the machinery does not produce; the real-world "the inventory answered nothing" case still depends entirely on LLM-executed prose in phase-4-plan.
- **Action:** give the guard an expected-profile set (from `marshal.json` active profiles or the `architecture profiles` key set) and emit the same named condition for an expected profile that is absent, with wording that distinguishes absent from present-but-empty.
- **Done when:** a module whose `skills_by_profile` contains only `implementation`, in a project whose active profiles include `module_testing`, surfaces the named condition for `module_testing`; a declared-minimal or populated `module_testing` surfaces nothing.
- **Effort:** M
- **Risk if fixed:** noisy on projects whose active-profile configuration is broader than their real inventory; needs the expected set to come from configuration, not from a hard-coded list.

## G4 — Test the fail-closed `is True` identity check

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-architecture/test_skills_by_profile_staleness_guard.py:122-152`, covering `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:462-470`
- **Evidence:** mutation M1 — `return profile_data.get('minimal') is True` → `return bool(profile_data.get('minimal'))` — left the guard file at **9 passed**, and, re-measured across the guard file plus `test_cmd_enrich.py` together, **48 passed**: no test anywhere in the manage-architecture suite catches the weakening. No test feeds the guard a non-boolean `minimal`, although `enrich_skills_by_profile` persists `"minimal": "true"` (it warns at `_cmd_enrich.py:198-202` but still writes the block at `:473-478`), so the value is reachable on disk and the guard's `is True` is the only thing that stops it laundering the signal.
- **Why it matters:** the fail-closed identity check is the one thing preventing a malformed declaration from laundering the signal — the plan's stated design constraint — and it is currently free to regress silently.
- **Action:** add guard tests asserting that an empty profile carrying `"minimal": "true"`, `1`, or `False` still surfaces the named condition, and that only the boolean `True` silences it.
- **Done when:** mutating `is True` to a truthy test makes the guard test file go red.
- **Effort:** S
- **Risk if fixed:** none.

## G5 — Test `_emit_skills_by_profile_staleness_warning` itself

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:535-564`; no test file references the symbol
- **Evidence:** `grep -rn "_emit_skills_by_profile_staleness_warning" test/` → no hits, while the same pattern over `marketplace/` finds the definition (`:535`) and its call site (`:584`), so the negative is trustworthy. Every test targets the pure `detect_stale_skills_by_profile`.
- **Why it matters:** the emitter holds all the branching that decides whether the condition ever reaches anyone — the registry fail-open (G1), the `[STALENESS]` prefix, and the swallow-all logging guard. None of it is exercised, which is how G1 shipped with a comment contradicting the code.
- **Action:** add tests that inject a raising `resolve_bundles_root` and a captured `log_entry`, asserting which messages are emitted in each branch and that no exception escapes.
- **Done when:** the emitter's three branches (registry available, registry unresolvable, empty map) each have an assertion on the emitted message list.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Update the guard test file's docstring to the three-signal model

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-architecture/test_skills_by_profile_staleness_guard.py:4-11`
- **Evidence:** *"it flags a module whose `skills_by_profile` references skill notations absent from the live registry (retired / renamed IDs) or is missing entirely"* — the two-signal model. The run report recorded three instances of exactly this defect (findings 1–3) and fixed them in the production file; this fourth instance, in the file whose own new tests cover the third signal, was missed.
- **Why it matters:** the next reader of the test file is told the guard has two signals while reading tests for a third.
- **Action:** rewrite the module docstring to name the unresolved-profile signal alongside stale and missing.
- **Done when:** the docstring names all three signals.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Teach the enrichment workflow that a profile may declare itself minimal

- **Kind:** omission
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/SKILL.md:306` (Step 9 completeness check)
- **Evidence:** *"Every module has `skills_by_profile` with at least `implementation` and `module_testing`"*, followed by *"If any module is incomplete → return to Steps 5-8 for that module."* No step anywhere in the skill mentions `minimal`; the marker is documented only in `standards/architecture-persistence.md:437-474`.
- **Why it matters:** the escape hatch is undiscoverable from the workflow that populates the inventory, so the operator facing an genuinely-empty profile has no instruction to declare it — which is precisely the "worked around with a placeholder" failure the plan's design caveat predicts.
- **Action:** amend the Step 9 checklist to accept a declared-minimal profile as complete, and add the `enrich skills-by-profile` invocation that sets `"minimal": true` as the remedy for a profile with no applicable skills.
- **Done when:** `manage-architecture/SKILL.md` names the marker, shows the command that sets it, and its completeness check no longer treats a declared-minimal profile as incomplete.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Correct the "always receive a non-empty skill list" claim in the steward reference

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/references/skill-domains-setup.md:84`
- **Evidence:** *"Populate `skills_by_profile` for every module × every applicable extension so that downstream `phase-4-plan` tasks always receive a non-empty skill list."* `enrich_add_domain` skips profiles with no resolved skills (`_cmd_enrich.py:329`), and `applies_to_module` omits them upstream (`extension_base.py:1190`), so enrich-all guarantees no such thing.
- **Why it matters:** a false guarantee in shipped documentation is exactly the "cheaper explanation wins" trap this plan describes — a reader who believes it will not look for an unresolved profile. (Severity medium, not low: the calibration puts *a false claim in shipped documentation* at medium, and this sentence is read by the steward workflow that populates every project's inventory, not confined to a run record.)
- **Action:** reword to state that enrich-all populates every profile an extension resolves skills for, and that a profile with none is either left absent (unresolved) or declared `"minimal": true`.
- **Done when:** the sentence no longer promises a non-empty skill list.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Surface the named condition in the command's structured output, not only in a log file

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:558-564` and `get_module_info`'s return at `:586-599`
- **Evidence:** the condition is written via `log_entry('script', None, 'WARNING', …)`, which appends to a log file under the plans store (`manage-logging/scripts/plan_logging.py:285-314` — `def log_entry` at `:285`, the file append at `:308-309`); the dict `get_module_info` returns is `merge_module_data`'s output with only reasoning/packages/dependencies keys stripped (`_cmd_client_query.py:586-599`) and carries no warnings field, so the TOON payload a consumer reads is unchanged. The report describes this as the condition being *"surfaced … on the `architecture module` read"*.
- **Why it matters:** the allocation-time consumer (phase-4-plan) reads the command's output, never the script log, so the deterministic signal reaches no decision-maker; the only surface that does is the LLM-executed prose branch.
- **Action:** attach the guard's messages to the returned payload (e.g. a `warnings[]` field on `architecture module`, consistent with the enrich commands' `warnings[]`), keeping the log write.
- **Done when:** `architecture module` output for a module with an undeclared-empty profile contains the named condition as a field, and a test asserts it; a declared-minimal profile's output does not.
- **Effort:** M
- **Risk if fixed:** output-shape change for every `architecture module` consumer; needs the field to be presence-gated so quiet reads are byte-identical.

## G10 — Correct the run report's D1 absence claim

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/160-empty-skill-resolution-indistinguishable-from-minimal/report-01.md:32-43`
- **Evidence:** the report says a per-profile empty *"produces **zero** signal"* and reproduces *"an empty `skills[]` degrading to the persona floor"*. The pre-fix `phase-4-plan/SKILL.md` Step 5 (`git show f29e5ce~1`) already contained *"Log WARNING: … Module {D.module} has empty skills_by_profile.{P}"* and a Q-Gate triage finding titled *"Missing skills_by_profile: {D.module}.{P}"*. The plan required the asserted absence to be verified at the allocation site before building a replacement.
- **Why it matters:** the audit trail records a stronger absence than existed; a later reader re-deriving the epic's archetype from this report would mis-locate the gap (which was distinguishability, not reporting).
- **Action:** amend the D1 section to state that an allocation-time report of the absence already existed in phase-4-plan Step 5, and that the confirmed defect was the inability to distinguish deliberate from unresolved.
- **Done when:** the report's D1 section names the pre-existing WARNING and Q-Gate finding.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Remove the duplicate `_pending_` stub sections at the end of the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/160-empty-skill-resolution-indistinguishable-from-minimal/report-01.md:251-265`
- **Evidence:** after the filled `## Cost`, `## Contract check (Step 9)`, `## What have we learned (Step 9)` and `## Residue` sections (lines 189-249), the same four headings repeat, each with the body `_pending_`.
- **Why it matters:** a template remnant in a shipped record; a reader scanning to the end of the report finds four sections claiming the run's cost, contract check and residue are unfinished.
- **Action:** delete the duplicated stub block.
- **Done when:** each of the four headings appears exactly once in `report-01.md`.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Correct the run report's rejection rationale for finding #6

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/160-empty-skill-resolution-indistinguishable-from-minimal/report-01.md:154` (and the § Residue restatement at `:243-248`)
- **Evidence:** *"Rejected (out of scope) — nonsensical input; neither the plan nor the closed-vocabulary posture asks to reconcile a `minimal` flag on a populated profile."* The state is produced by `enrich_add_domain` (`_cmd_enrich.py:337,344`) whenever a declared-minimal profile is later enriched — ordinary input, not nonsensical.
- **Why it matters:** the rejection rationale is the reason the defect in G2 was left unowned; leaving it uncorrected means the next reader inherits the same false premise.
- **Action:** amend finding #6's disposition to record that the ordinary enrichment path produces the state, and cross-reference the fix item.
- **Done when:** the report no longer characterises the contradictory block as unreachable input.
- **Effort:** S
- **Risk if fixed:** none.

## G13 — Do not skip a non-dict profile block silently

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:504-505`
- **Evidence:** `if not isinstance(profile_data, dict): continue  # structural defects are the enrich validator's surface`. The legacy list shape is still supported downstream (`_cmd_client_render.py:138` `if isinstance(profile_data, list): return len(profile_data)`), so `"module_testing": []` is a representable empty profile that produces no condition — and `_validate_skills_by_profile_structure`, the surface the comment defers to, never runs on the `enrich add-domain` / `enrich all` write paths.
- **Why it matters:** a second shape of "the inventory answered nothing" passes the guard silently, and the justification comment points at a validator that the writing path does not invoke.
- **Action:** treat an empty list-shaped profile block as an empty profile (subject to the same `minimal` rule, which a list cannot carry, hence always unresolved), and emit a malformed-shape message for other non-dict values instead of skipping.
- **Done when:** `{"module_testing": []}` surfaces the named condition, with a test.
- **Effort:** S
- **Risk if fixed:** projects still carrying legacy list-shaped profiles begin emitting messages; verify the population before landing.

## G14 — Reflect the three-state distinction on the render surface

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_render.py` — `_count_profile_skills` (`:127-140`) and its **two** call sites: `_render_skills_by_profile_section` (`:143-160`, emitting at `:157-158`) and `render_module_markdown` (emitting at `:314-315`)
- **Evidence:** both call sites print `- {profile}: {count} skill{s}` from the same `_count_profile_skills`, which sums `defaults` + `optionals` and never reads `minimal`; `grep -rn "minimal" _cmd_client_render.py` → no hits. A declared-minimal profile and an undeclared-empty one both render `0 skills`. Recorded as deliberately deferred residue by the run report and still open. (Topic is `architecture-core`, not `documentation-surface`: the fix is a Python change in the manage-architecture render scripts, so it groups with the other guard/renderer work, not with the standards documents.)
- **Why it matters:** the human-facing surface reproduces exactly the indistinguishability the plan removed from the machine-facing one, so an operator reading `architecture module --full` cannot tell the two apart.
- **Action:** annotate a zero-count profile in the rendered output as `0 skills (declared minimal)` or `0 skills (unresolved)`.
- **Done when:** both the overview section and the module deep-dive distinguish the two zero-count states in their rendered lines, with a test asserting each.
- **Effort:** S
- **Risk if fixed:** rendered-output assertions in existing render tests may need updating.

## G15 — Document the `minimal` field and the read-path condition in the client API standard

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:350-360`, `:405-425`, `:467`
- **Evidence:** the `architecture module` examples show only `defaults`/`optionals`; neither the `minimal` marker nor the `[STALENESS]` unresolved-profile condition appears anywhere in the file (`grep -n minimal client-api.md` → no hits). The three-state model lives only in `architecture-persistence.md:437-474`, the persistence standard.
- **Why it matters:** `client-api.md` is the read-surface contract a consumer of `architecture module` reads; a field that changes how output must be interpreted is absent from it.
- **Action:** add the `minimal` marker to the `skills_by_profile` example and one sentence naming the read-path condition, cross-referencing `architecture-persistence.md` rather than restating the table.
- **Done when:** `client-api.md` mentions `minimal` and the unresolved-profile condition.
- **Effort:** S
- **Risk if fixed:** none.
