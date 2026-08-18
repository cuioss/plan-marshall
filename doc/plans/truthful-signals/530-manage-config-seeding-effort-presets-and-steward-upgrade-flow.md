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

# manage-config seeding, effort presets and the steward upgrade flow report success over lost data

**Epic:** truthful-signals
**Branch prefix:** `fix` — the three highest-severity items are shipped bugs (a config-destroying
write, a fail-open reconcile, and a guard no test constrains); the remainder are corrections to
statements the tree makes about itself.

## Problem

Thirty-four defects were filed against twelve landed plans in this epic, and they concentrate on three
mechanisms that all produce the same shape of lie. **First, `.plan/marshal.json` write paths lose data
and say they did not.** `ClaudeRuntime.project_initial_setup`
(`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`) builds
`marshal_data = {"runtime": …, "project_dir": …}` and hands it to `claude_runtime._write_json` with no
read of the existing file and no existence check — every other top-level block in an initialized
project is destroyed, and the verb returns `marshal_written: True`. Its OpenCode sibling, implementing
the same contract operation, reads and merges. `manage-providers`' `_save_marshal` performs an
unguarded whole-document read-modify-write with a plain `write_text`. And the top-level keys those
seeds write — `runtime` from both targets, `project_dir` from the Claude seed alone — are absent from
`CANONICAL_TOP_LEVEL_KEY_ORDER`, so `normalize-keys` reports the product's own first-party
configuration as unrecognized.

**Second, the build-server reconcile infers idleness it was never told.** `run_status`
(`manage-build-server/scripts/manage_build_server.py`) coerces a missing `in_flight` to `0`, so a
daemon pinned to a copy predating the counts extension is indistinguishable from an idle one; the
project-local reconcile then drains a live build. `run_upgrade` discards both fields that could report
a failed upgrade (`run_drain`'s `exited`, `_start_daemon`'s `already_running`) and hard-codes
`status: success`, and the reconcile clears its owed marker on that word alone.

**Third, guards and descriptions do not constrain what they claim to.**
`test_bare_resolve_without_workflow_emits_nothing` asserts against a plan-scoped log that the
invocation under test never writes to, so replacing `if workflow:` with `if True:` in `_cmd_effort.py`
leaves the module's whole test suite green. `EffortPresets.describe('balanced')` — the text an operator
reads verbatim in the wizard's `AskUserQuestion` — names every slot above its stated default and none
of the three below it, so the sentence reconstructs to a different ladder than `apply-preset balanced`
writes. `manage-config`'s SKILL.md promises a `--audit-plan-id` alias the executor strips before the
parser ever sees it, and a lane value (`auto`) argparse rejects.

## Goal

Every write path that touches `.plan/marshal.json` — the population and its routed/bypass split
re-derived by D1(a), never counted from this plan or from the gap documents — either preserves what it
did not author or is recorded, in the docstring that claims to be the ordering authority, as one that
does not; a
reconcile that cannot read the daemon's own counts defers instead of draining; the guards and
descriptions this epic's earlier plans shipped constrain and describe what actually runs; and the
operator-facing steward surfaces relay the fields the tools underneath them now emit. Where a fix
requires a decision this run cannot make, the plan records a proposal and ships nothing on it.

## Deliverables

Ordered so a run that stops early has shipped the `high` items. D1 is a cheap derivation that gates
the scope of D5 and D8 only; D2–D4 carry every `high` gap and rest on named files and symbols rather
than on any derived population, so they proceed regardless of D1's outcome.

1. **D1 — Derive the three populations this plan's scope rests on (gating)** — no gaps closed; gates
   D5 and D8. Run three derivations and write each one, with the exact command that produced it, into
   the run report:
   (a) every `*.py` under `marketplace/bundles/` that both names a marshal path and performs a write —
   the `.plan/marshal.json` writer set, split into *routed through `_config_core.order_config_keys`*
   and *bypass*;
   (b) a filename-reference sweep over `marketplace/bundles/**/*.{md,py}` for every
   `*/skills/*/standards/*.md` document that no file references by filename;
   (c) `grep -rnoE "/Users/[a-z0-9_.-]+" test/` and the matching `/home/…` sweep — the placeholder-root
   population under `test/`.
   ⛔ **STOP CONDITION.** If (a) cannot be derived, do **not** write any count into the
   `order_config_keys` docstring in D5: record D5's docstring half BLOCKED in the run report and ship
   D5's code half only. If (b) or (c) cannot be derived, record the dependent half of D8 BLOCKED. In
   no case write a hand-maintained substitute list — a hand-maintained enumeration is the defect class
   D5 and D8 exist to close, and reproducing it inside the fix is worse than shipping nothing.
   *Done when:* the run report carries three derived lists, each with its producing command, or an
   explicit BLOCKED entry naming which derivation failed and why.

