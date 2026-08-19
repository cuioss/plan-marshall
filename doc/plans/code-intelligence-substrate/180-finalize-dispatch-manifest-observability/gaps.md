# Gaps — 180-finalize-dispatch-manifest-observability

The plan's central work landed and is well guarded: the finalize dispatcher's four `effort
resolve-target` sites ride the per-firing seam, the completion marker is fused to the
`mark-step-done` handshake on the single write path, and the roster correctness check is genuinely
derived from the finalize-step registry (re-measured: 26 discovered step docs covering all 25
registered steps). What remains is a **population problem and a semantics problem**. The dispatch
migration was applied to `phase-6-finalize/SKILL.md` only, while two dispatch sites in the same
skill still use the pre-seam shape — one of them emitting nothing at all for its spawn — and two
more step docs still instruct a hand-written emit the dispatcher no longer performs. The fused
completion line fires for `loop_back`, an outcome the same documents say owes no completion, and no
test covers it. The start half of the marker pair is still prose. The D6 check's *derivation* is
real but its realized comparison population is **one doc of twenty-five** (G11), because only
`architecture-refresh.md` carries a self-classification sentence. Finally, the test the run's report
names as its N>1 verification for D2 passes against the D2 defect (proved by mutation, twice
independently), so the property is guarded only by the roster-closure detector.

## G1 — Migrate the `finalize-step-simplify` in-body dispatch onto the resolve seam

- **Kind:** incomplete
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md:113` (resolve) and `:127` (`Task: plan-marshall:{target}`)
- **Evidence:** the resolve is bare —
  `effort resolve-target --phase phase-6-finalize` with no `--workflow`, `--plan-id` or `--caller`.
  `_cmd_effort.py:546` (`if workflow:`) gates `_emit_dispatch_records`, so the `[DISPATCH]` line and
  the paired decision-log record are emitted **only** when `--workflow` is supplied; and no
  `--message "[DISPATCH]"` command exists anywhere in that file (re-swept the whole
  `marketplace/bundles/` tree — the eleven surviving hand-written emits are in `plan-marshall`,
  `workflow-pr-doctor`, `phase-3-outline`, and the three finalize files named in G2/G3/G4; none is
  in `finalize-step-simplify.md`). The spawn at `:127` therefore leaves no dispatch record on either
  surface. `default:finalize-step-simplify` is on the dispatched roster
  (`dispatch-inline-split.md:25`).
- **Why it matters:** this is exactly the condition D2 exists to remove — a finalize spawn the
  dispatch count cannot see. `check-dispatch-audit.py:388` computes
  `missing = max(0, len(dispatched) - finalize_dispatch_line_count)`, where `dispatched` is the set
  of terminal finalize steps with non-zero token attribution. `default:finalize-step-simplify` is a
  registered terminal step that dispatches, so it enters the minuend while contributing nothing to
  the subtrahend — and because a *re-fire* of any other step adds a line without adding a step, that
  shortfall is silently absorbed rather than surfacing as a `missing_dispatch_emission` finding. The
  detector under-reports precisely when other steps looped back.
- **Action:** replace the bare resolve with the canonical seam form used at `SKILL.md:1015` —
  `effort resolve-target --phase phase-6-finalize --workflow plan-marshall:phase-6-finalize/standards/finalize-step-simplify.md --plan-id {plan_id} --caller plan-marshall:phase-6-finalize` —
  and state, as SKILL.md:629 does, that the resolve and the spawn are one indivisible pair.
- **Done when:** the resolve at `:113` carries `--workflow`, `--plan-id` and
  `--caller plan-marshall:phase-6-finalize` (the `--caller` is load-bearing: `_cmd_effort.py:493`
  falls back to `plan-marshall:manage-config` when it is absent, and
  `check-dispatch-audit.py:98` (`FINALIZE_DISPATCH_CALLER`) counts finalize lines by that caller,
  so a migration without `--caller` still leaves the line uncounted), and `grep -n 'Task: '` over
  `finalize-step-simplify.md` shows every spawn preceded by that resolve. Independently of this
  entry, G5 widens the automated detector so the condition is machine-checked.
- **Effort:** S
- **Risk if fixed:** one extra `[DISPATCH]` + decision-log record per simplify dispatch; any
  archived-corpus comparison of dispatch counts across the change point shifts by that amount.

## G2 — Replace the hand-written `[DISPATCH]` emit in `pre-submission-self-review` with the seam resolve

- **Kind:** bug
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:194` (bare resolve), `:204` (hand-written emit), `:210` (`Task:`)
- **Evidence:** `:204` reads, verbatim,
  `--message "[DISPATCH] (plan-marshall:phase-6-finalize) target={target} level={level} role=default workflow=plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md plan_id={plan_id}"`,
  and `:192-195` is the bare `effort resolve-target --phase phase-6-finalize` that precedes it.
  `ref-workflow-architecture/standards/dispatch-logging.md:44`: "The caller's only obligation is to
  pass the dispatch context to the resolve it already performs; it MUST NOT also hand-write a
  separate `manage-logging work "[DISPATCH]"` line (that reintroduces the per-role blind spot and
  double-emits)." `phase-6-finalize/SKILL.md:629` repeats the prohibition.
