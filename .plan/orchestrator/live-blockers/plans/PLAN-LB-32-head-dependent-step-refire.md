# PLAN-LB-32: Head-dependent project steps: a fix commit re-examines only what it could have changed

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-32-head-dependent-step-refire.md` and is queued as one row file, `queue/PLAN-LB-32.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-09 by operator instruction, at high priority, after the Watch "Head-dependent
> finalize steps re-fire in full on every fix commit" met its trigger. Every OBSERVED claim below
> was read at HEAD `97f341b6c`.

## Objective

Every commit made during finalize — a self-review fix, a review-bot fix — moves HEAD, and every
finalize step that depends on HEAD is then run again from the start. For two project steps this
is almost always wasted work: `project:finalize-step-lessons-housekeeping` re-classifies the whole
lessons corpus and `project:finalize-step-plugin-doctor` re-runs its gate, and both return the
verdict they returned before. On three landings in a row they fired five, seven and eight times
each with identical results; on the last one that cost at least 1.68 million tokens and filled
the decision log with 710 entries, so that later steps could no longer read it in full.

The mechanism that could skip such a re-fire, `verdict_inputs`, does not fit either step, and the
step documents say why: it admits static path globs only, while housekeeping reads a git-ignored
corpus and plan records, and plugin-doctor's rules read link targets and agent files across the
whole repository. Those refusals are sound and this plan does not overturn them by declaring a
glob. It makes the re-fire itself cheap instead: a re-fired step learns what changed since its
last firing and re-examines only what that change could affect, carries the rest of its previous
verdict over, and says in one line what it carried. In the same two documents it replaces two
stale reads of the plan's footprint — one of a retired field, one of the declared list where the
realized set is meant — because the delta rule is only as good as the footprint it starts from.

## Deliverables

1. **A re-fired step can ask what changed since its last firing.** One deterministic, read-only
   verb returns, for a plan and a step, the HEAD recorded at that step's last `done` firing, the
   live HEAD, and the tracked paths that differ between them — the same pair and the same diff
   `verdict_currency` already computes in `resolve_changed_paths`, exposed for the step to read.
   It reports a first firing (`recorded_head: none`) and an uncomputable diff as distinct,
   named outcomes, never as an empty change list. Reuse the existing derivation; do not write a
   second one. *Done when:* a test in a real temporary repository records a firing, adds one
   commit touching two files, and reads exactly those two paths back; a test with no prior
   firing and a test with an unreachable recorded commit each get their named outcome and no
   `changed_paths` key that could be read as "nothing changed".

2. **Lessons-housekeeping re-examines only the lessons a commit could affect.** On a re-fire
   with a computable change list, the step re-classifies a lesson only when (a) the lesson was
   added or edited since the last firing, or (b) its component's standards directory, or a path
   the lesson names, intersects the changed paths. Every other lesson keeps the classification
   of the previous firing. Which lessons fall under (a) and (b) is answered by a script, not by
   the agent reading the corpus: a script in the step's own skill directory takes the change
   list and the time of the last firing and returns the affected lesson ids with the reason for
   each. It lives with the step, not in `manage-lessons`, because the step is project-local and
   five specs of the `lessons-routing` epic are staged against `manage-lessons.py`; it imports
   that script's component-to-directory helper and edits nothing there. A first firing,
   an uncomputable diff, or a previous firing that did not finish cleanly runs the full
   classification as today. *Done when:* a test builds a corpus of several lessons in three
   components, passes a change list touching one component, and reads back exactly that
   component's lessons plus one lesson edited after the recorded time; a test with an empty
   change list and no edited lesson returns zero affected lessons; the step document states the
   three full-run conditions; and a cold reader given only the amended document answers
   "none — carry the previous classification" to "which lessons do you classify when the commit
   touched only test files and no lesson changed?".