2. **D2 — `ClaudeRuntime.project_initial_setup` stops destroying an existing config**
   *(closes 080/G9 — high)* — in
   `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py`,
   `project_initial_setup` reads any existing `marshal.json` first and merges, mirroring
   `opencode_runtime.py`'s implementation of the same contract operation: load the existing document
   when the file is present, set `runtime.target` and `project_dir` on it, write the merged result. On
   the failure edges, mirror what `opencode_runtime.project_initial_setup` actually does rather than
   the source gap's paraphrase of it: a *missing* file starts from `{}`, while an unreadable or
   unparseable one is caught (`except (OSError, json.JSONDecodeError)`) and returned as an `io_error` —
   the OpenCode path does **not** fall back to `{}` on a corrupt file, and neither may this one,
   because that fallback would destroy exactly the config this fix exists to preserve.
   *Done when:* a test in `test/plan-marshall/platform-runtime/test_claude_runtime.py` seeds
   `.plan/marshal.json` with a `plan` block, calls `ClaudeRuntime.project_initial_setup`, and asserts
   both that `runtime.target == 'claude'` and that the pre-existing `plan` block survives — **and the
   test has been seen RED against the unmodified unconditional write before the fix is applied**, with
   the failure text quoted in the run report.

3. **D3 — The reconcile fails closed on unknown counts, and `upgrade` can report a failed upgrade**
   *(closes 070/G1 — high, 070/G7, 070/G2)* — three changes in dependency order.
   (a) In `manage_build_server.run_status`, emit `in_flight` / `queued` only when the ping response
   actually carries them; when either key is absent emit an `unknown` sentinel rather than `0`. In
   `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py`'s `decide`, add a branch **before**
   the busy check returning `ReconcileDecision(ACTION_DEFER, 'counts_unknown')` when either count is
   missing or not an integer — the same fail-closed shape `provenance_unknown` already uses.
   (b) In `run_upgrade`, add `drain_exited` (from `run_drain`'s `exited`) and `already_running` (from
   `_start_daemon`) to the returned dict, and set `status: error` with a `reason` when `drain_exited`
   is false or `already_running` is true. Name both keys in the `run_upgrade` docstring and in the
   `upgrade` row of `manage-build-server/SKILL.md`'s verb table.
   (c) In `reconcile_daemon.reconcile`, gate the success path on those two fields instead of on
   `result['status']`: for `upgrade`, `drain_exited is False` **or** `already_running is True` is a
   failed reconcile; for `start`, `already_running is True` is. On failure set
   `summary['reconcile_result'] = 'failed'` and **write** (never clear) the owed marker with
   `reason='reconcile_failed'`, carrying the same `running_binary_path` / `resolved_binary_path` fields
   the defer branch records, and extend `_display_detail` with a `reconcile_failed` line. Clear the
   marker only on a verified success.
   *Done when:* `test/sync-plugin-cache/test_reconcile_daemon.py` contains a case feeding a
   `running ∧ binary_diverges` status with both counts absent and asserting
   `decide(...).action == ACTION_DEFER` with reason `counts_unknown`; a second case drives `reconcile`
   with an `action_runner` returning `{'status': 'success', 'drain_exited': False,
   'already_running': True}` and asserts `reconcile_result == 'failed'` with the marker written at
   `reason == 'reconcile_failed'`; `test/plan-marshall/build-server/test_manage_build_server.py`
   contains a case stubbing `_running_pid` to a live pid and `_wait_for_exit` to `False` asserting
   `drain_exited is False`, `already_running is True` and `status != 'success'`. **Each of the three
   has been seen RED with the new guard reverted**, and the run report quotes the failures.

4. **D4 — `manage-config`'s declared surface constrains and matches what runs**
   *(closes 280/G1 — high, 280/G6, 290/G5, 100/G3, 290/G4)*.
   (a) *(280/G1, `vacuous-test`)* In
   `test/plan-marshall/manage-config/test_dispatch_seam_emission.py::test_bare_resolve_without_workflow_emits_nothing`,
   pass `--plan-id bare` alongside `--phase phase-5-execute` (still no `--workflow`) so the assertion
   reads the log the emission would actually route to, and add a second assertion over the global log
   for the no-`--plan-id` case (read `plan_logging.get_log_path(None, 'work')` and `(None, 'decision')`
   before and after, assert the line counts are unchanged).
   (b) *(280/G6)* In `_cmd_effort._emit_dispatch_records`, compute the display value from the same
   predicate the routing already uses — `plan_display = plan_id if names_real_plan(plan_id) else
   'none'` — so the `NO_PLAN` sentinel emits `plan_id=none`, and pin it with a test.
   (c) *(290/G5)* Make the `--audit-plan-id` sites agree with the executor contract, which strips the
   flag unconditionally before the target parser runs: delete the declarations in `manage-config.py`
   (`build-decision` and `sync-defaults`), delete the `or getattr(args, 'audit_plan_id', None)`
   fallback in `_cmd_build_map.py`, change that file's error string to `build-decision requires
   --plan-id`, and delete the alias sentence from `manage-config/SKILL.md`. Do **not** take the
   alternative direction (re-appending the flag in the executor) — it contradicts the stated contract
   in `plan-marshall:script-shared`'s `argparse_surface.py`
   (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/argparse_surface.py`, the
   `audit-plan-id` member of the universal accept-set comment), and amending that contract is not this
   run's to decide.
   (d) *(100/G3)* Replace `auto` with `standard` at the three surviving lane restatements —
   `manage-config/SKILL.md`'s `finalize-steps` row of the noun/verb summary table,
   `manage-config/standards/data-model.md`'s per-element lane-override paragraph, and the
   `_LANE_ASK_INFRA_STEPS` comment in `_config_defaults.py`. The live authority is
   `_RESOLVED_ASK_LANE_VALUES = ('off', 'standard', 'full')`; `auto` is rejected at runtime. Leave
   every unrelated `auto` (the `gate_mode` enum, the `lane_selection` enum) alone.
   (e) *(290/G4)* Append a clearly-marked correction note to
   `doc/plans/truthful-signals/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/report-01.md`
   § D0 recording that `--audit-plan-id` is declared on `build-decision` and `sync-defaults`, never on
   `build-map`. **Append, do not rewrite the original sentence** — a run report is a dated record of
   one execution, and `380-test-suite-false-confidence/gaps.md` G5 states in terms that a report must
   not be retro-edited; the note is the correction of record.
   *Done when:* replacing `if workflow:` with `if True:` in `_cmd_effort.py` makes
   `test_bare_resolve_without_workflow_emits_nothing` **fail** (the red has been observed and quoted
   in the run report) and the unmutated file passes; a `resolve-target --workflow … --plan-id NO_PLAN`
   emits `plan_id=none`, pinned by a test; `build-decision --audit-plan-id X` through
   `.plan/execute-script.py` and its `--plan-id X` control no longer disagree, and no remaining
   `audit-plan-id` mention in `manage-config.py`, `_cmd_build_map.py` or `manage-config/SKILL.md`
   promises an affordance the executor strips; no hit under
   `marketplace/bundles/plan-marshall/skills/manage-config/` presents `auto` as a `lane` value, and
   `validate_lane_override` still rejects it.