- **Why it matters:** the dispatch has an observable line but **no** decision-log resolve record, so
  `check-dispatch-audit.py::evaluate_shape_violation` cannot pair it (its left-hand side is Surface
  B), and the line is the per-role hand-written shape D2 removed from every other finalize site. It
  also falsifies the comment at `check-dispatch-audit.py:91-95`, which asserts that every finalize
  `[DISPATCH]` line comes from the seam.
- **Action:** convert `:194` to the seam form (`--workflow plan-marshall:phase-6-finalize/workflow/pre-submission-self-review.md --plan-id {plan_id} --caller plan-marshall:phase-6-finalize`) and delete the `:198-205` emit block, replacing it with the "the same seam call has already written the line" sentence used at `SKILL.md:627`. Leave the `:168` inline-gate instruction ("do NOT emit a `[DISPATCH]` log line") intact — it stays correct once the emission rides the resolve, since the inline branch performs no resolve.
- **Done when:** the resolve at `:194` carries `--workflow`/`--plan-id`/`--caller`, and
  `grep -n -- '--message "\[DISPATCH\]' pre-submission-self-review.md` returns nothing. (The
  skill-wide condition — no such occurrence anywhere under `skills/phase-6-finalize/` — is only
  reachable once G3 and G4 also land, since `lessons-capture.md:66` and `adr-propose.md:51` carry the
  other two; do not treat this entry as blocked on them.)
- **Effort:** S
- **Risk if fixed:** the emitted `role=` field changes from the hand-written literal `default` to the seam's resolved role key (`phase-6-finalize` when no `--role` is passed); any consumer matching on `role=default` for this step would need updating.

## G3 — Correct the false dispatcher claim in `lessons-capture.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md:57`, `:59-67`
- **Evidence:** `:57` — "The dispatcher emits the standardized `[DISPATCH]` work-log line **at the
  call site**"; `:59` — heading "`[DISPATCH]` log line (emitted by the dispatcher)"; `:61` — "The
  phase-6-finalize SKILL.md dispatcher emits the line below immediately before invoking this
  workflow", followed at `:64-66` by a full `manage-logging work "[DISPATCH]" …` command. After D2
  the dispatcher does no such thing: `SKILL.md:629` says "Do NOT hand-write a separate `[DISPATCH]`
  line". This is the same falsity class the run corrected in `dispatch-inline-split.md:15` (F4) and
  `dispatch-walkthrough.md` (F6) and missed here.
- **Why it matters:** shipped documentation that describes a removed mechanism; anyone reconciling
  the dispatcher against this doc — or restoring the block "to match the doc" — reintroduces the
  double-emit the seam was built to prevent.
- **Action:** delete the `[DISPATCH]`-log-line section and rewrite the `:57` sentence to say the
  emission rides the dispatcher's `effort resolve-target … --workflow` seam call, per firing, citing
  `dispatch-logging.md` § Emission contract.
- **Done when:** `grep -n '\[DISPATCH\]' lessons-capture.md` returns only seam-descriptive prose, no
  `manage-logging work` command.
- **Effort:** S
- **Risk if fixed:** none beyond doc churn; no test reads this section.

