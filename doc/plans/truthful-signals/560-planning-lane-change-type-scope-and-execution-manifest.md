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

# The planning lane, the change-type scopes and the execution manifest each stop reporting a confidence their inputs do not support

**Epic:** truthful-signals
**Branch prefix:** fix — the plan's two highest-severity items are behavioural defects (a compose
refusal with no accepting input; a de-escalation bought by a zero-evidence band), and every remaining
item corrects a shipped statement that contradicts the code beside it.

## Problem

Three surfaces landed recently, and each one shipped a confident signal that its own inputs do not
support.

**The planning-lane router** (`marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py`,
`evaluate_signals_pure`) de-escalates an explicit author scale warning (`S7:risk_prose`) whenever the
scope band reads `single_module`. But `classify_scope_pure` assigns `single_module` through
`band_rule='pathless_non_empty_body'` to any non-empty request body in which **zero** file paths were
found — so the sensor's "I found nothing to bound this with" is consumed as "I measured a middle-sized
change". The same branch defines its residue by exclusion (`not in _DEEP_SCOPE_ESTIMATES and not in
_NARROW_SCOPE_ESTIMATES`), so every unrecognised, empty or whitespace-padded band also de-escalates,
while the comment directly above it asserts the residue "is exactly `{single_module}`" and "adapts
automatically if the band set changes". Further down in the same function, the `low_confidence` flag is
`signals_null > signals_resolved` over a seven-member vector in which two members are booleans that are
never `None` — so it needs 4 of the 5 nullable fields null and can no longer fire for the
orchestrator-launched population it was built for.

**The change-type reconciliation** in `cmd_compose`
(`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`)
validates the *supplied* value against `VALID_CHANGE_TYPES` but never validates the *settled* value
read back by `_read_settled_change_type`. A plan whose `status.metadata.change_type` holds any value
outside the six canonical ones — `feature_breaking` is documented as live at exactly that key — has
**no accepting input**: every canonical supplied value returns `change_type_scope_conflict` and the
non-canonical one returns `invalid_change_type`, so the plan can never compose and can never leave
phase 4. The refusal, which is the single highest-value audit event this feature creates, `return`s
before the `_emit_decision_log` call and therefore writes **nothing** to the plan's decision log —
while `decision-rules.md` asserts the decision "can be audited afterward" with no carve-out.

**The execution manifest's own statements about itself** have drifted from the code beside them: the
compose resolution gate's call-site comment still claims the `unresolvable_step` error names the
marshal.json key unconditionally (the D3 provenance split replaced that); the CSV-fallback branch of
`check_emitted_steps_resolvable` still says a step is "in marshal.json" on the one path that fires
precisely because no marshal.json could be read; a new `terminal_emission_dropped` field is absent
from both documents that enumerate the compose result; two `decision-rules.md` lines offer `auto` as a
per-element `lane` value that `validate_lane_override` rejects; a SKILL.md asserts the skill "MUST NOT
be registered in `plugin.json`" while its own bundle registers it; a contract subsection forbids
treating a declared surface as ground truth while `_apply_code_step_inactive` does exactly that; and a
category-B migration shim carries no marker because the sweep that was supposed to find it reported
zero hits for its whole bundle.

Two consumer documents complete the set: **`phase-5-execute`** parses `conflict_count` from
`baseline-reconcile` with no branch on `status` first, so a probe that explicitly declined to classify
(returning `merge_base_unresolved`, `head_unresolved` or `probe_mutated_head` at exit code 0, with no
`conflict_count` at all) is read as zero-overlap and the run **writes new baseline metadata and
continues the task loop**; and a `phase-2-refine` test still names
`git checkout -- .plan/marshal.json` as "the recovery path the post-refine orchestrator runs", the
destructive contract a prior plan replaced with an inspect-and-dispose one.

## Goal

Every signal named above either reports what its inputs support or refuses in a way a reader can act
on: the corroboration de-escalates only against a *measured* middle band drawn from an enumerated
residue, `low_confidence` fires for the population it was built for, a non-canonical settled
classification stops being an unescapable compose block and starts being a logged, recoverable
condition, the refusal leaves a durable audit line, and every document, comment and docstring listed
under Expected surface describes the code it sits beside.

## Deliverables

Ordered so the two `high` gaps land in D2 and D3. D1 precedes them because it is a mechanical
minutes-long derivation whose failure would invalidate D5, D6 and D7 as well; it changes no file.

1. **D1 — Derive the two populations this plan's scope rests on, or HALT** *(closes no gap directly;
   gates D6's 340/G3 clause and D7's 310/G7 clause)*
   Two populations are named in gap fixes as though they were known. Derive both from the clone before
   editing anything that depends on them, and **write neither as a hand-maintained list**:
   - **(a) The unresolvable-canonical set.** Evaluate `_check_step_resolvable(f'verify:{verb}',
     'phase_5')` over every entry of `ALL_CANONICAL_COMMANDS`
     (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/_extension_constants.py`;
     `_check_step_resolvable` lives in
     `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py`)
     at HEAD and record
     which canonicals have no phase-5 verify gate. **Do not trust any count in this plan** — the gap
     that motivated it recorded seven of fourteen at its own authoring time, and the set moves whenever
     a canonical gains or loses a gate. Re-derive it at the moment of the edit.
   - **(b) The `baseline-reconcile` consumer set.** Sweep `marketplace/` for documents that instruct a
     reader to parse `conflict_count` from a `baseline-reconcile` return, and record which of them
     branch on `status` first. **The candidate set is what the sweep returns, not what this plan
     lists** — the gap that motivated this names only the two `phase-5-execute` documents, and a sweep
     at authoring time found several further `.md` files carrying both tokens (under `phase-6-finalize/`,
     `phase-2-refine/` and `plan-marshall/`), so the population is materially larger than the gap's two
     and its exact membership must be re-derived at the moment of the edit. For **every** file the sweep
     returns, establish whether it is a consumer of this return (it dispatches `baseline-reconcile` and
     reads `conflict_count` from the result) or an unrelated mention (it describes the field, or reads a
     different script's `conflict_count`), and record the verdict per file. Exclude
     `phase-6-finalize/standards/archive-plan.md`, whose `conflict_count` belongs to a different script.
   **HALT condition:** if either population cannot be derived from the tree — the constant is
   unimportable, the resolvability check cannot be executed, the sweep cannot be scoped to a decidable
   set — **stop the run and report it blocked**, naming which derivation failed. Do not substitute a
   list written by hand: a hand-maintained enumeration is the defect class D6 and D7 exist to close, so
   a fallback would reproduce it inside the fix.
   *Done when:* the run report carries both derived populations with the command or snippet that
   produced each, and every later deliverable that names a set cites this derivation rather than a
   number copied from this plan.

2. **D2 — A settled classification outside the canonical vocabulary is not a conflict** *(closes
   350/G1 — `high`)*
   In `cmd_compose`
   (`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`,
   the block that reads `settled_change_type = _read_settled_change_type(plan_id)` and returns
   `change_type_scope_conflict`), treat a settled value that is **not** a member of
   `VALID_CHANGE_TYPES` (`_manifest_core.py`) as *not a usable classification* rather than as a
   conflicting one. Prefer the fail-toward-composing shape the malformed-`status.json` path already
   follows: have the read return `None` for a non-member value and emit a decision-log line naming the
   unusable value, so compose falls through to the existing `change_type_scope: supplied` path. Do not
   silently swallow it — the log line is the whole point.
   *Done when:* a test in
   `test/plan-marshall/manage-execution-manifest/test_compose_change_type_reconciliation.py` seeds
   `status.metadata.change_type = 'feature_breaking'`, calls compose with **each** of the six members
   of `VALID_CHANGE_TYPES`, and asserts none of the six returns `change_type_scope_conflict`
   (`status == 'success'` with `change_type_scope == 'supplied'`); and reverting the guard makes that
   test fail.

3. **D3 — The planning-lane router de-escalates only on measured evidence, and reports its own
   confidence** *(closes 240/G2 — `high` —, 240/G5, 240/G1)*
   The three behavioural edits (a)–(c) land in `evaluate_signals_pure`
   (`marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py`) and its
   caller `_evaluate_signals` in the same file; (d) corrects the prose around them, in that file and in
   `manage-status/SKILL.md`; (e) moves the existing tests those edits invalidate. They are one
   deliverable because they rewrite the same two blocks and the same false comment.
   - **(a) Require a measured band (240/G2).** `classify_scope_pure` already returns `band_rule`, and
     `_evaluate_signals` computes it but attaches it to the result only after the decision is made. Add
     an optional `scope_band_rule: str | None = None` parameter to `evaluate_signals_pure`, pass
     `scope_provenance['band_rule']` from `_evaluate_signals`, and require
     `scope_band_rule == 'path_count_middle_band'` — never `pathless_non_empty_body`, and never `None`
     for a caller that cannot supply it — in addition to the existing noncommittal test before S7 is
     suppressed.
   - **(b) Enumerate the residue (240/G5).** Replace the two `not in` exclusions with an explicit
     allowlist frozenset (`_NONCOMMITTAL_SCOPE_ESTIMATES = frozenset({SINGLE_MODULE})`, beside the
     existing `_DEEP_SCOPE_ESTIMATES` / `_NARROW_SCOPE_ESTIMATES`) so an unrecognised, empty or
     whitespace-padded band falls through to "no corroboration" and S7 keeps the lane.
   - **(c) Make `low_confidence` reachable (240/G1).** Change the predicate so it keys on the
     discriminating inputs rather than a bare majority of the seven-member dict: exclude
     `planning_lane_override` from the denominator (its absence is the normal state, not an unresolved
     read) and flag when two or more of `plan_source`, `scope_estimate`, `change_type`, `compatibility`
     are null. Three existing assertions in
     `test/plan-marshall/manage-status/test_planning_lane_corroboration.py` already read
     `confidence['low_confidence']` (`test_d3c_several_nulls_reported_low_confidence`,
     `test_confidence_high_when_most_signals_resolve`, and the control
     `test_d3d_control_deep_warranting_vector_still_routes_deep`) — re-read all three at HEAD and state
     for each whether the new predicate keeps its expected value or the expectation has to move.
   - **(d) Correct the prose that (a), (b) and (c) falsify.** These texts describe the two blocks being
     rewritten, and each states something narrower or wider than the code will:
     the **corroboration comment block** above `scope_resolved_noncommittal` — the only site asserting
     both that the residue "is exactly `{single_module}`" and that it "adapts automatically if the band
     set changes", and that "A genuinely large change is unaffected: it fires a corroborator"; the
     **module docstring**'s corroboration paragraph and its confidence paragraph; `evaluate_signals_pure`'s
     own docstring bullets for `suppressed_signals` and `confidence`; and the **prose-only corroboration**
     and **signal-resolution confidence** paragraphs of
     `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` § planning-lane — the SKILL.md
     asserting "a genuinely large change is unaffected because it fires a corroborating signal", but
     making no "adapts automatically" claim. A pathless, concretely-worded, non-generative,
     non-breaking request that declares its own scale fires no corroborator at all (not S2, S3, S4 or
     S5), so the "genuinely large change is unaffected" reassurance is exactly what fails — state
     the narrowed rule, say the residue is enumerated rather than derived, and restate the
     `low_confidence` predicate to match (c). Re-read each site before editing it: only rewrite the
     sentences that are actually there.
   - **(e) Move the tests that pin the pre-(a) behaviour.**
     `test/plan-marshall/manage-status/test_planning_lane_corroboration.py`'s
     `test_d3a_recorded_vector_does_not_route_deep` calls `evaluate_signals_pure` with **no** band rule
     and asserts `lane == 'light'` with `suppressed_signals == ['S7:risk_prose']` — under (a) that call
     no longer suppresses, so the test must be updated to pass the measured band rule (and its module
     docstring's coverage list with it) rather than left to fail. Re-read the whole file for any other
     assertion (a)–(c) move, and report each one moved.
   *Done when:* an S7-alone request whose `single_module` band came from `pathless_non_empty_body`
   routes `deep` with `suppressed_signals == []`; a `path_count_middle_band` case (4–7 distinct paths,
   no fan-out marker) still routes `light`; a parametrized test over `['module_pair', '',
   ' single_module']` shows each routes `deep` with an empty `suppressed_signals`; and
   `evaluate_signals_pure` reports `low_confidence: True` for the post-bridge motivating vector
   (`plan_source` non-null, `scope_estimate='single_module'`, `change_type=None`, `compatibility=None`,
   `override=None`) — every one of the four pinned by a test; and `test/plan-marshall/manage-status/`
   passes in full, with no test left asserting the pre-(a) suppression.

4. **D4 — The reconciliation refusal is auditable, and its test can tell the two scopes apart**
   *(closes 350/G4, 350/G2)*
   - **(a)** In `cmd_compose`, emit a decision-log line immediately **before** the
     `change_type_scope_conflict` `return`, carrying the same
     `(plan-marshall:manage-execution-manifest:compose) change_type reconciliation — ` prefix as the
     accepting path (so the retrospective's `_DECISION_TAG` filter in
     `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py`
     picks it up) and naming the refusal plus both values. Leave the accepting-path emission unchanged.
   - **(b)** 350/G2 is a **vacuous-test** gap: `test_reconciliation_emits_auditable_decision_log_line`
     asserts `'settled' in recon[0]` and `'bug_fix' in recon[0]`, both of which hold whichever scope
     drove the decision. Assert on the scope-bearing clause instead (`"from the settled scope"`), and
     add a paired case seeding no `status.json` that asserts `"from the supplied scope"`.
   *Done when:* **red-first, both halves, demonstrated in the run report** — (i) with the new
   emission call deleted, the new refusal-path test fails; (ii) with `change_type_scope` pinned to the
   constant `'supplied'` in `cmd_compose`, `test_reconciliation_emits_auditable_decision_log_line`
   fails. A test that has not been *seen* red against the defect it names does not close either gap.
   Restore the mutations and re-run green before committing.

5. **D5 — The unresolvable-step gate stops asserting a provenance it does not have** *(closes 340/G1,
   340/G2)*
   - **(a)** Rewrite the naming clause of the comment block above the
     `check_emitted_steps_resolvable(...)` call in `cmd_compose` so it describes the three-way
     provenance split rather than the retired universal "names the offending ORIGINAL marshal.json
     key" behaviour: an authored step is named by the original marshal.json key (mapped back via
     `marshal_phase_{5,6}_map`); a phase-5 step absent from that map is named as routed from a derived
     `verification.commands` entry by `architecture derive-verification`; a phase-6 step absent from
     the map gets the neutral composer-injected note; the CSV-fallback path reports the emitted id.
     Extend the `_build_step_marshal_key_map` docstring in `_manifest_validation.py` to mention the
     routed branch alongside the CSV-fallback degradation it already documents.
   - **(b)** In the `marshal_map is None` branch of `check_emitted_steps_resolvable`
     (`_manifest_validation.py`), drop the "in marshal.json" clause — that branch fires precisely when
     no marshal.json could be read — and state the real situation instead, naming that the step's
     origin (authored vs routed) could not be determined.
   *Done when:* `check_emitted_steps_resolvable(['verify:compile'], [], None, None)['message']` no
   longer claims marshal.json origin, pinned by a test beside
   `test_marshal_authored_step_error_names_marshal_json` in
   `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py`; and no comment or
   docstring under
   `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/` contains the string
   `offending ORIGINAL marshal.json key`.

6. **D6 — The execution-manifest contract documents describe the code beside them** *(closes 340/G3,
   302/G6, 100/G8, 100/G9, 330/G4, 050/G3)*
   Six items around the `manage-execution-manifest` skill: five statements that assert something the
   code beside them contradicts, plus one shim that carries no marker. Each is a small, independent
   edit; they are one deliverable because they land in that skill's documents and its two immediate
   neighbours (`phase-4-plan/SKILL.md` for (a), the `plugin-script-architecture` shim convention for
   (f)'s classified-out branch), and one reviewer reads them together.
   - **(a) 340/G3 — the build-phase-canonical carve-out.** `decision-rules.md`,
     `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` and the `_VERB_TO_PHASE_5_STEP`
     comment in `_manifest_rules.py` each render the predicate with an inline parenthetical
     (`` `compile` / `test-compile` ``) that reads as the exhaustive carve-out set; the real predicate
     is `verb in ALL_CANONICAL_COMMANDS and not _check_step_resolvable(f'verify:{verb}', 'phase_5')`.
     Mark the pair as illustrative, name the derived predicate as the authority, and cite **D1(a)'s
     derivation** for the current membership. Do **not** hard-code the set as the contract. Two further
     sites — `manage-execution-manifest/SKILL.md`'s "`derive-verification` legitimately emits `compile`
     and `test-compile`" sentence and the router comment/docstring that scope the pair to the deriver —
     were **refuted during the source plan's adversarial review** as accurate; leave them alone.
   - **(b) 302/G6 — `terminal_emission_dropped`.** `cmd_compose` returns this field, and no `.md` file
     in the bundle mentions it. Add it to the compose-result TOON example and the field-shape paragraph
     in `manage-execution-manifest/SKILL.md` beside `unresolved_ask_provider_dropped`, and add a bullet
     to `decision-rules.md` § Outputs: the terminal-emission step dropped for a non-orchestrated plan,
     a bare step-id list, with the reason riding the paired `[STATUS]` line.
   - **(c) 100/G8 — the lane restatements.** `decision-rules.md` offers `off`/`auto`/`full` as resolved
     ask values and `(auto / full / ask / absent)` as the per-element lane values. `auto` is not a lane
     value: the closed set is `VALID_LANE_OVERRIDE` in
     `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`, and the
     resolved-ask subset is `_RESOLVED_ASK_LANE_VALUES` in `_cmd_finalize_steps.py`. Correct both lines
     to `off`/`standard`/`full` and `(standard / full / ask / absent)` respectively, leaving the
     trailing `→ auto` **gate-mode** target unchanged — that one is correct.
   - **(d) 100/G9 — the false registration prohibition.** `manage-execution-manifest/SKILL.md` ends its
     script-only paragraph with "it MUST NOT be registered in `plugin.json`", while
     `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` registers it. The rule that governs
     this (`plugin-doctor`'s `plugin-json-orphan-component`) makes a `user-invocable: false` skill
     **exempt** from the registration requirement, not forbidden from registering. Delete the sentence,
     or replace it with the rule's own wording. Confirm the registration by reading the `plugin.json`
     entry rather than assuming it.
   - **(e) 330/G4 — declaration vs. record, reconciled.** `decision-rules.md` § "Declared surface vs.
     live footprint" states a gate "MUST NOT treat the declaration as ground truth for what changed",
     while `_apply_code_step_inactive` in `_manifest_rules.py` drops `finalize-step-simplify` on
     `affected_files_count == 0` alone, with no live-footprint leg — unlike its sibling
     `_apply_security_class_inactive`, which drops only when the declaration is empty **and** the live
     footprint is resolvable-and-empty. **This run does not choose between the two remedies.** Change
     the *document* so it stops contradicting the shipped code: name the `finalize-step-simplify` gate
     as an explicitly sanctioned exception in that subsection, with its reason (the gate runs
     pre-worktree, where the live footprint is not yet resolvable) and a pointer to the sibling gate
     that does consult it, and reconcile the "`finalize-step-simplify`'s gate is unchanged" line so it
     no longer reads as an endorsement of the contract the subsection forbids. Then **record, in the
     run report only, a proposal** for the behavioural alternative — extending
     `_apply_code_step_inactive` with the same `live_footprint_count` leg — for an operator to decide.
     Changing that gate's behaviour is a contract decision this run has no operator to authorise, so it
     is proposed and not made.
   - **(f) 050/G3 — the unmarked category-B shim.** `_LEGACY_CI_WAIT` in
     `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_decide.py`
     is a permanent read-path accommodation of a persisted config shape an older version wrote, and it
     carries no marker. Read the constant and its two `drop=` call sites, then either add a conforming
     marker block per
     `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`
     (owner `manage-execution-manifest`; the change that retired the `ci-wait` phase-6 step id as the
     floor; "no project marshal.json lists `ci-wait` as a phase-6 candidate" as the removal trigger),
     **or** record it in that convention's not-a-shim list with the reason. Whichever way it lands,
     re-run the shim vocabulary sweep over `manage-execution-manifest` and state the **population size
     and the hit count separately** — a zero hit count over an unstated population is the signal this
     epic exists to remove.
   *Done when:* (a) none of the three carve-out sites presents `{compile, test-compile}` as the
   complete set and each names the derived predicate as the authority; (b) both documents name
   `terminal_emission_dropped` and state its shape; (c) no line under
   `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` presents `auto` as a value of
   the per-element `lane` override; (d) the SKILL.md no longer asserts a registration state its own
   bundle's `plugin.json` contradicts; (e) `decision-rules.md` reads consistently end to end — no gate
   makes a drop decision from a declared-surface count alone without the subsection naming it as a
   sanctioned exception — and the run report carries the behavioural proposal; (f) `_LEGACY_CI_WAIT`
   either carries a conforming marker or is named in the not-a-shim list, and the re-sweep is recorded
   with its population size.

7. **D7 — The `baseline-reconcile` consumers branch on `status` before reading `conflict_count`, and
   the refine documents agree with themselves** *(closes 310/G7, 310/G2, 210/G1)*
   - **(a) 310/G7 — the fail-open consumer.** `phase-5-execute/SKILL.md` and
     `phase-5-execute/standards/sync-with-main.md` both say "Parse `conflict_count`,
     `upstream_commit_count`, and `upstream_commits` from the returned TOON" and then branch on
     `conflict_count == 0` → **self-absorb** (write `status.metadata.worktree_sha` / `main_sha` and
     continue the task loop). Neither branches on `status` first, and the probe's
     `merge_base_unresolved` / `head_unresolved` / `probe_mutated_head` returns carry **no**
     `conflict_count` at all at exit code 0 — so an agent reading an absent field as falsy records a
     new baseline on the strength of a probe that declined to classify. Insert, immediately before the
     parse instruction in both documents: `status: error` → return the structured drift TOON with
     `error: baseline_drift`, do not self-absorb and do not enter the task loop; `status: skipped` →
     the same abort, with `display_detail` carrying the `reason`; only `status: success` proceeds to
     read `conflict_count`. Add an explicit sentence that an absent `conflict_count` is never treated
     as zero, and add the corresponding rows to the § "Drift Semantics" table in `sync-with-main.md`.
     Apply the same branch to **every** further consumer D1(b) identified as one; for any file D1(b)
     classified as an unrelated mention, record that verdict in the run report and leave the file
     alone.
   - **(b) 310/G2 — the skip-condition row.** In
     `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md`, the
     "Skip Conditions Summary" row still reads `| Zero upstream commits since phase-1-init | …`, while
     line 234 of the same document was rewritten by the landing to name
     `merge-base(HEAD, origin/{base})` and to say "never a SHA captured at plan initialisation".
     Change the row to name the merge-base. **Do not gate this on the bare pattern
     `since phase-1-init`** — `phase-5-execute/SKILL.md` contains an unrelated, correct sentence ending
     "…since phase-1-init no longer records it", so that pattern can never reach zero. Gate on
     `upstream commits since phase-1-init`.
   - **(c) 210/G1 — the destructive recovery contract still pinned by a test.**
     `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` states, in its
     module docstring, in `test_marshal_json_restored_after_checkout`'s own docstring, and in an inline
     comment, that the post-refine orchestrator runs `git checkout -- .plan/marshal.json` as "the
     recovery path". The authority
     (`marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § "Named recovery
     case — `.plan/marshal.json`") now mandates `git diff -- .plan/marshal.json` plus an explicit
     operator disposition. Keep `test_manage_config_set_dirties_marshal_json` (the detection half)
     unchanged. Replace the restored-after-checkout test with one whose subject is the **inspection**
     step — assert that `git diff -- .plan/marshal.json` in the test's synthetic repository emits a
     non-empty diff after the mutating `manage-config set` — and rewrite the module docstring's test
     list, the "recovery path" sentence and the inline comment accordingly, cross-referencing that
     authority.
   *Done when:* (a) both `phase-5-execute` documents branch on `status` before reading
   `conflict_count`, the `sync-with-main.md` Drift Semantics table has a row for the non-`success`
   return, and every consumer D1(b) identified carries the same branch; (b) `upstream commits since
   phase-1-init` returns zero hits under `marketplace/` and the row agrees with line 234 of its own
   document; (c) the symbol `test_marshal_json_restored_after_checkout` no longer exists anywhere under
   `test/plan-marshall/phase-2-refine/`, the strings `the recovery path` and
   `post-refine orchestrator runs` no longer appear in that file attached to a `git checkout --`
   instruction, and the file's tests pass.

8. **D8 — Documentation corrections** *(closes 240/G3, 240/G4, 300/G6, 300/G7, 350/G3)*
   Five cosmetic drifts, each a statement that is simply false about the current tree. No behaviour
   changes here; every assertion is checked against the file it describes before it is rewritten.
   - **(a) 240/G3.** `test/plan-marshall/manage-status/test_planning_lane_corroboration.py` contains
     `test_recorded_vector_routes_deep_without_the_corroboration_fix`, whose body asserts
     `result['lane'] == 'light'` and never runs against a pre-fix router. Rename it to state what it
     asserts (e.g. `test_recorded_vector_is_light_when_s7_does_not_fire`) and update the module
     docstring's coverage list if it names the old identifier.
   - **(b) 240/G4.** The `planning-lane` subparser `description=` in
     `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` states the
     unqualified predicate "any deep-precondition signal forces deep", which two documented exceptions
     now falsify. Qualify it with the narrow-and-concrete carve-out (S3/S4) and the prose-only
     corroboration, and point at the `manage-status` skill § planning-lane. The occurrences in
     `_cmd_planning_lane.py`'s module docstring and in `manage-status/SKILL.md` are each qualified in
     place within the same section — leave them. Note the sequencing: D3(d) rewrites the corroboration
     prose, so word this description against **D3's** rule, not the pre-D3 one.
   - **(c) 300/G6.** In
     `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_validate.py`,
     `_ORDER_RESOLVABLE_CANDIDATES` annotates `'architecture-refresh'` as `# order 25` and
     `'finalize-step-preference-emitter'` as `# order 61`; both are wrong. Correct each comment against
     the order the step's own standards document declares — read it, do not copy a number from this
     plan. In `decision-rules.md`, the narrative clause saying the incident "moved the step to its
     pre-merge `order: 61`" describes an intermediate state: rewrite it to say the correction moved the
     step out of the post-archive append position and that the step now sits in the post-run-review
     band at the order its standards document declares.
   - **(d) 300/G7.** The `test_project_step_order_resolves_from_project_local_skill_md` docstring in
     `test/plan-marshall/manage-execution-manifest/test_validate_loadable.py` asserts in the present
     tense that `default:finalize-step-preference-emitter` "now sits pre-merge at order 61 (the settle
     band)". It sits post-merge, in the post-run-review band (`post_run_review: true`), at the order
     its standards document declares. Rewrite those docstring sentences. **Change no assertion** — the
     test asserts only `deploy-target == 81` and `sync-plugin-cache == 85`, both correct.
   - **(e) 350/G3.** Five surfaces spell `change_type` bare at the point where they *author* one of the
     two scopes, so a reader of any one of them cannot tell which scope the field carries:
     `phase-3-outline/SKILL.md`, `manage-solution-outline/standards/solution-outline-standard.md` and
     `manage-solution-outline/templates/deliverable-template.md` (the DELIVERABLE-scoped field), and
     `manage-status/SKILL.md` and `manage-status/standards/status-lifecycle.md` (the PLAN-scoped
     field). Annotate each with its scope and cross-reference
     `manage-execution-manifest/standards/decision-rules.md` § "change_type scope reconciliation"
     rather than restating the explanation. This is residue **beyond** the source plan's D2, which its
     adversarial review found complete — do not re-edit the four sites where both scopes already appear
     and already differ.
   *Done when:* each of (a)–(e) is verified against the file it describes: the renamed test's name and
   assertion agree and its file's tests pass; `manage-status planning-lane --help` names both
   exceptions and no other argparse string in that file states the unqualified predicate; no comment or
   prose in the three 300/G6 locations names an order the step does not currently declare; no sentence
   in `test_validate_loadable.py` names an order for `finalize-step-preference-emitter` other than the
   one its standards doc declares; and each of the five 350/G3 sites names its scope and links to the
   canonical explanation.

## Out of scope

- **Validating `change_type` on the `manage-status metadata --set` write side.** The source gap
  suggests it as an independent follow-up, and it would close the door D2 opens a window in. It is
  excluded because it changes the contract of a generic metadata setter used by callers this plan has
  not enumerated: an enum check there could reject a value some other consumer legitimately writes, and
  establishing that population is a plan of its own. D2's read-side guard makes the plan composable
  without it.
- **Changing `_apply_code_step_inactive`'s behaviour (330/G4's first remedy).** Excluded because it is
  a contract decision — whether `finalize-step-simplify` may drop on a declared-surface count alone —
  and this run has no operator to authorise one. D6(e) documents the current behaviour as a sanctioned
  exception and records the alternative as a proposal instead.
- **The other gaps in the source plans' `gaps.md` files.** Only the twenty-two ids named in the
  deliverables above are in scope. Excluded because each remaining gap is assigned to a different plan
  in this epic, and two plans editing one file is the collision the epic's numbering exists to prevent.
- **Re-editing the four sites where both `change_type` scopes already appear and already differ.**
  Excluded because the source plan's adversarial review re-read all four at HEAD and found its D2
  done-when met; re-opening them spends review budget on text that is already correct.
- **The two carve-out sites refuted during the 340 adversarial review** —
  `manage-execution-manifest/SKILL.md`'s deriver-scoped sentence and the router comment/docstring.
  Excluded because they were re-read and found accurate: both attribute the `compile` /
  `test-compile` pair explicitly to what the deriver emits, which is true, so neither presents the pair
  as the carve-out's complete set.
- **Regenerating the plugin cache or the script executor.** Excluded because both are machine-local
  build steps over git-ignored trees, unavailable and meaningless in a cloud clone; the merged bundle
  source is authoritative.

## Expected surface

Files this plan is expected to touch. Anything else changing is collateral and is reported.

- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py` — D3(a)(b)(c)(d).
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — D8(b), the
  `planning-lane` subparser description.
- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — D3(d); D8(e).
- `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md` — D8(e).
- `test/plan-marshall/manage-status/test_planning_lane_corroboration.py` — D3's new tests and D3(e)'s
  updates to the existing ones; D8(a).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
  — D2, D4(a), D5(a).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_decide.py` —
  D2 (`_read_settled_change_type`), D6(f) (`_LEGACY_CI_WAIT`).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py`
  — D5(a)(b).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_rules.py` —
  D6(a), the `_VERB_TO_PHASE_5_STEP` comment only.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md` —
  D6(a)(b)(c)(e); D8(c).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md` — D6(b)(d).
- `test/plan-marshall/manage-execution-manifest/test_compose_change_type_reconciliation.py` — D2, D4.
- `test/plan-marshall/manage-execution-manifest/test_compose_execution_tier.py` — D5.
- `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_validate.py` — D8(c).
- `test/plan-marshall/manage-execution-manifest/test_validate_loadable.py` — D8(d), docstring only.
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — D6(a).
- `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`
  — D6(f), only if the constant is classified out rather than marked.
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` and
  `.../phase-5-execute/standards/sync-with-main.md` — D7(a).
- `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md` — D7(b).
- `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` — D7(c).
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md`,
  `.../manage-solution-outline/standards/solution-outline-standard.md`,
  `.../manage-solution-outline/templates/deliverable-template.md` — D8(e).
- Possibly further `.md` files under `marketplace/bundles/plan-marshall/skills/` — **only** those
  D1(b)'s sweep establishes as `baseline-reconcile` consumers that read `conflict_count` without
  branching on `status`. This entry is deliberately open because D1(b), not this list, settles the
  membership; the run names every file it added here and every candidate it classified out.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 350/G1 reproduces at HEAD: `cmd_compose` validates the supplied value against `VALID_CHANGE_TYPES` but never the settled value returned by `_read_settled_change_type` | OBSERVED | `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — `cmd_compose`, the `settled_change_type != supplied_change_type` block; `_manifest_core.py` — `VALID_CHANGE_TYPES` |
| 240/G2 reproduces at HEAD: the corroboration branch tests only `scope_resolved_noncommittal` and never the band's provenance | OBSERVED | `.../manage-status/scripts/_cmd_planning_lane.py` — `evaluate_signals_pure`, the `fired == ['S7:risk_prose'] and scope_resolved_noncommittal` branch |
| 240/G5 reproduces: `scope_resolved_noncommittal` is defined by two `not in` exclusions, and the comment above it claims the residue "is exactly {single_module}" and "adapts automatically" | OBSERVED | same symbol and the comment block immediately above it |
| 240/G1 reproduces: `low_confidence` is `signals_null > signals_resolved` over the seven-member `signals` dict | OBSERVED | same file, the `confidence` dict in `evaluate_signals_pure` |
| 350/G4 reproduces: the `change_type_scope_conflict` `return` precedes the `_emit_decision_log` call | OBSERVED | `manage-execution-manifest.py` — `cmd_compose`, refusal `return` then `_emit_decision_log` |
| 350/G2 reproduces: the log test asserts bare substrings that hold under either scope | OBSERVED | `test/plan-marshall/manage-execution-manifest/test_compose_change_type_reconciliation.py` — `test_reconciliation_emits_auditable_decision_log_line` |
| 340/G1 reproduces: the call-site comment still says the error names "the offending ORIGINAL marshal.json key" | OBSERVED | `manage-execution-manifest.py`, comment block above `check_emitted_steps_resolvable(...)` |
| 340/G2 reproduces: the `marshal_map is None` branch emits "in marshal.json is unresolvable" | OBSERVED | `_manifest_validation.py` — `check_emitted_steps_resolvable`, the CSV-fallback `return` |
| 302/G6 reproduces: `terminal_emission_dropped` appears in `manage-execution-manifest.py` and in no `.md` under `marketplace/` | OBSERVED (asserted absence — re-verify by sweeping `marketplace/` for the token before editing) | the compose return dict in `manage-execution-manifest.py`; `manage-execution-manifest/SKILL.md`; `decision-rules.md` § Outputs |
| 100/G8, 100/G9, 330/G4, 050/G3, 310/G2, 310/G7, 210/G1, 300/G6, 300/G7, 240/G3, 240/G4, 350/G3 each reproduce at HEAD | OBSERVED | the file and symbol each gap names, all git-tracked under `marketplace/`, `test/` and `.claude-plugin/`; and the full entry in the source `doc/plans/truthful-signals/{plan}/gaps.md` |
| The build-phase-canonical carve-out currently covers more than the two canonicals the three sites name | HYPOTHESIS | D1(a): evaluate `_check_step_resolvable(f'verify:{verb}', 'phase_5')` over `ALL_CANONICAL_COMMANDS` at HEAD. The source gap recorded seven of fourteen at its authoring time — **treat that as a lead, not a count**, and re-derive |
| The `baseline-reconcile` consumer set that reads `conflict_count` without branching on `status` is exactly the two `phase-5-execute` documents 310/G7 names | HYPOTHESIS — expected **false** | D1(b): an authoring sweep of `marketplace/` found several further `.md` files carrying both tokens (under `phase-6-finalize/`, `phase-2-refine/` and `plan-marshall/`), so the population is materially larger than the gap's two candidate files. Re-derive the membership and classify every returned file before D7(a) edits anything — do not treat the gap's two as the set |
| The expected surface above is complete | HYPOTHESIS | the two "possibly" entries are settled by D1(b); everything else is the union of the files the twenty-two gap entries name, re-checked as each deliverable opens its files. Collateral change outside this list is reported, not absorbed |
| No gap in this plan is already closed at HEAD | OBSERVED | every gap above was opened at its named file and symbol during authoring and reproduced; the run re-checks each before editing and records any that no longer reproduces as already-closed rather than fixing it |

An asserted **absence** is verified exactly as an asserted presence and is the higher-risk half here:
302/G6's "no `.md` mentions the field", D5's "no docstring contains the string", D7(b)'s zero-hit gate
and D6(c)'s "no line presents `auto` as a lane value" are all absences, and each is re-run as a sweep
whose **population is stated alongside its hit count**.

## Verification

Beyond each deliverable's *Done when*:

1. **Build gate.** This plan changes `*.py` under `marketplace/` and `test/`, so the conditional build
   gate fires. Run the repository's verify command as `cloud-plan-lane` prescribes, and read its
   result rather than its exit code.
2. **Targeted suites, run and named in the report.** At minimum:
   `test/plan-marshall/manage-status/` (D3, D8(a)(b)),
   `test/plan-marshall/manage-execution-manifest/` (D2, D4, D5, D6, D8(c)(d)), and
   `test/plan-marshall/phase-2-refine/test_phase_2_refine_manage_config_readonly.py` (D7(c)).
3. **Red-first evidence for D4.** Both mutations in D4's *Done when* are applied, the failure observed
   and recorded, and the mutation reverted. A vacuous-guard gap is closed only by a test that has been
   **seen red** against the defect it names — if a mutation does not turn the test red, the gap is
   **not** closed and the run says so rather than claiming it.
4. **Cold reads — an independent reader takes the text and reports which reading it took.** Four
   texts in this plan are worth only what they make a later reader do, and "implemented as specified"
   cannot verify any of them. Dispatch each to the pre-PR verification sub-agent (`cloud-plan-lane`
   § Step 6) **without** telling it the intended answer, and record the reading it returned:
   - **D7(a)** — show it the rewritten `phase-5-execute` Step 3 and ask: *given a `baseline-reconcile`
     return carrying `status: error, error: merge_base_unresolved` and no `conflict_count` field, what
     does this instruct you to do?* The only acceptable reading is **abort and return the drift TOON**
     — anything that self-absorbs, records a baseline, or continues the task loop means the wording
     failed however complete it looks.
   - **D6(e)** — show it the rewritten declaration-vs-record subsection and ask whether
     `finalize-step-simplify`'s current gate is *permitted* or *forbidden* by this document. The
     acceptable reading is **permitted, as a named exception with a stated reason**. A reading of
     "forbidden" means the contradiction survived the edit.
   - **D6(a)** — show it the rewritten carve-out sentence and ask which build verbs the carve-out
     covers. The acceptable reading names the **derived predicate** as the authority and the two
     deriver-emitted verbs as examples; a reading that returns a fixed two- or seven-item set as the
     contract means the wording re-froze the thing D1(a) exists to keep derived.
   - **D8(e)** — show it exactly **one** of the five annotated sites, with no other document, and ask
     which of the two `change_type` scopes that field carries. The acceptable reading identifies the
     right scope from that page alone; needing a second document means the annotation failed its
     purpose.
5. **Re-derivation at the moment of the claim.** Every count this plan mentions is a lead. Before D6(a)
   and D7(a) are written, D1's two derivations are re-run and their outputs — not this plan's prose —
   are what the edits cite. Any sweep reported in the run report states its **population** and its
   **hit count** separately; a bare "zero hits" is not evidence.
6. **Per-gap coverage read-back.** Before the PR is opened, walk the twenty-two gap ids in the
   deliverable headings against the source `gaps.md` entries under
   `doc/plans/truthful-signals/*/gaps.md` (git-tracked, readable from the clone) and state, per id,
   closed / not closed / no longer reproduces. An id that is not closed is reported as not closed —
   an overstated outcome is collected as done and never picked up again.

## Notes

- **`.plan/` does not exist in this clone.** It is git-ignored, so the orchestrator ledger, the plan
  specs, the generated `execute-script.py` executor and any `marshal.json` are **absent**. Several
  gaps quote strings like `.plan/marshal.json` and `status.metadata.change_type` — in every case those
  are *text inside a document, a comment or a test fixture*, never a file to open. Do not go looking
  for a `.plan/` tree, and do not invoke `python3 .plan/execute-script.py`; the tests build their own
  synthetic repositories under `tmp_path`.
- **Three orderings are forced by cross-coupling.** D3(d) rewrites the corroboration
  prose that D8(b) then has to match; write D8(b) against D3's rule, not the pre-D3 one. Similarly D6(a)
  cites D1(a)'s derivation, and D7(a)'s consumer list is D1(b)'s output.
- **Adversarial-review dispositions carried across.** No gap assigned to this plan was refuted. Three
  narrowings from the source reviews are honoured in the deliverables and repeated here so they are not
  re-litigated: 350/G3 is residue *beyond* the source plan's D2 rather than a shortfall against it (its
  D2 done-when was re-checked and found met); two of 340/G3's originally-cited sites were refuted as
  accurate and are excluded; and 240/G2's clause requiring a `scan_incomplete`-banded S7-alone vector
  to route `deep` was refuted as unreachable by construction (`scan_incomplete` bands as
  `multi_module`, which fires S2) and is **not** carried into D3.
- **Severity mix.** Two `high` (350/G1, 240/G2), fourteen `medium`, six `low`. The ordering puts both
  `high` items in D2 and D3 so a run that stops early has shipped them. D1 precedes them only because
  it writes no file and its failure would mean the plan is unexecutable anyway.
- **Eight deliverables rather than the usual six-or-fewer.** The gap set spans three independent
  mechanisms (the planning-lane router, the compose reconciliation, the manifest's own contract
  documents) plus two consumer surfaces; collapsing them further would produce a deliverable no single
  reviewer can hold. D1 writes no file, the seven working deliverables are each independently
  reviewable, and D3, D6, D7 and D8 are lettered so a partial completion can be reported per sub-item.
- **The source gap documents are git-tracked** under `doc/plans/truthful-signals/{plan}/gaps.md` and
  are readable from this clone. Where this plan compresses a gap, the entry there carries the full
  Kind / Severity / Where / What is wrong / Why it matters / Fix / Done when, plus the sibling
  `verification.md` § "Adversarial review". Read the entry before writing the fix; read the
  adversarial section before disagreeing with the entry.