5. **D5 — marshal.json write paths and the schema they write into**
   *(closes 080/G4, 080/G6, 080/G2, 080/G1, 080/G8)*.
   (a) *(080/G4)* Add `runtime` **and** `project_dir` to `CANONICAL_TOP_LEVEL_KEY_ORDER` in
   `_config_core.py` at their intended slots, and document both in
   `manage-config/standards/data-model.md`, so `normalize-keys` stops reporting the product's own
   first-party keys as unrecognized. Adding is the non-destructive half and is grounded:
   `platform_runtime._resolve_target` reads `runtime.target` back. **Record as a proposal, do not act
   on it:** D1(a) is expected to show that no code reads the *top-level* `project_dir` key, so the
   tighter alternative is to stop persisting it in the Claude runtime seed — the only seed that writes
   it, since `opencode_runtime.project_initial_setup` sets `runtime.target` alone — and that is a
   schema decision with no operator to approve it, so the run writes the proposal into its report and
   ships the additive change only.
   (b) *(080/G6)* Route `_providers_core._save_marshal` through `_config_core.save_config`, pairing it
   with a `_config_core.load_config` at the read end of `write_provider_config` so the fingerprint is
   recorded. Both sides already resolve the same path via `file_ops.get_marshal_path()`, so no path
   plumbing is needed. If routing proves infeasible, replicate the fingerprint + `os.replace` there
   instead — and either way name the site in the `order_config_keys` / `save_config` docstrings.
   (c) *(080/G2)* Correct the `order_config_keys` docstring's bypass enumeration to name **both**
   runtime seeds — `_claude_runtime_impl.project_initial_setup` alongside the OpenCode one — and the
   two extension-defaults writers, and to state the routed/bypass split from **D1(a)'s derivation**,
   not from any number quoted in this plan or in the gap documents. Gated by D1's stop condition.
   (d) *(080/G1)* In `manage-config.py:main()`, wrap the dispatch in
   `except ConcurrentConfigModificationError as e: result = error_exit(str(e),
   error_type='concurrent_modification')`, leaving `@safe_main` for genuine crashes, so a recoverable
   lost-update condition stops being reported as an `internal_error` crash at exit 1.
   (e) *(080/G8)* Import `safe_main` from `file_ops` in `marshall-steward/scripts/upgrade.py` and
   decorate `main()` with it, matching `bootstrap_plugin.py`; add `except
   ConcurrentConfigModificationError` handling in `cmd_migrate_bot_lists` returning
   `error_type: concurrent_modification` at exit 0.
   *Done when:* `normalize_keys()` returns `status: success` with `unrecognized_keys: []` for a
   `marshal.json` produced by `manage-config init` followed by `project initial-setup --target
   opencode` — that sequence and not its reverse, because `init` refuses when marshal.json exists and
   `--force` rebuilds from defaults, so the reverse assertion passes vacuously; a test races a
   concurrent write against `write_provider_config` and shows the other writer's change survives (or
   the path delegates to `save_config` and the existing guard test covers it); a test drives a
   `manage-config` verb **other than** `normalize-keys` through a load→concurrent-write→save race and
   asserts `status: error` with `error_type: concurrent_modification` at exit code **0**; and a test
   that forces an exception out of `cmd_migrate_bot_lists` asserts `upgrade.py` prints parseable TOON
   `status: error` on stdout and never leaves stdout empty.