## G4 — Correct the false dispatcher claim in `adr-propose.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/adr-propose.md:42`, `:44-52`
- **Evidence:** identical shape to G3 — `:42` "The dispatcher emits the standardized `[DISPATCH]`
  work-log line at the call site"; `:44` heading "`[DISPATCH]` log line (emitted by the
  dispatcher)"; `:49-51` the hand-written `manage-logging work` command with
  `role=post-run-review`. Contradicted by `SKILL.md:629` and `dispatch-logging.md:44`.
- **Why it matters:** same as G3; filed separately because it is a second instance in a second file
  and each must be edited independently.
- **Action:** same remedy as G3.
- **Done when:** `grep -n '\[DISPATCH\]' adr-propose.md` returns only seam-descriptive prose.
- **Effort:** S
- **Risk if fixed:** none beyond doc churn.

## G5 — Widen the seam-pairing detector from one SKILL.md section to the whole finalize skill

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py:256-281` (`_dispatch_branch_scoped_skill_text`), `:659-677` (`test_every_task_spawn_is_preceded_by_a_seam_resolve`) and `:680-697` (`test_no_hand_written_dispatch_emit_survives`)
- **Evidence:** the sweep reads `_SKILL_DOC` only (`:85`) and blanks every line outside
  `### Step 3: Execute Step Pipeline`. Consequently G1's unpaired spawn
  (`finalize-step-simplify.md:127`) and G2's hand-written emit
  (`pre-submission-self-review.md:204`) are invisible to it — confirmed twice independently by
  mutating `SKILL.md:1015` (dropping the `--workflow/--plan-id/--caller` continuation), which turned
  `test_every_task_spawn_is_preceded_by_a_seam_resolve` red naming `line 1031`, while the same suite
  stayed green with the two real out-of-section violations present. The detectors are alive; their
  *population* is the defect.
- **Why it matters:** the plan's D2 asks for the dispatch count to equal the spawn count for the
  phase; a detector scoped to one section of one file can only ever certify that one section, and it
  is the only guard the run left behind (the test its report names is vacuous — see G7).
- **Action:** extend the (e) population to every `.md` under
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` (SKILL.md § Step 3 plus `workflow/`
  and `standards/`), keeping the existing per-file section scoping for SKILL.md to avoid the
  `## Related`-table false positive the current comment documents, and keeping both mutation guards.
- **Done when:** with G1/G2 unfixed the widened check fails naming both sites; with them fixed it
  passes; the pre-fix mutation guards still fire.
- **Effort:** M
- **Risk if fixed:** prose in step docs that mentions `Task:` illustratively could trip the sweep —
  the lookback-window heuristic needs a negative control per newly-covered file.