3. **A firing writes one line for what it kept.** The step document requires a decision-log
   entry for every deliberate retain, per lesson, per firing. Replace that with one aggregate
   entry per firing naming the counts (re-examined, carried over, retained) and, on a delta
   firing, the recorded HEAD it started from. Removals, promotions and adaptations keep one
   entry each: they change the corpus and must stay individually traceable. *Done when:* the
   amended Step 6 states the rule; a doc-contract test asserts the document no longer requires
   a per-lesson entry for a retain and still requires one for each of the three mutating
   outcomes.

4. **Lessons-housekeeping reads the realized footprint.** Step 1 calls
   `manage-references get --field modified_files`, a retired field that returns `field_retired`,
   so the step has run without a footprint on every firing since the retirement. Replace it with
   `manage-references compute-footprint`, handle each of that verb's error outcomes by name, and
   correct the other places in the document and in `verdict-currency.md` that name the retired
   field. *Done when:* a doc-contract test asserts no document under `.claude/skills/` or
   `marketplace/bundles/plan-marshall/skills/` instructs a read of `modified_files`, and the
   step document's footprint read names `compute-footprint` with its required arguments.

5. **Plugin-doctor gates what the plan changed, not what it declared.** The step derives its
   skill directories from `references.affected_files`, the footprint declared at outline time.
   Files changed by fix tasks and fix commits never enter that list: on PLAN-LB-23 it held 46
   entries while the branch touched 56 files, and the gate covered 10 of 14 touched skill
   directories on its first two firings. Derive the scope from `compute-footprint`, united with
   the declared list so a declared-but-untouched directory is still gated; keep the whole-tree
   triggers as they are, evaluated against the same united set. *Done when:* a test gives the
   scope derivation a declared list naming two skill directories and a realized set naming a
   third and reads back all three; the whole-tree trigger test passes when the triggering path
   is in the realized set only; the wrapper test's docstring no longer says the wrapper reads
   `modified_files`.

6. **Plugin-doctor skips a re-fire that cannot change its verdict, and says why.** Its recorded
   refusal stands for static globs. Settle, on the evidence of the verify-first clause below,
   whether a narrower rule is sound: a re-fire is skipped when the change since the last firing
   adds, deletes and renames no tracked path, and modifies no path inside a gated skill
   directory, no agent file the two whole-repository analyzers read, and no file of the
   plugin-doctor or plan-doctor skills themselves. Such a change can alter neither a rule's
   input nor the existence of any link target. If the clause shows the rule is unsound, the
   deliverable is the recorded reason, in the step's refusal section, and nothing else. If it
   is sound, the skip is decided by a script from the change list of deliverable 1, the step
   records the skip with the reason and the recorded HEAD, and the refusal section is rewritten
   to say what is refused (a static glob) and what is admitted (this predicate). *Done when,
   under the sound branch:* tests show a modify-only change outside the listed paths is
   skipped, and that one added file, one deleted file, one rename, and one modified file inside
   a gated directory each force a full run; the first firing always runs. *Done when, under the
   unsound branch:* the refusal section names the counter-example.

7. **The currency standard and its guards describe what the two steps now do.**
   `verdict-currency.md` says no step declares a surface and lists both steps as refusals; the
   guards in the three `test_verdict_currency_*` modules pin them as undeclared. Both stay
   undeclared — this plan adds no `verdict_inputs` — so those guards must keep passing
   unchanged. Add to the standard's levers section the third lever this plan builds: a step
   that cannot declare a static surface narrows its own re-fire from the change list, and name
   the two steps that use it. State in the extension-point contract that a step may read the
   change list, and what it must do when there is none. *Done when:* the existing guard tests
   pass without edits to their assertions; a doc-contract test asserts the standard names the
   lever and both steps, and that each step document's refusal section and its delta rule do
   not contradict each other (the section says what is refused, the rule says what is done
   instead).

## Claim Labels