6. **D6 — Steward operator-facing surfaces relay what the tools underneath them emit**
   *(closes 070/G5, 070/G3, 080/G3, 080/G7, 150/G3, 360/G5, 080/G5)*.
   (a) *(070/G5)* In `marshall-steward/SKILL.md` § "Build Server Status (read-only pointer)", add
   `binary_diverges` (and the `note` when present) to the named field list, with one sentence saying a
   `true` value means the running daemon is executing an older pinned copy and a reconcile is owed.
   (b) *(070/G3)* Change the `status` sub-parser help string in `manage_build_server.py` from
   `'Report running version + binary path.'` to text naming the version, the in-flight/queued counts,
   and the running-vs-resolved provenance, matching that skill's SKILL.md verb table.
   (c) *(080/G3)* In `marshall-steward/references/upgrade-flow.md`, replace the "its position is
   load-bearing" rationale with what is true: `sync-defaults` and `steps-sort` are conditional writes,
   so on a config whose only drift is key order neither writes and `normalize-keys` — the unconditional
   canonicalizer — is what is required; every write canonicalizes through `save_config`, so
   `normalize-keys`' *position* among the three does not change the resulting key order and it is
   sequenced last only for readability. Add a one-line note at the Re-Run Remediation Pass step (a) in
   `marshall-steward/SKILL.md` saying its position is likewise immaterial, so the two documents stop
   giving opposite accounts. Leave the Stage-2 order test asserting the order — it still pins presence.
   (d) *(080/G7)* Extend `upgrade-flow.md`'s freshness parse instruction to name `compared_against`
   alongside `freshness`, `refuses_upgrade` and `remediation`, and state that a `fresh` verdict must be
   reported with its comparison scope attached; list `compared_against` among the emitted fields in the
   `cache_freshness — check` entry of `marshall-steward/SKILL.md` § Canonical invocations.
   (e) *(150/G3)* Add a "Display Timezone" option to the steward Configuration submenu — an option row
   on one of the `AskUserQuestion` pages in `references/menu-configuration.md`, a matching row in that
   file's Routing table, and a new `references/menu-display-timezone.md` wrapping
   `run_config display-timezone get` / `set --value {zone}`, modelled on the existing
   `menu-derivation-resolvers.md`. ⚠ Do **not** seed `display_timezone` into `DEFAULT_STRUCTURE`; the
   source gap's refutation section rules that out. Append a correction note to
   `doc/plans/truthful-signals/150-configurable-display-timezone-for-rendered-timestamps/report-01.md`
   § Residue recording that the deferral pointed at plan `090`, whose scope is a different
   configuration file, and that the surfacing landed here instead.
   (f) *(360/G5)* In `marshall-steward/scripts/cache_retention.py`'s module docstring, state keep-rule 3
   as a superset of what the newest-*eligible* resolver selects rather than as identical to it, and
   name the foreign Claude Code plugin GC as `.orphaned_at`'s sole producer, dropping the live/marked
   partition wording. Do not touch `data-model.md` — the source gap records it as already correct.
   (g) *(080/G5)* Append the reload/restart step to `cache_freshness.REMEDIATION`, to its docstring
   example, and to the two `upgrade-flow.md` restatements, updating
   `test/plan-marshall/marshall-steward/test_cache_freshness.py` accordingly. That half is grounded
   in-tree at three sites (`doc/user/installation.adoc`, `platform-runtime/standards/contract.md`,
   `extension-api/standards/ext-point-dynamic-level-executor.md`) which all state a reload is required
   for a refreshed cache to be visible. **Record as a proposal, do not act on it:** whether
   `/plugin update <name>` exists in the Claude Code plugin CLI at all cannot be settled from the
   clone, and the rest of the repository prescribes `/plugin marketplace update` plus a reinstall
   instead. Write the two candidate sequences, the four sites that would change, and the test
   assertion that currently blocks the reinstall form into the run report as a proposal for the
   operator. Do not change the command itself.
   *Done when:* `marshall-steward/SKILL.md` names `binary_diverges`; no file under `marketplace/`
   contains the string `Report running version + binary path`; `upgrade-flow.md` no longer asserts that
   `normalize-keys`' position changes the resulting key order and its parse instruction names
   `compared_against`; `menu-configuration.md` carries both an option row and a Routing row for
   `display-timezone` and `menu-display-timezone.md` exists naming the `get`/`set` invocations;
   `cache_retention.py`'s docstring names the foreign GC as the marker's sole producer and contains no
   live/marked partition wording, with `test_cache_retention.py` still passing; `REMEDIATION` ends with
   a reload/restart step and its test passes; and the run report carries the `/plugin update` proposal
   with both candidate sequences. **Cold read required** — see Verification.