## G6 — Fuse the `[STEP] … Executing step:` start marker, or retire the pair claim

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:753-754` (item 2)
- **Evidence:** item 2 is still `manage-logging … --message "[STEP] (plan-marshall:phase-6-finalize)
  Executing step: {step_ref}"` — a prose instruction. D3's *Done when* reads "markers are emitted by
  the shared path, and a step that completes without any prose instruction still produces **its
  pair**"; only the completion half rides a write. The run recorded this as residue with the
  argument that item 2 is loop-driven, but "inside the loop" is the same voluntary-emission property
  the plan rejected for the completion line ("a prose instruction to log … can only ever drift
  toward silence").
- **Why it matters:** the start/complete pairing remains convention rather than contract, so a
  missing start line is still indistinguishable from a step that never ran — the original defect,
  half-closed.
- **Action:** either emit the start marker from the shared path (e.g. a `mark-step-start` handshake,
  or an emission from the dispatcher's step-record write), phase-scoped exactly as
  `_emit_completion_marker` is; or, if the symmetric fusion is deliberately declined, record that
  decision in `SKILL.md` item 2 and in `manage-status/SKILL.md` § "Fused completion emission" so the
  asymmetry is documented rather than residual.
- **Done when:** either a test analogous to `test_mark_step_completion_emission.py` pins a start
  line produced without any prose instruction, or the declined-symmetry rationale is stated in both
  documents and a test pins that item 2 is the sole start emitter.
- **Effort:** M
- **Risk if fixed:** the start marker's population would change for consumers that count
  `[STEP] … Executing step:` lines; `check-dispatch-audit.py` does not read them today, but an
  archived-corpus comparison would straddle the change point.

## G7 — Replace or delete the vacuous `test_finalize_dispatch_emits_one_line_per_spawn`

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-config/test_dispatch_seam_emission.py:144-173` (the test),
  `:135-141` and `:167-168` (the in-tree comments that misdescribe it)
- **Evidence:** the test drives `manage-config effort resolve-target` directly with `--workflow`,
  three times, and asserts three `[DISPATCH]` lines. It reads no finalize document. **Mutation
  proof, re-run independently:** after removing `--workflow/--plan-id/--caller` from
  `phase-6-finalize/SKILL.md:1015`, all **9** tests in this file passed while
  `test_dispatch_roster_closure.py::test_every_task_spawn_is_preceded_by_a_seam_resolve` failed with
  `["line 1031: 'Task: plan-marshall:{target}'"]`. It is a re-parameterisation of
  `test_role_fired_n_times_produces_n_records` (`:124-132`, already green before this plan — the
  seam landed in #1200) with `--phase phase-6-finalize` and a different `--caller` literal; its one
  extra assertion (the line starts with `[DISPATCH] ({caller})`) is already covered generically at
  `:218` in `test_dispatch_line_fields_match_the_resolved_envelope`.
- **Why it matters:** the false attribution is **in the shipped test tree**, not only in the run
  report. The comment at `:139-140` claims the test "pins the N>1 per-spawn property specifically for
  the finalize dispatch path", and the inline comment at `:167-168` claims three lines is "the
  property that fails against the pre-migration finalize emission" — mutation shows it does not fail
  against that state. A maintainer reading the file believes a load-bearing regression guard exists
  where none does; that is what lifts this above a report-only stale claim. (The property itself *is*
  guarded — by roster-closure check (e) — so nothing is unprotected today.)
- **Action:** delete the test and point the D2 verification at the roster-closure (e) checks, or
  rewrite it so its subject is the finalize document (e.g. assert that every finalize resolve block
  in `SKILL.md` § Step 3 carries the three seam flags — which is G5's remit, in which case deletion
  is the right move to avoid two names for one property).
- **Done when:** no test in the tree claims to verify the finalize per-spawn property while passing
  against a document mutation that removes `--workflow` from a finalize resolve site.
- **Effort:** S
- **Risk if fixed:** the seam's per-firing property must remain covered by
  `test_role_fired_n_times_produces_n_records`; do not delete both.

## G8 — Decide and pin the fused emission's behaviour for `loop_back`

- **Kind:** bug
- **Severity:** high
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py:182-216` (`_emit_completion_marker`), guard at `:209`, called at `:420` and `:478`
- **Evidence — executed, not inferred:** neither call site nor the function inspects `outcome`; the
  only guard is `if suppress or phase != _COMPLETION_MARKER_PHASE` (`:209`). Driving
  `cmd_mark_step_done` with `phase='6-finalize'`, `outcome='loop_back'`,
  `loop_back_target='5-execute'` and reading the work log back returns exactly
  `['[STEP] (plan-marshall:phase-6-finalize) Completed step: step-lb']`. `phase-6-finalize/SKILL.md:1100`
  calls a loop-back "a PRODUCTIVE non-completion"; `SKILL.md:1297` states the governing principle —
  "the item-7a `defer` branch records nothing (the step did not settle, so it owes no completion)";
  `manage-status/SKILL.md:374` describes the emission as riding "the terminal write". The test
  suite's own docstring (`test_mark_step_completion_emission.py:14-16`) enumerates the emitting
  outcomes as "done / skipped / failed" — `loop_back` is neither documented nor tested.
- **Why it matters:** the operational log asserts a completion for a step the dispatcher is about to
  re-fire (`SKILL.md:722` — a `loop_back` record is read back as "RE-FIRE (treat as no record)"), and
  the step emits a second line when it finally settles. `check-dispatch-audit.py:521` counts every
  such line into `completion_count`; `:436` divides `dispatch_line_count / completion_count` and
  `:441` downgrades the audit's own confidence to `low` when that ratio falls under
  `_SPARSE_RATIO = 0.5` (`:132`). A step that loops back once moves from 2/1 to 2/2, so the extra
  line pushes the ratio *down*, toward a spurious `low`-confidence verdict.
- **Severity note (why high, not medium):** the entry offers two remedies, but *both* concede the
  shipped text is wrong — (a) suppresses the line, (b) requires renaming/qualifying it. There is no
  reading under which "Completed step: X" is a true statement about a step that did not settle, so
  this is shipped behaviour that is wrong and that feeds a measurement, not merely an undecided one.
- **Action:** pick one and make code, both SKILL.md sections and a test agree: (a) suppress the
  emission for `outcome == 'loop_back'` (matching "settled" semantics and the `defer` precedent), or
  (b) keep it per firing and rename/qualify the line and the `completion_count` documentation so a
  loop-back firing is legible as such.
- **Done when:** `test_mark_step_completion_emission.py` carries a `loop_back` case asserting the
  chosen behaviour, and `manage-status/SKILL.md` § "Fused completion emission" plus
  `phase-6-finalize/SKILL.md` item 7 state the same rule.
- **Effort:** S
- **Risk if fixed:** choosing (a) lowers `completion_count` for looped runs, which shifts the audit's
  `dispatch_line_count / completion_count` ratio upward — the `_SPARSE_RATIO` threshold should be
  re-read against a real archived corpus before the change lands.

## G9 — Make an unregistered self-classifying step doc a finding, not an assertion error

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py:436-441` (`_step_doc_claims`)
- **Evidence:** the helper hard-asserts that every self-classifying discovered doc resolves to a
  registered key (`f'{path} declares frontmatter name {name!r}, which resolves to no registered
  finalize-step key'`). I measured the derived population: `find_implementors` returns **26** docs
  while `.plan/marshal.json` registers **25** finalize steps — `default:emit-landing` is discovered
  but unregistered. It does not self-classify today (`emit-landing.md:47` says "This step is
  **non-fatal**", which the `_SELF_CLASSIFICATION` regex correctly ignores), so the assert is
  dormant.
- **Why it matters:** the moment that doc gains a `This step is **inline**` sentence, the suite fails
  with a message about frontmatter resolution rather than reporting the real state (a step doc that
  classifies itself while the registry does not know it). The failure is loud but misattributed, and
  it fires on a doc-only edit.
- **Action:** downgrade the unregistered case from `assert` to a collected finding — skip the
  roster comparison for that doc and report "self-classifies but is not registered" through the same
  mismatch list, so the message names the actual condition.
- **Done when:** a synthetic self-classifying, unregistered implementor produces a mismatch message
  naming registry absence, and the registered-doc comparison behaviour is unchanged.
- **Effort:** S
- **Risk if fixed:** if the downgrade is written as a silent skip rather than a reported finding, the
  check loses a real drift signal — the report path is the load-bearing half.

## G10 — Correct the run report's "all four finalize sites" and N>1 claims

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/180-finalize-dispatch-manifest-observability/report-01.md` § "D2" (the "Migrated all four finalize `effort resolve-target` sites" sentence and the "Verification (N>1)" sentence)
- **Evidence:** six finalize dispatch sites exist under `skills/phase-6-finalize/` — the four
  migrated ones (`SKILL.md:622/951/1015/1498`) plus `finalize-step-simplify.md:113` and
  `pre-submission-self-review.md:194`, both still bare (G1, G2). And
  `test_finalize_dispatch_emits_one_line_per_spawn` passes against the D2 defect (G7, mutation-proved).
- **Why it matters:** the report is the record a retrospective and any follow-up plan reads; as
  written it certifies a completed migration and a per-spawn regression test, so the two live
  pre-seam sites read as already handled.
- **Action:** amend the D2 section to say "four of the six finalize dispatch sites (SKILL.md);
  `finalize-step-simplify.md` and `pre-submission-self-review.md` were not migrated", and state that
  the per-spawn property is guarded by roster-closure check (e) rather than by the named seam test.
- **Done when:** the report's D2 section names the unmigrated sites and attributes the N>1 guard to
  check (e); this file's G1/G2/G7 cross-reference it.
- **Effort:** S
- **Risk if fixed:** none — the report is a dated record; amending it does not change behaviour.