- OBSERVED: the classifier is `phase-6-finalize/scripts/verdict_currency.py`: `classify_step` orchestrates, `classify_advance` is the pure decision, `resolve_verdict_inputs` reads the declaration, `resolve_changed_paths` runs `git diff --name-only {recorded} {live}` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py:178-206`, `:239-292`, `:295-340`, `:365-485`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict_currency.py: classify_advance 178-206 (pure), resolve_verdict_inputs 239-292, resolve_changed_paths 295-340 runs git diff --name-only recorded live (318-332), classify_step 365-485 orchestrates.
- OBSERVED: the two verdicts are `preserved` and `invalidated`; an empty or absent declaration gives `invalidated` with reason `verdict_inputs_undeclared` — `verdict_currency.py:129-144`, `:200-201`, `:450-460`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict_currency.py: VERDICT_PRESERVED 129, VERDICT_INVALIDATED 132, REASON_UNDECLARED = 'verdict_inputs_undeclared' 139; empty declaration returns invalidated at classify_advance 200-201 and classify_step 450-460.
- OBSERVED: `verdict_inputs` is a frontmatter key of the step document holding a list of fnmatch globs over tracked repository-relative paths; a non-list value is treated as empty — `verdict_currency.py:84-88`, `:121`, `:266`, `:282-290`; the contract row at `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:56` ("The declaration MUST be a superset of what the step reads", "Absence is the fail-closed default")
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict_currency.py 84-88 (fnmatch convention), VERDICT_INPUTS_KEY 121, frontmatter read 282-285, non-list treated as empty at 288-289. ext-point-finalize-step.md row at line 56 carries both quoted sentences.
- OBSERVED: a derived surface is excluded on purpose — "The vocabulary is deliberately static globs; admitting a *derived* surface — a command whose output is the path set — would make shape 2 declarable, and is not attempted here" at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md:189-190`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict-currency.md lines 189-190 carry the quoted sentence verbatim: static globs by design, a derived surface is not attempted.
- OBSERVED: no finalize step declares `verdict_inputs` today; the standard says so at `verdict-currency.md:154`, and a search for a line starting `verdict_inputs:` under `marketplace` and `.claude` returns nothing. Ten step documents are head-dependent and undeclared, among them `.claude/skills/finalize-step-plugin-doctor/SKILL.md:11` and `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:14`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict-currency.md:154 says no step declares it; inventory search for ^verdict_inputs: gives 0 hits and the 5 .claude finalize-step frontmatters carry none. head_dependent: true in 7 marketplace docs plus 3 .claude docs (plugin-doctor:11, housekeeping:14, review-retrospective:16) = 10.
- OBSERVED: lessons-housekeeping records its refusal under "Verdict-input surface — deliberately undeclared": its verdict reads the plan's records and the lessons corpus, both git-ignored, and "Whichever standards clause a lesson names … the set cannot be written down ahead of the run" — `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:59-69`; added by `6b00815e0` (#1718)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: finalize-step-lessons-housekeeping/SKILL.md section 'Verdict-input surface - deliberately undeclared' at 59-69; quoted clause at line 67. git log -S shows the section added by 6b00815e0 (#1718).
- OBSERVED: plugin-doctor records its refusal in the same form: the `broken-relative-link` rule stats link targets anywhere under the repository root, and `analyze_agentfile_line_budget` and `analyze_agentfile_directory_tree` walk the whole repository, so "no proper subset of the tree is sound here" — `.claude/skills/finalize-step-plugin-doctor/SKILL.md:48-57`; added by `ee78fd918` (#1235), before PLAN-LB-22
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: finalize-step-plugin-doctor/SKILL.md section at 48-57: broken-relative-link line 54, the two agentfile analyzers line 55, 'no proper subset of the tree is sound here' line 57. Added by ee78fd918 (#1235); the PLAN-LB-22 ordering is not checkable from git.
- OBSERVED: both refusals are listed in the table at `verdict-currency.md:182-187`, and four tests pin tabled refusals as undeclared — `test_every_tabled_refusal_carries_its_section` (`test/plan-marshall/phase-6-finalize/test_verdict_currency_cli.py:411`), `test_every_project_local_refusal_row_resolves_to_a_project_skill_document` and `test_every_head_dependent_step_named_in_the_table_declares_no_surface_in_its_own_frontmatter` (`test_verdict_currency_currency.py:460`, `:490`), `test_no_tabled_refusal_also_declares_a_surface` (`test_verdict_currency_stale_evidence.py:386`)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: verdict-currency.md table 182-187 lists both steps (185, 187). Tests at the cited lines: test_verdict_currency_cli.py:411, test_verdict_currency_currency.py:460 and :490, test_verdict_currency_stale_evidence.py:386.
- OBSERVED: lessons-housekeeping Step 1 reads `manage-references get --plan-id {plan_id} --field modified_files` — `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:101-102`; the field is retired: `RETIRED_REFERENCE_FIELDS = frozenset({'modified_files'})` and `retired_field_error` returning `error: field_retired`, enforced at the CLI boundary — `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py:125`, `:133-158`, `manage-references.py:180-183`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: housekeeping SKILL.md Step 1 at 100-103 reads --field modified_files. _references_core.py: RETIRED_REFERENCE_FIELDS 125, retired_field_error 133-157 returns error field_retired; CLI guard at manage-references.py 180-183.
- OBSERVED: the step has no carry-over rule — "the classification is a fresh read each time" at `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:57`; it reads the corpus through `manage-lessons list-stalled` and `manage-lessons list --full` (`:124`, `:146`)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: housekeeping SKILL.md line 57: 'the classification is a fresh read each time'; no carry-over rule anywhere in the doc. Corpus reads: list-stalled at line 124, list --full at line 146.
- OBSERVED: the step requires one decision-log entry per lesson per firing — "Record a decision-log entry for **every** removal, **every** promote-then-retire, **every** adaptation, **and every** deliberate retain" at `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:284`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: housekeeping SKILL.md Step 6 line 284 carries the quoted sentence verbatim; the decision-log call follows at 286-290.
- OBSERVED: plugin-doctor Step 1 reads `manage-references get --plan-id {plan_id} --field affected_files` and Step 2 filters it to skill directories; whole-tree mode is chosen when that list touches the plugin-doctor or plan-doctor skills, or when the read fails with `field_not_found` — `.claude/skills/finalize-step-plugin-doctor/SKILL.md:64-65`, `:72-76`, `:84-86`; a scoped run still runs `validate_extension_contracts` whole-tree (`:90`)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: plugin-doctor SKILL.md: Step 1 affected_files read 63-66, Step 2 skill-dir filter 72-76, Step 2.5 whole-tree modes 84-85 (doctor skills touched, or field_not_found), scoped mode 86; validate_extension_contracts whole-tree exception at line 90.
- OBSERVED: `manage-references compute-footprint` exists, is read-only, takes `--plan-id` and `--worktree-path` and returns `status, plan_id, base_ref, base_ref_source, files, live_count`, with the named errors `worktree_not_found`, `references_not_found`, `not_a_git_worktree`, `git_error`, `files_out_refused`, `files_out_unwritable` — `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage-references.py:111-126`, `_cmd_compute_footprint.py:43`, `:106-113`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-references.py compute-footprint parser 110-138 (--plan-id, --worktree-path required; also optional --base-ref, --files-out). _cmd_compute_footprint.py handler 43, success payload 105-112, all six error codes at 55, 64, 73, 89/100, 125, 132.
- OBSERVED: the dispatcher consults the classifier in `phase-6-finalize/SKILL.md` § "Special case — HEAD-dependent steps" and branches on `verdict` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:563-570`, `:592-604`; a preserved skip is recorded as a `skipped` row (`:801-810`)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: phase-6-finalize/SKILL.md: 'Special case - HEAD-dependent steps' 563 with table 565-573 (classifier row 569); classifier call and verdict branches 592-604; preserved skip recorded as a skipped record-step row at 795-806.
- OBSERVED: the wrapper test's docstring still says the wrapper reads `references.modified_files` — `test/plan-marshall/finalize-step-plugin-doctor/test_finalize_step_plugin_doctor.py:4`; no test directory exists for the lessons-housekeeping step
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: test_finalize_step_plugin_doctor.py lines 4-5 still say the wrapper reads references.modified_files. test/plan-marshall/ at HEAD has finalize-step-plugin-doctor/ but no lessons-housekeeping directory; inventory find for the name returns 0 paths.
- OBSERVED: `manage-lessons` has a component-to-standards-directory helper, `_derive_standards_dir` — `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py:737`
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-lessons.py: def _derive_standards_dir(component) at line 737 (body to 762), maps a bundle:skill component to {bundles}/{bundle}/skills/{skill}/standards/.
- HYPOTHESIS: the cost is as reported — both steps fired five times on PLAN-LB-14, seven on PLAN-LB-22 and eight on PLAN-LB-23, each time with an identical verdict ("0 rm, 0 promo, 0 adapt, 64 keep" for housekeeping on all eight); at least 1,680,033 tokens over 13 identifiable dispatch rows on PLAN-LB-23, six housekeeping rows at 84 to 88 tool uses and seven plugin-doctor rows at 16 to 18; a decision log of 710 entries and 180 KB. Reported by the three plans' retrospectives, not measured here — confirm/refute on this plan's own finalize, which is the first to run the changed steps (verify-at-outline)
- HYPOTHESIS: on PLAN-LB-23's fourth firing the housekeeping leaf already applied the delta rule by hand (four lessons re-examined, sixty carried over) and reached the same verdict, which is the evidence that the rule is workable — reported by that plan's retrospective, not reproduced here; confirm/refute by replaying one recorded fix commit of an archived plan through the verb of deliverable 2 (verify-at-outline)
- HYPOTHESIS: the recorded HEAD of a step's last firing is readable from the plan's status record under the key the classifier already uses (`head_at_completion`) — confirm/refute at `verdict_currency.py` § `classify_step` and the `manage-status` step-record reader it calls (verify-at-outline)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: head_at_completion is stored on status.metadata.phase_steps[phase][step] (_cmd_mark_step.py _build_entry 844-846; reader find_step_record 773-785). But classify_step calls no manage-status reader: the SHA arrives as --head-at-completion (verdict_currency.py 494-499). prior_firings keep no SHA.
- HYPOTHESIS: a lesson file carries, or its file metadata gives, a reliable "last changed" time to compare with the time of the last firing — confirm/refute at `manage-lessons.py` § the list and frontmatter readers; if neither does, deliverable 2(a) compares a content hash recorded at the last firing instead (verify-at-outline) — ⛔ RE-SCOPED 2026-10-09 at `4ed67e228`: refuted. `cmd_list` (`_lessons_query.py:101-149`) emits no time field, the frontmatter carries only `created`, no reader stats the file, and `restore-from-plan` moves files with `shutil.move`, which keeps the old modification time. Deliverable 2(a) therefore uses the fallback: the step records a content hash per lesson at each clean firing and compares against it
  - verdict: contradicted | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: yes | evidence: No reliable last-changed time: _lessons_query.py cmd_list 101-149 emits no time field; frontmatter has created, and last_seen only for arch-constraint (_lessons_crud.py 346). No reader stats mtime, and restore-from-plan moves files (shutil.move, line 601), keeping the old mtime.
- HYPOTHESIS: the lane key `prunable_when: footprint_no_lesson_component` in the housekeeping frontmatter has no evaluator in Python and appears only in documents and one comment (`ext-point-lane-element.md:180`, `_config_defaults.py:576`) — confirm/refute by a content search; if it holds, deliverable 2's verb is the first deterministic reading of "the footprint touches no lesson component" and the lane key is left as it is (verify-at-outline)
  - verdict: corroborated | checked_at: 4ed67e228 | by: live-blockers/cleanup | rescoped: n/a | evidence: No Python evaluator: the token is in _config_defaults.py only as a comment (576) and _manifest_lanes.py only parses prunable_when (56-91). Docs: ext-point-lane-element.md:180, plus manage-config/SKILL.md, data-model.md, lessons-capture.md and the housekeeping frontmatter line 5.
- HYPOTHESIS: recurrence, folded in on 2026-10-09 from inbox message `plan-lb-29-harness-sync-012.md`: on plan `plan-lb-29-harness-sync` the housekeeping step fired three times, each time got `field_retired` from its Step 1 read and used `compute-footprint` with flags taken from `--help` (60 files on the third firing). Reported by that plan's retrospective, not reproduced here; it matches the OBSERVED claim above on Step 1. It adds two things for deliverable 4 to weigh: sweep every project-local step document under `.claude/skills/` for the same retired read, by a direct search, because that tree is outside the inventory content search; and have the `field_retired` error name the replacement call — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py` § `retired_field_error` (verify-at-outline)
- HYPOTHESIS: folded in on 2026-10-09 from inbox message `lessons-routing-001.md` (retired lesson `2026-10-02-10-005`): a finalize step that itself commits after the review band — a generated commit such as an architecture refresh or a baseline sync — moves HEAD and so re-fires every head-dependent step on each re-entry, although the commit holds nothing a reviewer or a project step judged. Reported from earlier plans, not reproduced here. Under this plan's delta rule such a commit should cost the two project steps a cheap re-fire; confirm that on a fixture whose only change since the last firing is a generated path, and name the generated paths the rule treats as unable to affect either step — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` § `classify_step` (verify-at-outline)
- Verify-first clause: settle deliverable 6 before any code. For every rule and analyzer the plugin-doctor gate runs in scoped mode, including the whole-tree `validate_extension_contracts`, list what it reads. The predicate is sound only if each input is either inside a gated skill directory, an agent file the two analyzers read, a file of the doctor skills, or the mere existence of a path. One rule that reads the CONTENT of a file outside those sets refutes it; name that rule in the refusal section and stop.
- Verify-first clause: decide where deliverable 1's verb lives before writing it. It needs the recorded HEAD (a `manage-status` step record) and the diff (`verdict_currency`). Adding a subcommand to `verdict_currency.py` keeps one derivation and touches no document outside this plan's surface; a dispatcher-side hand-over, where the dispatcher passes the change list into the step's dispatch, needs an edit to `phase-6-finalize/SKILL.md`, which plans in flight are editing. Prefer the subcommand; take the dispatcher edit only if the step cannot resolve its own step id and plan id for the call. Read on 2026-10-09 at `4ed67e228`: the existing `classify` subcommand cannot serve as it is — its payload has a `changed_paths` key, but for a step with no `verdict_inputs` it returns (450-460) before the diff runs, so the key is empty for both steps of this plan; a new subcommand or a reordering is needed. `classify_step` reads no status record: the recorded HEAD arrives as `--head-at-completion`. The record lives at `status.metadata.phase_steps[phase][step].head_at_completion` (`manage-status/scripts/_cmd_mark_step.py` § `find_step_record`), and `prior_firings` keep no HEAD, so only the latest firing's HEAD is recoverable.
- Verify-first clause: confirm a carried-over classification is safe when the previous firing is not the immediately preceding one — a firing may have been skipped, failed or been interrupted. The carry-over must start from the last firing that completed cleanly and that this plan's rule recorded; a firing recorded before this plan landed has no carried state and forces a full run.
- Verify-first clause: confirm a script under `.claude/skills/{skill}/scripts/` is registered with the executor and can import `_derive_standards_dir` from the `manage-lessons` script directory without editing that script (see how `.claude/skills/finalize-step-plugin-doctor/` ships and calls its own script). Read on 2026-10-09 at `4ed67e228`: plugin-doctor ships no script of its own. The working precedent is `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py`, registered by `discover_local_scripts` as `default-bundle:{skill}:{script}` and importing marketplace modules by plain name. `_derive_standards_dir` sits in the hyphenated `manage-lessons.py`, which a plain `import` cannot name; reaching it needs a load by file path, which runs that module's top-level imports. Its underscore siblings (`_lessons_io`, `_lessons_query`) import normally. If the import is not possible, copy nothing: return to the operator with the choice between a `manage-lessons` verb, which collides with the `lessons-routing` epic's staged specs, and a shared helper module.
- Verify-first clause: the two step documents live under `.claude/skills/`, project-local to this repository. Confirm how a project-local step is tested here (the plugin-doctor wrapper has a test directory, housekeeping has none) and whether the doc-contract tests this plan adds belong under `test/plan-marshall/` or a project-local test directory, before creating one.

## Expected Surface

- OBSERVED: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — Step 1 footprint read, the delta rule, Step 6 logging, the refusal section, error handling (D2, D3, D4, D7)
- OBSERVED: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — Steps 1 to 3 scope derivation, the skip predicate or the recorded counter-example, the refusal section (D5, D6, D7)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — the change-list verb, reusing `resolve_changed_paths` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` — the levers section, the refusal table rows for the two steps, the line naming `modified_files` (D4, D7)
- HYPOTHESIS: `.claude/skills/finalize-step-lessons-housekeeping/scripts/affected_lessons.py` — new script answering which lessons a change list affects (D2) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — a step may read the change list (D7)
- OBSERVED: `test/plan-marshall/finalize-step-plugin-doctor/test_finalize_step_plugin_doctor.py` — scope derivation, whole-tree trigger, docstring (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — script table and canonical invocation for the new verb; the dispatcher section only under the dispatcher-side hand-over (D1) (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-plugin-doctor/scripts/` — a script deciding the skip predicate, only under the sound branch of deliverable 6 (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_verdict_currency_changed_paths.py` — new tests for the change-list verb (D1) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/finalize-step-lessons-housekeeping/test_affected_lessons.py` — new tests for the affected-lessons script (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_head_dependent_step_refire_doc_contract.py` — new doc-contract tests over the two step documents and the standard (D3, D4, D7) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/finalize-step-plugin-doctor/test_plugin_doctor_refire_skip.py` — new tests for the skip predicate, only under the sound branch (D6) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Priority: high. It is to be launched ahead of PLAN-LB-25 to PLAN-LB-28: every plan that reaches finalize pays this cost once per fix commit until it lands.
- Suggested order inside the plan: deliverable 1 first (2 and 6 read its output); then 4 and 5 (the footprint reads, independent of the delta rule); then 2, 3 and 6; 7 last.
- Overlaps with: PLAN-LB-24, PLAN-LB-25 and PLAN-LB-27 on `phase-6-finalize/SKILL.md`, and only if deliverable 1 takes the dispatcher-side form or the script table is edited; PLAN-LB-27 on `ext-point-finalize-step.md`, which that plan touches only under two of its three allowlist options. No other declared file is shared with a live plan.
- Kept clear of the `lessons-routing` epic: five of its staged specs (PLAN-LR-01, 02, 03, 05, 06) declare `manage-lessons/scripts/manage-lessons.py`. This plan reads that script's helper and does not edit it.
- Takes over from PLAN-LB-27: the plugin-doctor consumer of `affected_files` and the housekeeping read of the retired field, which that spec's verify-first clause says are "not fixed here: name them in the PR". They are fixed here (deliverables 4 and 5). PLAN-LB-27 keeps the question of whether `affected_files` itself should grow.
- Adjacent to: lessons `2026-10-08-21-003` (the proposal this plan narrows) and `2026-10-08-21-001` (the retired-field read, closed by deliverable 4).
- Left out on purpose: the other eight head-dependent steps (simplify, security audit, the Sonar round-trip, CI verify, the pre-push gate, the self-review, automatic review, the review retrospective) — each needs its own reading of what a re-fire could narrow, and the self-review's cost is the subject of the change that shipped as #1726; admitting a derived surface into `verdict_inputs` itself, which the standard rules out and which would change the fail-closed default for every step; a size-aware default for small review-fix commits; an evaluator for the `prunable_when` lane key.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-32-head-dependent-step-refire.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