7. **D7 — Every effort-preset description reconstructs the payload it describes**
   *(closes 200/G6, 200/G7, 200/G1, 200/G2, 200/G3, 200/G4, 200/G5)*.
   (a) *(200/G6)* Extend `_DESCRIPTIONS['balanced']` in
   `plan-marshall/scripts/effort_presets.py` with the below-default remainder, matching the clause style
   `describe('high-end')` already uses: after the level-5 clause, name the triage
   (`verification-feedback`) slots and `phase-6-finalize.default` as staying at `level-3`.
   (b) *(200/G7)* In the `BALANCED` module-docstring bullet and the `BALANCED` attribute docstring,
   replace "keeping the triage (verification-feedback) slots at `level-3`" with wording that also names
   `phase-6-finalize.default`.
   (c) *(200/G1)* Rewrite the comment above `RESERVED_LEVELS` so it states two separate facts: the
   tuple is empty, so the import-time validator rejects nothing beyond `ALLOWED_LEVELS`; and, as a
   *policy* rather than a validator constraint, no preset uses `level-6`/`level-7` because both resolve
   to alias-capability-gated efforts that fall back silently, so those tiers are explicit per-phase
   opt-in only. Fix the companion advice in `_validate_level_keyword`, whose error message points the
   caller at `level-7`. ⛔ **Scope this to `effort_presets.py` alone.**
   `manage-config/scripts/_cmd_effort.py` carries a deliberately-parallel `RESERVED_LEVELS` block and an
   identical `level-7` string, and **neither is a second instance**: that comment stops before the "so
   presets may reference it" clause, and that module validates a user-supplied per-scope level, where
   `level-7` opt-in is the sanctioned path. Changing them would introduce the error this fix removes.
   (d) *(200/G2)* Append `identify` to the `effort` row of `manage-config/SKILL.md` § API Reference's
   noun/verb table, matching the row's style and the verb set in `standards/api-reference.md`.
   (e) *(200/G3)* Add an `effort identify` line to the `Handles:` block of `_cmd_effort.py`'s module
   docstring, in the existing column-aligned style.
   (f) *(200/G4)* Add `identify` to the `effort_presets.py` row of the `## Cross-References` table in
   `marshall-steward/standards/effort-menu.md`.
   (g) *(200/G5)* Drop the "mirroring effort-menu Step 1" clause from the identical sentences in
   `marshall-steward/references/wizard-flow.md` and `references/menu-configuration.md`, or replace it
   with a note that the effort menu uses the deterministic `manage-config effort identify` recogniser
   and that `finalize-steps` has no equivalent verb. Keep the two files identical to each other, as
   they are today.
   *Done when:* reconstructing each preset's nine slots from its `_DESCRIPTIONS` string alone — the
   stated default applied to every slot not explicitly named — reproduces `EffortPresets.get(name)`
   exactly for all three names, and summing the levels the `BALANCED` docstrings describe gives the 36
   they state; no statement in `effort_presets.py` implies a preset may carry `level-6`/`level-7` and
   `_cmd_effort.py`'s `RESERVED_LEVELS` block is unchanged; the `effort` row in
   `manage-config/SKILL.md` and the `Handles:` block in `_cmd_effort.py` each name every verb
   `manage-config.py` dispatches to a `cmd_effort_*` handler; the `effort_presets.py` cross-reference
   row in `effort-menu.md` names `identify`; and no occurrence of "mirroring effort-menu Step 1"
   survives under `marketplace/` that describes an LLM deep-equality walk. **Cold read required** —
   see Verification.

8. **D8 — Documentation and marker corrections**
   *(closes 340/G4, 100/G5, 190/G4, 050/G4, 070/G4, 380/G5)*.
   (a) *(340/G4)* In `manage-execution-manifest/scripts/_manifest_validation.py`, make the four
   unresolvable-step reason literals origin-neutral by removing `referenced by \`marshal.json\`` from
   each, leaving the "the plan likely renamed/removed … without sweeping `marshal.json`" remediation
   hints in place — they are advice, not an origin claim. The wrapper in
   `check_emitted_steps_resolvable` is then the single place origin is stated. Extend
   `TestUnresolvableStepProvenance` in
   `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` with an assertion that
   a routed / composer-injected message contains no `referenced by \`marshal.json\`` substring.
   (b) *(100/G5)* For each unreferenced `*/skills/*/standards/*.md` document **D1(b)'s sweep returns**,
   decide wire-in or delete and act: if the content is current and unique, add an explicit link from the
   owning skill's SKILL.md; if it duplicates a canonical standard, delete it and point at the canonical
   one. The source gap names three at the time it was written
   (`manage-config/standards/domain-residency-audit.md`,
   `manage-config/standards/provisioning-fail-closed-audit.md`,
   `phase-3-outline/standards/integration-tests.md`) — treat that as a **lead, not the population**, and
   act on D1(b)'s result. Note that `integration-tests` as a canonical build-target *name* appears
   widely in prose; that is unrelated to the file.
   (c) *(190/G4)* Add `plan.phase-1-init.auto_route_recipe` and
   `plan.phase-1-init.auto_route_recipe_threshold` to `manage-config/standards/data-model.md`'s
   `plan.phase-1-init` section table and to its "Complete Structure" JSON sample, with the defaults and
   validators sourced from the block comments in `_config_defaults.py` — re-read them at the moment of
   the edit rather than trusting any default quoted here.
   (d) *(050/G4)* Delete the four-line `# SHIM(B):` marker block above `_deep_merge_missing`'s merge
   loop in `manage-config/scripts/_cmd_sync_defaults.py` — the function contains no branch on the legacy
   `{}` shape, so there is nothing for a future sweep to remove; the docstring's "Ownerless-step
   interaction" paragraph already records the history. Re-run the shim-marker detector over
   `marketplace/bundles` and confirm it is still clean.
   (e) *(070/G4)* Extend the `_ping` Returns block in `manage_build_server.py` to name `in_flight` and
   `queued` alongside `status`/`pid`/`version`, and state explicitly that a daemon older than the counts
   extension omits them — the assumption D3(a) exists to stop a reader making.
   (f) *(380/G5)* Normalise every remaining `/Users/…` placeholder root under `test/` onto `/home/dev`,
   over the population **D1(c) derives** — the source gap's own file list is a lead and is known to be
   short by at least one file — then re-run the owning test directories to confirm no assertion depends
   on the strings. Do **not** retro-edit `380-test-suite-false-confidence/report-01.md`. ⛔ Scope this
   to the `/Users/` population only. The source gap's *Done when* additionally demands that `/home/dev`
   be the only `/home/` root under `test/`; that condition is **false at HEAD and is not adopted here**
   — `test/` independently carries `/home/u` HOME-whitelist literals in more than one module,
   `/home/runner` inside captured CI-log fixtures, and other unrelated roots, none of which is a
   placeholder this gap is about. Re-derive that set with D1(c)'s `/home/…` sweep, record it, and leave
   it untouched.
   *Done when:* for every input on which `check_emitted_steps_resolvable` returns a message containing
   `NOT authored in marshal.json` or `composer-injected`, that message contains no occurrence of
   `referenced by \`marshal.json\``, pinned by a test in `TestUnresolvableStepProvenance`; a re-run of
   D1(b)'s sweep returns zero unreferenced `*/skills/*/standards/*.md` files and the derivation is
   recorded; every key `get_default_config()` emits under `plan.phase-1-init` appears in
   `data-model.md`'s table; `_cmd_sync_defaults.py` carries no `# SHIM(B):` block above
   `_deep_merge_missing` and the detector run is clean; the `_ping` docstring names all five keys and
   the omission case; and a re-run of D1(c)'s sweep returns no `/Users/` root under `test/` and only
   `/home/dev` among `/home/` roots, apart from the unrelated `/home/u` HOME-whitelist literal in
   `test/plan-marshall/build-server/test_marshalld_supervisor.py`.

## Out of scope

- **`doc/user/efforts.adoc`'s `balanced` preset row (gap `200/G8`).** It is the same defect family as
  D7(a)/(b) and a run working D7 will be tempted to sweep it in, but it was not assigned to this plan
  and is carried by a sibling plan in this epic; two plans editing one row is a merge conflict for no
  gain. If D7 lands and that row still contradicts the payload, say so in the run report.
- **The two `manage-execution-manifest` lane restatements (gap `100/G8`).** D4(d) covers only the three
  sites inside `manage-config`; the source gap document filed the `manage-execution-manifest` pair
  separately and scoped `100/G3` explicitly to the `manage-config` skill, so widening here would take
  work another plan owns.
- **Amending `argparse_surface.py`'s stripping contract to let `--audit-plan-id` survive to the parser.**
  D4(c) takes the contract-preserving direction. The alternative is a change to a governing contract,
  and a cloud run has no operator to approve one — the source gap says as much ("should not be chosen
  without amending that comment").
- **Changing the `/plugin update plan-marshall` command itself.** D6(g) ships only the reload step, which
  three in-tree sites independently require. Whether that command exists at all is a fact about the
  Claude Code plugin CLI that no file in the clone settles, so acting on it would be shipping the same
  unverified guidance the gap objects to, in the other direction.
- **Removing top-level `project_dir` from the two runtime seeds.** D5(a) adds it to the canonical order
  instead. Removal is a schema decision whose only evidence is an absence (no reader found), and an
  unverified absence acted on in a run with no operator is exactly the class of mistake this epic
  documents.
- **`manage-config/scripts/_cmd_effort.py`'s `RESERVED_LEVELS` block and its `level-7` advice string.**
  Explicitly excluded by D7(c) with the reason there: both statements are correct in their own context,
  and "harmonising" them would introduce the defect `200/G1` removes.
- **Redesigning `CANONICAL_TOP_LEVEL_KEY_ORDER` beyond adding the two runtime-seed keys.** The source
  plan for `080` declared that redesign out of scope, and reopening it here would put a schema debate
  in front of five unrelated fixes.
- **Every other gap in the twelve source `gaps.md` files.** This plan closes the thirty-four listed
  under § Claim labels and nothing else; the remainder are assigned to sibling plans, and an unassigned
  gap fixed here is a gap fixed twice.
- **Plugin cache sync.** `CLAUDE.md` § Standalone Plan Lane states the lane neither performs a sync nor
  records one as owed, because the sync reads a git-ignored `target/` tree and writes outside the
  repository. Merged bundle source is authoritative.

## Expected surface

The run should touch these and, per the lane contract, report anything else it had to change.

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py` — D2's
  read-merge-write.
- `test/plan-marshall/platform-runtime/test_claude_runtime.py` — D2's red-first test.
- `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py` —
  D3(a)/(b), D6(b), D8(e).
- `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md` — D3(b)'s verb-table row.
- `test/plan-marshall/build-server/test_manage_build_server.py` — D3's upgrade-failure case.
- `.claude/skills/sync-plugin-cache/scripts/reconcile_daemon.py` and
  `test/sync-plugin-cache/test_reconcile_daemon.py` — D3(a)/(c). Project-local but git-tracked, so
  present in the clone.
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` — D4(b), D7(e).
- `test/plan-marshall/manage-config/test_dispatch_seam_emission.py` — D4(a)/(b).
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` — D4(c), D5(d).
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_build_map.py` — D4(c).
- `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` — D4(c)/(d), D7(d).
- `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — D4(d), D5(a), D8(c).
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — D4(d).
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` — D5(a)/(c).
- `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/_providers_core.py` — D5(b).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — D5(e).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` — D6(a)/(c)/(d).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` — D6(c)/(d)/(g).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md` — D6(e),
  D7(g).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-display-timezone.md` — new,
  D6(e).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md` — D7(g).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/effort-menu.md` — D7(f).
- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_freshness.py` and
  `cache_retention.py`, with `test/plan-marshall/marshall-steward/test_cache_freshness.py` — D6(f)/(g).
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` — D7(a)/(b)/(c).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py`
  and `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` — D8(a).
- The unreferenced `standards/*.md` documents D1(b) returns, and the SKILL.md files that would link
  them — D8(b).
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` — D8(d).
- Test fixtures and test modules under `test/` carrying a `/Users/…` placeholder root, as D1(c) derives
  them — D8(f).
- `doc/plans/truthful-signals/290-main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully/report-01.md`
  and `doc/plans/truthful-signals/150-configurable-display-timezone-for-rendered-timestamps/report-01.md`
  — append-only correction notes, D4(e) and D6(e).

## Claim labels

Every scoping premise below was checked against the tree at the commit this plan was authored from.
Every artifact named is git-tracked and reachable from a fresh clone; none is under `.plan/`.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| **080/G9 (high) reproduces**: `project_initial_setup` builds `marshal_data` and calls `claude_runtime._write_json` with no read and no existence check | OBSERVED | `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py` — `ClaudeRuntime.project_initial_setup` |
| **070/G1 (high) reproduces**: `run_status` coerces an absent count with `int(response.get('in_flight', 0) or 0)` | OBSERVED | `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/manage_build_server.py` — `run_status` |
| **280/G1 (high) reproduces**: the test asserts against plan `bare`'s log after an invocation carrying no `--plan-id`, and the gate it names is `if workflow:` | OBSERVED | `test/plan-marshall/manage-config/test_dispatch_seam_emission.py` — `test_bare_resolve_without_workflow_emits_nothing`; `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` — `cmd_effort_resolve_target` |
| Every other gap in the set (070/G2–G5, 070/G7, 080/G1–G8, 100/G3, 100/G5, 150/G3, 190/G4, 200/G1–G7, 280/G6, 290/G4, 290/G5, 340/G4, 360/G5, 380/G5, 050/G4) reproduces at the authoring commit — none was dropped as already closed | OBSERVED | the file and symbol each gap names, in `doc/plans/truthful-signals/{050,070,080,100,150,190,200,280,290,340,360,380}-*/gaps.md` |
| `070/G6` and the refuted clauses inside `080/G1`, `290/G2`, `290/G3`, `340/G3`, `100/G2`, `100/G7` are **not** carried here | OBSERVED | the `## Refuted during adversarial review` section of each source `gaps.md`; none of those ids appears in this plan's gap set |
| `runtime.target` has a live first-party reader, so adding `runtime` to the canonical key order is not a schema invention | OBSERVED | `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — `_resolve_target` |
| The **top-level** `project_dir` marshal key has no reader anywhere under `marketplace/` | HYPOTHESIS | D1(a)'s derivation settles it. Until it does, D5(a) adds the key rather than removing it, and the removal ships only as a proposal. An asserted absence is the higher-risk half of a claim — do not act on this one on the strength of this row |
| `/plugin update <name>` exists in the Claude Code plugin CLI and refreshes an installed cache | HYPOTHESIS | Nothing in the clone settles it: the string appears only at the four `marshall-steward` sites the gap names, while `doc/user/installation.adoc` and `README.md` prescribe `/plugin marketplace update` plus a reinstall. D6(g) therefore ships a proposal, not a change |
| The **expected surface** above is the set this plan touches | HYPOTHESIS | The run's own diff. Three entries are populations rather than named files — D1(b)'s unreferenced standards documents, D1(c)'s placeholder-root files, and the SKILL.md files D8(b) would link — so the surface is exact only after D1 |
| Counts quoted anywhere in this plan or in the gap documents (writer sites, orphan documents, placeholder files, preset spreads) | HYPOTHESIS | Every one is a **lead**. Re-derive it at the moment of the change through D1, or by reading the payload, and report the re-derived value — the clone the run sees is not guaranteed to match the tree this plan was authored from |

## Verification

Beyond each deliverable's *Done when*:

**Red-first evidence is mandatory for D2, D3 and D4(a).** `280/G1` is filed as `vacuous-test`, and the
whole point of it is that a test can be present, well-formed and constrain nothing. For each of those,
the run applies the named mutation *before* the fix (D2: the unconditional write; D3: each new guard
reverted; D4(a): `if workflow:` → `if True:`), observes the failure, and **quotes the failure text in
the run report**. A test that was never seen red against the defect it names does not close a
vacuous-guard gap, however green it is afterwards.

**Cold reads, dispatched independently, for D6 and D7.** These deliverables are text whose entire value
is what a later reader does with it, so "implemented as specified" cannot verify them. Give a reader who
has not seen this plan only the changed text and ask what it makes them do, then record which reading
came back:

- The rewritten `upgrade-flow.md` Stage 2 rationale (D6c) — does the reader conclude that
  `normalize-keys`' position among the three verbs **does** or **does not** change the resulting key
  order? The correct reading is *does not*.
- The `marshall-steward/SKILL.md` Build Server Status section (D6a) — shown a `status` payload with
  `running: true`, a plausible `version`, and `binary_diverges: true`, does the reader report the daemon
  as healthy or as owing a reconcile? The correct reading is *owes a reconcile*.
- `EffortPresets.describe('balanced')` (D7a) — asked to write down the level of every one of the nine
  slots from the sentence alone, does the reader reproduce `EffortPresets.get('balanced')` exactly?
  This is the wizard's `AskUserQuestion` option text, read verbatim by an operator choosing a cost tier,
  so a reader who lands on `level-4` for `phase-6-finalize.default` means the wording failed.
- The rewritten `RESERVED_LEVELS` comment (D7c) — does the reader conclude a preset may carry `level-7`?
  The correct reading is *no*, and the reader should be able to say why the validator nonetheless
  permits it.

If any cold read returns the wrong reading, the wording failed however complete the diff looks — fix it
and re-read, and record both readings.

**Executed checks, not read ones.** Run the full build gate (the lane's conditional `./pw verify`, which
this plan's Python changes arm) and, in addition: the shim-marker detector over `marketplace/bundles`
for D8(d); the re-run of D1(b)'s and D1(c)'s sweeps as the *Done when* of D8(b)/(f); and the
`build-decision --audit-plan-id X` / `--plan-id X` pair through `.plan/execute-script.py` for D4(c). The
executor is a generated, git-ignored artifact — if it is absent from the clone, record D4(c)'s
executed check as unavailable and verify by reading the stripping code in
`tools-script-executor/templates/execute-script.py.template` instead. Do **not** treat its absence as
evidence the flag works.

**Read-only checks.** That D4(d) left every unrelated `auto` alone (the `gate_mode` and `lane_selection`
enums); that D7(c) left `_cmd_effort.py`'s parallel block untouched; that the two correction notes in
D4(e) and D6(e) are appended rather than replacing the original sentences.

## Notes

- **Do not go looking for `.plan/`.** It is git-ignored and absent from this clone — no orchestrator
  ledger, no plan spec, no landing record, and possibly no generated `execute-script.py`. Everything
  this run needs is in this file and in the git-tracked gap documents it cites.
- **The gap documents are the evidence, and they are in the clone.** Each deliverable names the gap ids
  it closes; the full entries — Kind, Severity, Where, What is wrong, Why it matters, Fix, Done when —
  live at `doc/plans/truthful-signals/{NNN}-*/gaps.md`, and the surrounding evidence at the sibling
  `verification.md`. Open the entry before writing the fix. Where a gap body and its `## Adversarial
  review` / `## Refuted during adversarial review` section disagree, **the review section wins**: it
  records which claims were upheld, refuted, re-severitied or corrected, and several gap bodies carry a
  ⚠ correction inline for exactly that reason.
- **Eight deliverables against the template's "roughly six is a signal to split" heuristic.** The split
  was considered and rejected: the plan number is assigned, the thirty-four gaps concentrate on three
  mechanisms rather than eight, and the deliverables are ordered so a run that stops early has still
  shipped every `high` item. D1 carries no gaps at all — it is a derivation whose only product is
  three lists in the run report.
- **Two gaps depend on a third and are sequenced accordingly.** `070/G2` cannot be closed inside
  `reconcile_daemon.py` alone, because `run_upgrade` today returns no field that distinguishes a
  completed upgrade from a failed one; `070/G7` must land first. D3 states the order (a) → (b) → (c)
  for that reason.
- **Two deliverables record a proposal instead of making a call**, because a cloud run has no operator
  to approve one: the `project_dir` schema question (D5a) and the `/plugin update` remediation
  sequence (D6g). Both proposals belong in the run report with their candidate options, the sites that
  would change, and the evidence that is missing. Shipping either decision silently would be the
  failure this epic documents, at the moment it is most tempting.
- **Two run reports get append-only correction notes** (D4e, D6e). A run report is a dated record of one
  execution, not documentation of current state — `380-test-suite-false-confidence/gaps.md` G5 states
  that explicitly and forbids retro-editing one. The notes are additions; the original sentences stay.
- **Every `high` gap is closed by a deliverable**: `080/G9` by D2, `070/G1` by D3, `280/G1` by D4(a).
  If the run must stop, stopping after D4 leaves all three landed.
