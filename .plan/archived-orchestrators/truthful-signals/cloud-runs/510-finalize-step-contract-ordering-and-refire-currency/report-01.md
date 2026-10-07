# Run report — 510-finalize-step-contract-ordering-and-refire-currency (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/step-contract-ordering-refire-cjlzup`    **PR:** [#1309](https://github.com/cuioss/plan-marshall/pull/1309)    **Outcome:** merged 2026-08-20T08:26:45Z via the merge queue, head `f07f0ea`

> **Run status:** complete. Merged; §§ Reviewer participation, Cost, Contract check, What have we
> learned and Residue are filled from what happened, and the one contract deviation (a commit shipped
> without a bot review, operator-directed) is recorded in § Contract check rather than smoothed over.
>
> **Verification loop exit:** `budget-exhausted` — five rounds run, the full budget. Round 5 returned
> five findings plus three minor, all condition A and all counting prose; every one is fixed above
> except **T8**, characterised in § Residue, and commit `c92dd11`'s message (**S8**), characterised
> there too. Not `verifier-clear`: five consecutive rounds each found real defects, four of them in the
> text written to fix the round before, so the honest reading is that a sixth round would find more —
> not that the tree is clean. What the rounds did establish, by re-derivation and replay rather than
> assertion, is that **the substrate work holds**: every population, every guard, every replayed
> mutation and the whole-tree gate reproduce exactly. The residual defect class is the report's own
> counting prose, which is now the only place findings have come from for two rounds.

## Skills loaded

Loaded by path from the bundle source (the `plan-marshall` plugin is not installed in this session,
so `Skill: {bundle}:{skill}` notation was not used):

| Skill | Path | Why |
|---|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` | always |
| `pm-plugin-development:plugin-script-architecture` | `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md` | always |
| `plan-marshall:ref-workflow-architecture` | `.../ref-workflow-architecture/SKILL.md` | workflow docs, dispatch topology (D5) |
| `plan-marshall:persona-implementer` | `.../persona-implementer/SKILL.md` | production code (D2.2, D4.3, D8) |
| `pm-dev-python:python-core` | `marketplace/bundles/pm-dev-python/skills/python-core/SKILL.md` | Python production code |
| `pm-dev-python:pytest-testing` | `marketplace/bundles/pm-dev-python/skills/pytest-testing/SKILL.md` | Python tests (D2, D3) |
| `pm-plugin-development:plugin-architecture` | `.../plugin-architecture/SKILL.md` | `SKILL.md` / bundle structure |
| `pm-documents:ref-asciidoc` | `marketplace/bundles/pm-documents/skills/ref-asciidoc/SKILL.md` | `.adoc` documentation (D4) |

Every skill named was obtainable by the bundle path; none was unavailable by both routes.

## Populations (D1)

All four populations were **re-derived during this run**. No number below is carried over from the
plan file. Derivation scripts were written to the session temp dir (never the repository).

⚠ **Every table and count in this section describes the tree D1 ran against — `origin/main` plus D1's
own commit — not the tree this branch ships.** That is what D1 is for: the populations are the baseline
the later deliverables were measured and built against, and plan Verification §3 asks specifically for
the asserted absences to be re-checked *before* D7.1 and D2.1 implement against them. But nothing here
said so, and three deliverables then changed the substrate underneath it: **D7.1 added `reads:` to five
steps**, **D7.3 added `records_facts` to `create-pr`, `emit-landing` and `branch-cleanup`**, and **D5
drove population (b) to zero**. Read as a description of the shipped tree — which the unqualified
heading invited — eight cells of table (a), the `reads:` absence bullet, and the whole of population (b)
are false. Round 3 raised this; the numbers are correct as a baseline and are kept, with the
post-implementation state stated beside each. Round 4 then found the *fix* had itself under-counted —
it named the two `records_facts` sites round 3 listed and missed `branch-cleanup`, whose `merge_state`
addition this report's own finding F1a already recorded. Fixing at the sites a round names rather than
across the class is the recurrence pattern this run hit three separate times; the delta table below is
now derived from the frontmatter rather than transcribed from a finding.

**The shipped-tree state is the authority for what the contract declares today**; a `### (x)` heading
below is the D1 baseline unless its § Post-implementation note says otherwise.

### (a) The `ext-point-finalize-step` implementor set — **26 implementors**

Derived from the `implements:` frontmatter across the four surfaces
`extension_discovery.find_implementors` scans (phase-6-finalize `workflow/` then `standards/` with
`workflow/` precedence on a bare-name collision; every bundle's `skills/*/SKILL.md` except
`phase-6-finalize`; project-local `.claude/skills/finalize-step-*/SKILL.md`). The stock
`_IMPLEMENTOR_FRONTMATTER_KEYS` tuple does **not** carry the eight keys D1 asks for, so the
derivation re-implements the same scan surfaces with the wider key set:

```bash
python3 $TMPDIR/derive_pop_a.py .     # mirrors find_implementors' four surfaces
```

| order | step id | source | `mutates_source` | `head_dependent` | `post_run_review` | `records_facts` | `requires_prompt_fields` | `verdict_inputs` | `reads` | `destroys` |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | `default:finalize-step-sync-baseline` | built-in | true | — | — | `action`, `upstream_commit_count`, `work_performed` | — | — | — | — |
| 4 | `project:finalize-step-lessons-housekeeping` | project | true | true | — | — | — | — | — | — |
| 5 | `default:pre-push-quality-gate` | built-in | false | true | — | — | — | — | — | — |
| 6 | `project:finalize-step-plugin-doctor` | project | — | true | — | — | — | — | — | — |
| 7 | `default:pre-submission-self-review` | built-in | false | true | — | — | `candidates` | — | — | — |
| 8 | `default:finalize-step-simplify` | built-in | true | true | — | — | — | — | — | — |
| 9 | `default:finalize-step-security-audit` | built-in | true | true | — | — | — | — | — | — |
| 10 | `default:architecture-refresh` | built-in | — | — | — | — | — | — | — | — |
| 11 | `default:push` | built-in | false | — | — | — | — | — | — | — |
| 20 | `default:create-pr` | built-in | false | — | — | — | — | — | — | — |
| 21 | `project:finalize-step-era-stamp-fill` | project | true | true | — | — | — | 3 globs | — | — |
| 22 | `default:ci-verify` | built-in | false | true | — | — | — | — | — | — |
| 30 | `plan-marshall:automatic-review` | built-in | true | true | — | — | — | — | — | — |
| 40 | `default:sonar-roundtrip` | built-in | true | true | — | `count_status`, `new_code_issue_count`, `issues_fetched`, `work_performed` | — | — | — | — |
| 62 | `default:adr-propose` | built-in | — | — | — | — | — | — | — | — |
| 70 | `default:branch-cleanup` | built-in | false | — | — | `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` | — | — | — | `worktree` |
| 81 | `project:finalize-step-deploy-target` | project | false | — | — | — | — | — | — | — |
| 85 | `project:finalize-step-sync-plugin-cache` | project | false | — | — | — | — | — | — | — |
| 990 | `project:finalize-step-review-retrospective` | project | false | true | true | — | — | — | — | — |
| 991 | `default:lessons-capture` | built-in | false | — | true | — | — | — | — | — |
| 992 | `default:finalize-step-preference-emitter` | built-in | false | — | true | — | — | — | — | — |
| 995 | `plan-marshall:plan-retrospective` | bundle-optional | false | — | true | — | — | — | — | — |
| 998 | `default:record-metrics` | built-in | false | — | true | `total_tokens`, `total_wall_seconds`, `any_phase_missing_end_time` | — | — | — | — |
| 999 | `default:finalize-step-print-phase-breakdown` | built-in | false | — | true | — | — | — | — | — |
| 1000 | `default:emit-landing` | built-in | false | — | true | — | — | — | — | — |
| 1100 | `default:archive-plan` | built-in | false | — | — | — | — | — | — | `plan-directory` |

A dash means the key is **absent** from the frontmatter, not that it is declared false.

Facts this run depends on, read off the table:

- **`reads:` is declared by zero implementors** — D7.1's asserted absence, re-verified **at the D1
  baseline**. This is the absence D7.1 then closed, so it is false of the shipped tree; see
  § Post-implementation below.
- **`destroys:` is declared by exactly two** — `default:branch-cleanup` → `[worktree]`,
  `default:archive-plan` → `[plan-directory]` — D2.5's two anchors, re-verified as present.
- **`create-pr` (20) → `era-stamp-fill` (21) → `ci-verify` (22)** — D2.1's adjacency holds today.
- **`mutates_source: true` AND `order > default:pre-push-quality-gate.order` (5)** resolves to
  `default:finalize-step-simplify` (8), `default:finalize-step-security-audit` (9),
  `project:finalize-step-era-stamp-fill` (21), `plan-marshall:automatic-review` (30),
  `default:sonar-roundtrip` (40) — D8 / 230-G1's correct membership.
- `default:lessons-capture` declares `mutates_source: false` — the wrong example 230/G1 names.

#### Post-implementation — where the shipped tree differs from the baseline above

Re-derived at HEAD with the same scan, after D7 landed. **Eight cells** of the table and one bullet
above are superseded; every other row still holds. The count is stated from the rows below rather than
carried in prose — round 3 reported six, round 4 found the table under it already had seven and that an
eighth was missing entirely.

```bash
grep -rn "^reads:" \
  marketplace/bundles/plan-marshall/skills/phase-6-finalize/{workflow,standards}/*.md \
  .claude/skills/finalize-step-*/SKILL.md
```

| step id (order) | key | baseline says | shipped tree declares | added by |
|---|---|---|---|---|
| `default:finalize-step-sync-baseline` (3) | `reads` | — | `worktree` | D7.1 |
| `default:pre-push-quality-gate` (5) | `reads` | — | `worktree` | D7.1 |
| `project:finalize-step-plugin-doctor` (6) | `reads` | — | `worktree` | D7.1 |
| `default:create-pr` (20) | `records_facts` | — | `pr_number` | D7.3 |
| `default:branch-cleanup` (70) | `records_facts` | `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` | the same four **+ `merge_state`** | D7.3 |
| `default:finalize-step-print-phase-breakdown` (999) | `reads` | — | `metrics` | D7.1 |
| `default:emit-landing` (1000) | `records_facts` | — | `work_performed` | D7.3 |
| `default:emit-landing` (1000) | `reads` | — | `metrics` | D7.1 |

So **`reads:` is declared by five implementors in the shipped tree**, not zero. Two independent
surfaces in this branch already state the post-implementation set and agree with it: the reader list in
`finalize-step-order-bands.md`, and the read-before-destroy ledger row below — whose quoted failure
(`default:pre-push-quality-gate (order 75) reads 'worktree'`) is only producible *because* that step
declares the key. The baseline bullet and the two `records_facts` cells also contradict this report's
own finding **F1b**, which recorded `create-pr`'s new declaration as fixed.

### (b) The hand-written `[DISPATCH]` emission population — **11 blocks in 7 files at the D1 baseline; 0 in the shipped tree**

```bash
python3 $TMPDIR/derive_pop_b.py .     # manage-logging `work` call carrying [DISPATCH]
```

Both D1 exclusions applied: `ref-workflow-architecture/standards/dispatch-logging.md` (which quotes
the shape in order to forbid it) is excluded by construction, and the dispatch-site / doc-echo split
is decided by whether the file carries a **fenced, executable** `effort resolve-target` command
block, not by the string appearing in prose.

**Dispatch sites — 9 blocks in 5 files:**

| File | Blocks (line) |
|---|---|
| `plan-marshall/workflow/planning-outline.md` | 110, 144, 429, 482 |
| `plan-marshall/workflow/planning.md` | 284, 324 |
| `phase-3-outline/standards/outline-workflow-detail.md` | 215 |
| `phase-6-finalize/workflow/pre-submission-self-review.md` | 202 |
| `workflow-pr-doctor/SKILL.md` | 36 |

**Doc-echoes — 2 blocks in 2 files:** `phase-6-finalize/workflow/lessons-capture.md` (64),
`phase-6-finalize/workflow/adr-propose.md` (49). Neither carries an `effort resolve-target` call,
confirming 280's adversarial-review correction that the "add `--workflow` to the resolve" instruction
is uncarryable for them.

#### Post-implementation — the population is now empty, and the line numbers above are stale

D5 is the deliverable that consumes this population, and closing it drove the count to **0**: every
block above was migrated to the `[DISPATCH]` seam, where `effort resolve-target
--workflow/--plan-id/--caller` emits the work-log line and its paired decision-log record itself. Re-run
at HEAD, the derivation returns zero — the only `manage-logging work` calls carrying `[DISPATCH]`
anywhere in the tree are the three prose lines in `dispatch-logging.md`, which quote the shape in order
to forbid it and are excluded by construction.

Because the migration rewrote those files, **the line numbers in the two tables above no longer locate
the blocks they name** — `planning-outline.md:110` and `:144` are now blank lines, `:429` is a
`name:` key, `planning.md:284` and `:324` are `[ATTEMPT]` lines, `workflow-pr-doctor/SKILL.md:36` is
blank. They are retained as the D1 baseline record — the census D5 was measured against — and are not
navigational aids to the shipped tree. § Deliverables' D5 row states the post-fix count; this heading
now states it too, rather than leaving the two in silent disagreement.

### (c) The per-implementor input-table `Required` row population — **1 row outside the contract**

```bash
python3 $TMPDIR/derive_pop_c.py . pop_a.json   # header-parsed Required column, never a fixed index
```

Across the 26 implementor docs, tables carrying a `Required` column yield 9 rows, of which **3** sit
in a table whose first header cell is `Prompt-body field` (the repository-wide convention header —
`grep -rln "^| Prompt-body field" marketplace/ .claude/ doc/user doc/developer` returns **10** docs
that use it verbatim) and **6** sit in `plan-retrospective`'s CLI `| Parameter |
Required |` table, which is not a prompt-body-field table. Scoped to prompt-body-field tables, the
rows whose key falls outside the generic contract set
(`name`/`plan_id`/`skills`/`workflow`/`instructions`/`WORKTREE`) are exactly one:

| Step | Key | Required |
|---|---|---|
| `default:pre-submission-self-review` | `candidates` | Yes |

**Sizing fact for D3:** only **2 of the 26** implementors carry a `prompt: |` block of their own
(`default:pre-submission-self-review`, `default:finalize-step-simplify`) — so **24 of 26** have none,
and the `∀`-direction of `test_step_prompt_fields_contract.py` is vacuous for those 24.

### (d) The `from _dispatch_roster import` importer set — **9 modules**

```bash
grep -rn "^from _dispatch_roster import" test/ | sed 's/:.*//' | sort -u
```

Six under `test/plan-marshall/phase-6-finalize/` and **three outside it**:
`test/plan-marshall/manage-lessons/test_lesson_store_resolution_population.py`,
`test/plan-marshall/phase-5-execute/test_execute_phase_markers.py`,
`test/plan-marshall/ref-workflow-architecture/test_citations_only_conformance.py`.

**040/G3 closed:** `040-inert-thinking-directives-in-dispatched-docs/report-01.md` § D2 asserted the
module's "sole consumers are the phase-6-finalize tests". That clause is replaced with the derived
importer set. The paragraph's conclusion — that the module is a Markdown-section/roster-row parser,
not the execution-context workflow roster — is independently correct and is left unchanged.

**HALT gate:** (a) and (c) were both derivable, so the plan proceeds.

## Deliverables

| D | Commit | State |
|---|---|---|
| D1 — derive the four populations, close 040/G3 | `28669af` | done — § Populations above |
| D2 — six guards seen RED | `b935f14` | done — red-first ledger below |
| D3 — bind prompt-body carriage to its declaration surface | `2217e8d` | done |
| D4 — the finalize configuration surface names only keys that resolve | `2217e8d` | done |
| D5 — hand-written `[DISPATCH]` emissions to zero | `17d1a87` | done — population (b) re-derived to 0 |
| D6 — the `baseline-reconcile` return contract | `9595e5c` | done |
| D7 — declare the advertised finalize-step facts | `974fecd` | done |
| D8 — thirteen statements made true against their substrate | this run's final deliverable commit | done — per-gap checks below |

### The red-first ledger (D2, D3's declaration guard, and A9's carve-out)

One row per mutation. Every mutation was applied through a harness that snapshots the target's BYTES
to an agent-private scratch path and restores them in a `finally` — never `git checkout`/`restore`,
which would rewrite the file from the index and discard this run's unstaged work. `git status` was
re-checked after each sweep; every target came back clean.

Each **Failure message** cell is the assertion text the mutated run actually emitted, captured from the
harness output. Round 3 caught this row set quoting a message read off the *test source* instead — for a
mutation under which that assertion was never reached, because an earlier one in the same test fired
first. Quoting a plausible message rather than the observed one is the defect class this plan exists to
close, so the harness now prints the emitted `AssertionError` and the cells are filled from it.

| Gap | File mutated | Mutation | Test that failed | Failure message (abridged) | Restore |
|---|---|---|---|---|---|
| 230/G2 | `.claude/skills/finalize-step-era-stamp-fill/SKILL.md` | `order: 21` → `23` (frontmatter-anchored) | `test_finalize_edge_ordering.py::test_era_stamp_fill_runs_between_pr_creation_and_ci_verification` | `project:finalize-step-era-stamp-fill (order 23) must run strictly after default:create-pr (order 20) … and strictly before default:ci-verify (order 22)` / `assert 23 < 22` | `git diff --quiet` clean |
| 310/G4 | `workflow-integration-git/scripts/git-workflow.py` | `push_barrier_action` also returns `re-fire` for `remote_absent_landed` | `test_git_workflow.py::TestBranchSyncState::test_verdict_token_drives_refire_skip_mapping` | `{'remote_absent_landed': 're-fire'} != {'remote_absent_landed': 'skip'}` | clean |
| 440/G6 (a) | `.claude/skills/finalize-step-plugin-doctor/SKILL.md` | renamed ONLY the `###` heading, leaving the cross-reference | `test_verdict_currency.py::test_every_tabled_refusal_carries_its_section` | `project:finalize-step-plugin-doctor is tabled as a recorded refusal but its own doc carries no "Verdict-input surface — deliberately undeclared" section` | clean |
| 440/G6 (b) | `phase-6-finalize/standards/pre-push-quality-gate.md` | renamed ONLY the `##` heading, leaving the cross-reference | same test | same shape, naming `default:pre-push-quality-gate` | clean |
| 440/G1 | `.claude/skills/finalize-step-era-stamp-fill/SKILL.md` | `era_stamp_fill.py` → `era_stamp_filler.py` in `verdict_inputs` | `test_verdict_currency.py::test_every_wildcard_free_declared_glob_names_a_tracked_path` | `project:finalize-step-era-stamp-fill declares '….../era_stamp_filler.py' — does not exist` | clean |
| 300/G1 | `phase-6-finalize/standards/archive-plan.md` | deleted the `destroys:` block | `test_finalize_orchestration_routing.py::TestCanonicalDestroysDeclarationsExist::test_each_canonical_anchor_declares_its_artifact` | `default:archive-plan declares no destroys: frontmatter … Removing it leaves both standards describing a capability with no instance` | clean |
| 302/G8 | `plan-orchestrator/scripts/_orchestrator_inbox.py` | removed `merge_state` from `LANDING_REQUIRED_KEYS` | BOTH `test_payload_spec_table_names_exactly_the_required_keys` AND `test_emit_landing_enumeration_names_exactly_the_required_keys` | `Extra items in the left set: 'merge_state'` on each | clean |
| D3 declaration guard (a) | `phase-6-finalize/workflow/pre-submission-self-review.md` | added a `Required: Yes` non-exempt `ghost_field` input-table row with no declaration | `test_step_prompt_fields_contract.py::test_input_table_required_keys_equal_the_declaration` (and the parser anchor test) | `declared=['candidates'] table=['candidates', 'ghost_field']` | clean |
| D3 declaration guard (b) | `phase-6-finalize/workflow/create-pr.md` | added `requires_prompt_fields: [synthetic_field]` to a step with NO own `prompt:` block | ONLY `test_input_table_required_keys_equal_the_declaration` — the ∃-direction and the block-presence guard both PASSED | `default:create-pr: declared=['synthetic_field'] table=[]` | clean |
| D7 read-before-destroy gate | `phase-6-finalize/standards/pre-push-quality-gate.md` | `order: 5` → `75`, past `branch-cleanup`'s `destroys: [worktree]` (70) | `test_finalize_edge_ordering.py::test_every_reader_runs_before_the_step_that_destroys_what_it_reads` | `default:pre-push-quality-gate (order 75) reads 'worktree', which default:branch-cleanup (order 70) destroys` | clean |
| D8 / 160-G2 substrate guard | `script-shared/scripts/build/_gate_coverage.py` | dropped `targets, build.py` from the `spdx-paths` parity note | `test_gate_coverage_parity_substrate.py::test_spdx_paths_note_matches_the_gate_it_describes` | missing `'build.py'`, `'targets'` | clean |
| A9 carve-out (a) | `test/plan-marshall/test_lane_refactor_cleanup_sweep.py` | widened the carve-out from run-report files to the whole `doc/plans/` tree | `test_the_rest_of_doc_plans_is_still_swept` (and the anchor control alongside it) | `live documentation under doc/plans/ is no longer swept, so a retired token in it would go uncaught: ['doc/plans/README.md', 'doc/plans/_template/plan.md']` | bytes identical |
| A9 carve-out (b) | same | dropped the `doc/plans` ancestor test, matching `report-NN.md` anywhere in the tree | `test_the_exclusion_is_anchored_to_doc_plans_and_to_the_report_name` | `assert not True` — on `_is_lane_run_report(doc/user/report-01.md)` | bytes identical |
| A9 carve-out (d) | same | carve-out swallows all of `doc/` (`return path.is_relative_to(PROJECT_ROOT / 'doc')`) | `test_the_rest_of_doc_is_still_swept` — **the row round 4 found missing**; the other three A9 mutations in this table leave this guard green, so its red was unrecorded and "each seen RED" was false for it. Also fails `test_the_rest_of_doc_plans_is_still_swept` and `test_the_exclusion_is_anchored_…` | `doc/user and doc/developer must both remain on the walk; swept top-level doc subdirectories were []` | sha256 identical |
| A9 carve-out (c) | same | defined `_is_lane_run_report` but removed its call from `_iter_text_files`, leaving it unconsulted | `test_the_run_report_exclusion_is_honoured_by_the_walk` — **and** `test_no_ceremony_policy_json_key_or_dotted_paths`, the original failure returning | `109 lane run report(s) reached the sweep despite the exclusion` / `Orphaned reference to retired token 'ceremony_policy' (4 hit(s))` | bytes identical |

**D3's second Done-when check, and where it disagrees with the plan.** The plan's stated check is that
adding `requires_prompt_fields` to a generic-template-dispatched step with no own `prompt:` block
*"leaves the suite green"*. Taken literally that is unsatisfiable once **call two** lands, because the
new input-table direction asserts declaration ≡ table for every step, and a declaration with no table
row is exactly a divergence. The two plan calls are in tension, so the run performed BOTH halves rather
than picking one:

- **(a)** declaration alone → the ONLY failure is the input-table direction; the ∃-direction and the
  block-presence guard pass. That is precisely what call one set out to buy — a generic-template
  declarer is no longer rejected for lacking a block.
- **(b)** declaration **plus** its matching `Required: Yes` input-table row, still with no own `prompt:`
  block → **19 passed**, suite green.

(b) is the honest form of the plan's check under call two, and it demonstrates the same property. The
deviation and its reason are recorded here rather than silently resolved either way.

### D8 — the per-gap check, one line each

| Gap | Check run | Result |
|---|---|---|
| 160/G9 | Read both link targets: `ref-workflow-architecture/standards/agents.md` states no ceiling (`grep` for `display_detail`/`80` → 0 hits); `external-step-contract.md` § "Required termination" states `≤80 characters` | repointed to the doc that states it |
| 160/G4 | Added a third `--display-detail` variant for the `whole_tree_available == false` branch; measured its expansion in Python (67 chars at `{N}`=1 digit, 68 at 2) and referenced it from branch 3 | done; Branch A's default documented as inapplicable there |
| 160/G2 | Relabelled `parity_population` as **recorded** in all four places that called it derived (module docstring, function docstring, `pre-push-quality-gate.md`, the sibling test docstring); added `test_gate_coverage_parity_substrate.py` binding the `spdx-paths` cell to `build.py`'s real SPDX scope, mutation-confirmed | done |
| 230/G1 | Replaced the hardcoded pair with the discriminator (`mutates_source: true` **and** `order > default:pre-push-quality-gate.order`); derived both operands from population (a) | done — the bullet now names no `mutates_source: false` step as a member, and no step at/below the gate |
| 300/G2 | Split the Settle band into pre-push (1–11) and post-push (12–69); re-derived occupancy from population (a): 3–11 fully occupied by nine steps, so the pre-push sub-region has **no** guaranteed insertion room | done — occupancy figures match the derivation |
| 300/G4 | Reduced the `mutates_source` obligation in the post-merge-operational and post-run-review rows to pointers at the owning contract; the Settle rewrite dropped the third | done |
| 330/G1 | Read the corrected sibling paragraph in `finalize-step-preference-emitter.md` and mirrored it — the guard's exemption is keyed on git trackedness, not the path prefix | done |
| 440/G2 | Lead sentence now defers the ACTION as well as the membership; the `differs from live HEAD` row points at Step 3's classifier; the closing summary is qualified. The `matches` and `field absent` rows left alone as the plan directs | done — no sentence in § Resumability prescribes an unconditional re-fire **for a step whose verdict can still be current**. The one row that does is `head_at_completion` **absent** (`SKILL.md:1768`, "Re-fire AND report the prior verdict UNVERIFIED") — deliberately untouched, per the plan, because a missing stamp leaves nothing to classify. The D4/440-G2 cold reader found that same sub-case unprompted |
| 440/G3 | Located both sentences at `:1100` and `:1105` and routed each by `use_merge_queue` | done — `grep -c "unconditional rebase" branch-cleanup.md` returns 0. Unscoped it returns 1, at `verdict-currency.md:57`, which discusses the `noop` discriminator rather than prescribing a rebase; the row is about `branch-cleanup.md`, so the command is stated scoped to it |
| 410/G1 | Rewrote § (e)'s closing sentence from the presence-only test to the recognized-identity form, changing nothing else in the section | done |
| 410/G4 | Scoped the `default` claim in § (d), `audit.py`'s `_UNATTRIBUTED_MODULE` comment AND its `_preference_module` docstring, and `preference-pattern-detector.md`. Verified the other producer is real and live at `lessons-capture.md:132` (*"the `default` module is the first-class home for cross-cutting"*), and left that file unchanged as the plan directs | done |
| 300/G8 | Corrected the seed annotation `# order 61` → `# order 992`, the order the step's standards doc declares (`finalize-step-preference-emitter.md:7`). No assertion and no seed position changed | done |
| 300/G9 | Rewrote the sort-rationale parenthetical to name the order the step carried **at the time of the incident** with an explicit past-tense marker, plus the order its standards doc declares today | done |

## Build gate

**Python-change verdict.** The gate fires: this branch changes Python, which is the only thing the
verdict turns on. It is true of the branch as a whole and of every commit from `b935f14` onward; the
first two commits (`a1b11b4` the plan directory, `28669af` D1's populations) touch no `*.py` at all,
which is why the per-commit gates below ran ahead of every *Python-touching* commit rather than every
commit.

The figures below are **exact between the PR's base and commit `db2f61d`** — the last commit that
changes implementation files — and stale for any other pair, so they name **both endpoints** rather
than standing bare:

```bash
# Both endpoints fixed. `db2f61d` is reachable from refs/pull/1309/head, NOT from main —
# git fetch origin refs/pull/1309/head  if this clone does not have it.
git diff --name-only 32c13fa...db2f61d -- '*.py' | wc -l   # 28  (9 production, 19 test)
git diff --name-only 32c13fa...db2f61d | wc -l             # 61
```

**Two corrections, both found after the merge and both of the kind this plan exists to catch.**

*Anchoring one endpoint was not enough.* These commands originally read
`git diff --name-only db2f61d origin/main`, which pins the left side and lets the right side move with
`main`. That was true when written and false as soon as anything else landed: run today it returns
**146 / 274**, not 28 / 61. A two-endpoint diff needs two fixed endpoints, and `origin/main` is not
one. The form above uses the PR's recorded base sha (`32c13fa`) and the three-dot merge-base
comparison, which is what the original figures were actually measuring.

*The shas are not reachable from `main`.* The merge queue **rebased** rather than creating a merge
commit, so `f07f0ea`, `db2f61d` and every other sha this report cites are absent from `main`'s
history — `git merge-base --is-ancestor db2f61d origin/main` is false. They survive on
`refs/pull/1309/head`, which is why the command block says to fetch it. The choice of a merge commit
at the merge step was made specifically to keep these citations checkable, and the queue's own merge
strategy overrode it; recording that is more useful than restating the intent.

Round 5 had flagged that the old rationale held only until the next implementation commit, and the
very next one falsified it — 27/60 became 28/61. Counting the two corrections above, **these figures
moved six times**. The lesson is not that anchoring failed but that it was applied to one side of a
two-sided measurement.

This is the third figure set recorded here, and the churn is the point rather than an embarrassment:
A7 caught the first set (19/48) stale, the re-derived set (23/56) went stale again the moment the
commit correcting it landed, and round 3 caught *that*. A diff-derived count is invalidated by the very
act of committing the correction — a regress that a bare "re-derived at HEAD" cannot escape, because
writing the number down changes the tree the number describes. Naming a commit is the exit.

**Result.** `UV_PYTHON=3.12 UV_HTTP_TIMEOUT=600 ./pw verify` — the full three-sub-step form, not the
narrower calls, so `test-compile` (mypy over the whole `test/` tree) is included. **The first run over
this tree came back RED**, and the wrapper exited 0 while doing so:

```text
1 failed, 21103 passed, 14 skipped in 343.87s (0:05:43)
verify: module-tests failed
FAILED test/plan-marshall/test_lane_refactor_cleanup_sweep.py::test_no_ceremony_policy_json_key_or_dotted_paths
```

The failure was **this report's own text**, and it had been red since the round-1 report commit
without being caught, because that commit's gate was scoped to the modules its `*.py` edits touched
and this guard is tripped by a `.md` line. `test_lane_refactor_cleanup_sweep` asserts the retired
`ceremony_policy` token appears nowhere under `marketplace/` or `doc/`; § Collateral check cited a
still-present test module whose *filename* contains that token, so naming the file reproduced it.

**The first fix was wrong, and the second whole-tree run proved it.** Judging the guard correct, this
run rewrote the citation to locate the module without spelling it, re-ran the guard alone, saw
`6 passed`, and re-ran `verify` — which came back **`1 failed, 21103 passed`** *again*, now with
**four** hits instead of one. Writing the finding up had reintroduced the token in § Build gate, in
§ Residue and in the A9 row itself. That is the decisive fact: **the guard forbids a run report from
naming the guard it tripped**, so no amount of rewording resolves it. A green single-test run is not a
green tree, and this run recorded the first as though it were the second — the same error class the
plan exists to close, committed while documenting an instance of it.

The guard was therefore **narrowed** — and the first attempt at narrowing it was itself too wide, which
round 3 caught (**R11**). The shipped carve-out excludes lane run reports only,
`doc/plans/**/report-NN.md`, on the boundary `CLAUDE.md` already draws between a dated record and
current documentation; the rest of `doc/plans/` — its README, the epic READMEs, the plan template,
every plan.md — stays on the walk. What the sweep polices is unchanged: an orphan is a live reference
in source or current documentation, not a historical record of one. Four guards hold the carve-out to
that shape, each seen RED against the defect it names — including a control that fails if it ever
widens back to the tree — see § The red-first ledger and **R11** below.

This is the second instance in this run of the failure mode the lane contract names — **the wrapper
exits 0 on a failing gate, so the verdict is only in the output.** The first was a ruff `F401` after
D4.3 removed `choices=` from `--lane`, also at exit 0, also caught by reading; its fix removed the
restatement rather than the import, so the help string now interpolates the constant. Per-commit gates
ran ahead of every `*.py`-touching commit; both defects show that a per-commit gate scoped to the
changed modules does not substitute for the whole-tree run.

**Green whole-tree result**, fourth run of this gate, over the tree carrying the carve-out and its four guards:

```text
21108 passed, 14 skipped in 338.74s (0:05:38)
coverage: COMPLETE over the dimensions below — checked over full scope:
  mypy(production) [415 files, cache disabled], ruff [marketplace/bundles, test, .claude],
  SPDX headers [marketplace/bundles, test, .claude, marketplace/targets, build.py],
  plugin-doctor [marketplace-wide], mypy(test) [780 files, cache disabled],
  module-tests [whole-tree pytest]
```

Zero `FAILED` lines, and all **three** sub-steps observed in the stream — `quality-gate` (ruff, SPDX,
plugin-doctor), `test-compile` (`mypy test`) and `module-tests` — so the green is not an early exit.
Three is the sub-step count `cmd_verify` runs; **six** is the number of *coverage dimensions* the line
above reports, and conflating the two is what this sentence did until round 3 separated them.
The count reconciles across all three runs rather than being read off on its own: 21103 passed **+ 1**
(the sweep assertion that was failing) **+ 3** (the first carve-out's guards) = **21107**, then **+ 1**
for the fourth guard R11's narrowing added = **21108**. A total that did
not reconcile would mean tests had been lost, which a rising pass count alone would hide.

The gate's own scope-limit block is worth carrying rather than eliding, because this run demonstrated
its point twice: `module-tests` "executes the tests that exist; it cannot evaluate behaviour under
inputs no test supplies", and a green here is evidence about the six dimensions listed, not whole-tree
assurance that the change is sound. Both defects this gate caught (a ruff `F401`, the sweep assertion)
were found by reading its output while the wrapper exited 0 — never by the exit code.

**Stale-base re-verification (§ Step 8 condition 2)** — recorded at the merge gate below.

## Findings

One row per instance. Source is the verification round that raised it.

### Round 1 — the pre-PR verification sub-agent

The verifier independently re-derived populations (a), (b) and (d), **executed** the resolver three
ways and the manage-config CLI, re-derived every character count and the Settle occupancy, read the
`baseline-reconcile` implementation and `_cmd_step`, ran 3246 tests, and read every new guard for
vacuity. It reported the new guards non-vacuous.

**17 rows below, under 10 F-numbers** — F1, F2, F5, F6 and F10 each cover more than one instance
(F1a/F1b, F2a/F2b, F5a/F5b/F5c, F6a/F6b, F10a/F10b/F10c), and § Findings' rule is one row per
*instance*. Commit `65669cb` counts the same set as "fourteen findings … plus three nits", which is a
third way of slicing it. The row count is the figure to trust, because it is the one the table can be
checked against:

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1a | round 1 | `ext-point-finalize-step.md` § Declared obligations — `default:branch-cleanup`'s union cell omits the `merge_state` D7.3 added | **fixed** — cell updated, consumer question added |
| F1b | round 1 | Same table has no row for `default:create-pr`, which now declares `records_facts: [pr_number]` | **fixed** — row added |
| F2a | round 1 | `ext-point-finalize-step.md:48` still says the agreement is "enforced in BOTH directions"; the same file now says three scopes | **fixed** — row states the three surfaces |
| F2b | round 1 | `phase-6-finalize/SKILL.md`'s dispatch paragraph says the guard "fails the build when a declared field is not carried" — precisely the behaviour D3.1 removed, sitting beside the template's own declared-field slot | **fixed** — rewritten to the three-surface form, naming the generic-template case as correct rather than a failure |
| F3 | round 1 | D4's new paragraph said `standard`/`full` "pin its tier". The canonical transform maps every value other than `off`/`minimal` → `auto`, so `full` does **not** force a gate in | **fixed** — the transform is stated as the canonical states it |
| F4 | round 1 | The same paragraph told the operator to run `step set --step-id pre-push-quality-gate`, which **errors** (`Step 'pre-push-quality-gate' not found`); the seeded key is `default:pre-push-quality-gate`. Verified by execution | **fixed at all three sites** — `configuration.adoc`, and the two upstream sources carrying the same unprefixed id (`manage-config/SKILL.md` twice, `manifest-schema.md`). The transform's own constant is `_QGATE_OWNER_STEP = 'default:pre-push-quality-gate'` |
| F5a | round 1 | `test_manage_execution_manifest_validate.py:431-432` — fixture annotations `architecture-refresh # order 25` (real 10) and `finalize-step-preference-emitter # order 61` (real 992); a test fixture hardcoding retired values that still passes | **fixed** — both annotations corrected and the list re-sorted so its ascending presentation is true |
| F5b | round 1 | `test_validate_loadable.py:311` docstring — "sits pre-merge at order 61 (the settle band)" | **fixed** — post-merge, order 992, post-run-review band |
| F5c | round 1 | `decision-rules.md:463` — "moved the step to its pre-merge `order: 61`", read as current placement | **fixed** — marked historical, with today's order stated |
| F6a | round 1 | **Behavioural.** Removing `choices=` from `--lane` (D4.3) silently retired a live binding: `canonical-enum-choices-drift` takes its fail-closed no-`choices=` branch and SKIPs, so `manage-config/SKILL.md`'s documented `{off,standard,full}` became an unbound restatement — and this flag was that rule's own driving example | **fixed, not characterised** — the binding is replaced directly by `test_canonical_block_enum_equals_the_writer_set`, section-anchored, with an anti-vacuity companion and a neighbouring-verb control. Mutation-confirmed: reintroducing the historical `{off,auto,full}` drift turns it red |
| F6b | round 1 | `rule-provenance.md:242` says in the present tense "`choices=` **is** `{off,standard,full}`" | **fixed** — past tense, plus a note that the flag now declares none and where its binding lives |
| F7 | round 1 | D6's Done-when ("no document claims the probe writes nothing") unmet in the owning script: five prose sites in `_cmd_baseline_reconcile.py` claim "performs no writes" / "non-mutating classifier" | **fixed** — all five narrowed to what the probe guarantees (moves no refs, touches no working tree) with the persisted `references.json` write named. `grep -c "performs no writes"` → 0 |
| F10a | round 1 | `test_verdict_currency.py` ended the refusal-heading guard with `assert level, …` — a tautology (the regex guarantees 1–6 `#`) whose message reads as success text in a failure slot | **fixed** — replaced with a real level-set check |
| F10b | round 1 | A paraphrase of `ext-point-execution-context-workflow.md` was presented inside quote marks, in two places | **fixed** — de-quoted; the claim is unchanged and remains true |
| F10c | round 1 | `test_the_three_scopes_publish_their_populations` claims to publish counts and prints nothing | **fixed** — renamed to what it asserts (own-block population is a proper, non-empty subset), and the module docstring's item (6) updated to match |
| F8 | round 1 | Collateral check and report sections unfinished | **partly fixed** — § Collateral check is complete below, as are §§ Populations, Deliverables, Build gate and Reviewer participation's derived population. The sections that record Steps 7–9 (per-reviewer verdicts, Cost, Contract check, What have we learned, Residue) were left `_pending_` at the time because those steps had not run — they are filled at the point the run reaches them, not before. **All are now complete**, the run having merged; this row records the state when F8 was raised, not the state today |
| F9 | round 1 | D5's Done-when clause "every `effort resolve-target` in the former dispatch-site files carries `--workflow`" is not literally met | **rejected, with reason** — see § Collateral check |

### Round 2 — the pre-PR verification sub-agent, re-dispatched over the round-1 fixes

The verifier re-read every round-1 fix against the tree it landed on and raised **eight** findings
(A1–A8), **all condition A** (a statement in the shipped tree that is false); three of them are text
*this run wrote* — round-1 fixes whose own new prose, or whose neighbours, the fix falsified. Two more
rows below came from elsewhere in the same round and are labelled by their source rather than folded
in: **A9** from the whole-tree build gate and **A10** from a cold read. Ten rows in total. Each was
re-verified against the tree here before being fixed.

| # | Source | Finding | Disposition |
|---|---|---|---|
| A1 | round 2 | `ext-point-finalize-step.md` § "Declaration is step-level" — "`branch-cleanup.md` has four `--outcome done` branches plus a `loop_back` call". D7.3 wired `merge_state` at **six** done branches in that same file, so this run's own edit turned a stale count into an in-document contradiction. Re-counted in the tree: **six** terminal `mark-step-done --outcome done` call sites (lines 1732, 1764, 1774, 1784, 1798, 1813 — the doc's own Branches A through F) and **three** `--outcome loop_back` call sites (945, 1092, 1176). The eleven lines a bare `grep -c -- '--outcome done'` returns are those six call sites plus five non-call-site lines — four prose references (1703, 1707, 1714, 1715) and one partial-flag snippet (169) | **fixed** — both counts corrected, the branches named by their letters; consistent with the same file's § "Structured step facts", which already said six |
| A2 | round 2 | F7's fix narrowed the "performs no writes" claim in `_cmd_baseline_reconcile.py`, but the claim survived at **five further sites**, one of them prose D6 itself wrote: `workflow-integration-git/SKILL.md:924`, `refine-workflow-detail.md:288` and `:254`, the operator-facing `probe_mutated_head` message in `_cmd_baseline_reconcile.py:565`, and `test_baseline_reconcile.py`'s module docstring | **fixed at all five** — each narrowed to what the probe guarantees (moves no refs, touches no working-tree file), with the persisted `references.json` write named where the site had room for it |
| A3 | round 2 | `workflow-integration-git/SKILL.md:883` and `:184` both say the probe lists upstream commits "since the captured `worktree_sha`". The implementation reads no stored SHA — `grep -c worktree_sha _cmd_baseline_reconcile.py` → **0**; it recomputes `merge-base(HEAD, origin/{base_branch})` per call, which is what makes it idempotent | **fixed at both** — the real anchor stated, with "recomputed per call, never read from a stored SHA" |
| A4 | round 2 | `manage-config/standards/data-model.md:730` names the qgate owning step as `pre-push-quality-gate` — the same unprefixed id F4 corrected at three other sites, and the same id `step set` refuses | **fixed** — `default:` prefix added; it was the fourth site, missed because F4's sweep was scoped to the three files that round named |
| A5 | round 2 | F5a's fix corrected two order annotations in `test_manage_execution_manifest_validate.py` and re-sorted the ascending list — which left a **neighbouring** reverse-sorted seed no longer descending, a comment falsified by the fix beside it | **fixed** — the seed re-ordered to be genuinely descending (1100, 999, 998, 992, 70, 22, 11, 10, 3), each entry annotated with the order it carries |
| A6 | round 2 | F10c renamed the test whose name over-claimed, but `ext-point-finalize-step.md:142` still echoed the old claim — the guard "**publishes each scope's population**", which it does not | **fixed** — "asserts how far each scope reaches", matching what the renamed guard does |
| A7 | round 2 | § Build gate's "19 files … out of 48 changed" and `21101 passed` are exact for commit `1e61000`; the round-1 fixes moved the diff to **22 / 54**, and no `./pw verify` was recorded over that tree while the section reads as the gate verdict for the diff being shipped | **fixed** — figures re-derived and `./pw verify` re-run over the round-2 tree; see § Build gate |
| A9 | build gate | **Raised by the whole-tree gate, not by a verifier.** § Collateral check cited a still-present test module whose filename contains the retired `ceremony_policy` token, tripping `test_lane_refactor_cleanup_sweep::test_no_ceremony_policy_json_key_or_dotted_paths`. Red since the round-1 report commit; the per-commit gate missed it because that commit's `*.py` edits were elsewhere and this guard is tripped by a `.md` line | **fixed by narrowing the guard**, after a first attempt to work around it failed — see below |
| A10 | cold read | D4's `[#run-at-all-gates]` section gave `step set … --param lane` only as a bare fragment, never as a runnable command, and never said how it relates to the fully-worked `set-lane` example above it. A fresh reader answered `set-lane` first and warned that "an operator who stops reading at the NOTE will run the other command" | **fixed** — the complete command added, plus the executed relationship between the two verbs. Details and the measurements behind them in § Cold reads |
| A8 | round 2 | F8's row claimed "the report's remaining sections completed"; §§ Reviewer participation (verdicts), Cost, Contract check, What have we learned and Residue were still `_pending_` | **fixed** — F8's disposition restated as **partly fixed**, naming which sections are complete and why the Step 7–9 sections are not yet filled |

### Cold reads (Verification §2)

Four fresh readers, one per deliverable, each given an **interpretation** brief and barred from this
plan, from `doc/plans/` entirely, from every Python source and test file, and from searching the
repository — so the answer measures what the changed text conveys on its own. Each was asked to report
**which reading it took**, including any wrong path taken first. Answers are recorded as given.

| Deliverable | Question | Reading taken | Verdict |
|---|---|---|---|
| **D4** | "An operator wants to switch off the finalize self-review. What exact command do they run?" | `plan phase-6-finalize step set --step-id default:pre-submission-self-review --param lane --value off` | **pass** — names the `step set … --param lane` route against the prefixed id, and did **not** produce the `plan phase-6-finalize set --field self_review` form the plan names as the failure signal. Reported one wrong path first (see below) |
| **D3** | "I need one extra prompt-body field. Where do I declare it, where do I carry it, does the generic template suffice?" | Declare in `requires_prompt_fields` **and** the step's input table (`Required`); carry in the step's own `prompt:` block **or** the generic template's declared-field slot; **yes**, the generic template suffices | **pass** — all three parts match the contract |
| **D6** | "The command exited 0 and printed `status: skipped, reason: merge_base_unresolved`. What next?" | Branch on `status` first; force the consumer's own conservative decision; log the `reason` token; **do not read `classification`** (no such field on a skip) | **pass** — and the reader named the exit-code trap unprompted: "exit code 0 carries no signal here" |
| **D8 / 440-G2** | "A head-dependent step has a `done` record and HEAD has moved. Re-fire or skip?" | "Neither unconditionally — consult the verdict-currency classifier"; separately identified the absent-`head_at_completion` sub-case as the one unconditional re-fire | **pass** — the reader reported the redundant "NOT an unconditional re-fire" caveat "worked", steering it off a bare re-fire |

Four passes. Three readers additionally reported wording weaknesses that the pass/fail criterion does
not capture; each was checked against the substrate before deciding what to do:

- **D4 — two routes, one shown.** The reader first answered `finalize-steps set-lane --lane off` and
  only switched after reaching the ceremony-gate paragraph, warning that "an operator who stops
  reading at the NOTE will run the other command". Checked by execution rather than by reading: on a
  seeded config `set-lane --step-id default:pre-submission-self-review --lane off` **succeeds** and
  writes `{"lane": "off"}` — byte-identical to what `step set --param lane --value off` writes, since
  both target `plan.phase-6-finalize.steps.<id>.lane`. So the reader's first answer was not wrong,
  merely undocumented as equivalent. Two further facts were measured the same way: `step set`
  **errors** (`Step '<id>' not found in phase-6-finalize`) when the step is absent from the map, where
  `set-lane` materialises it; and `_seed_finalize_steps()` seeds **19** steps including all four
  ceremony-gate owners, so that difference never arises for a ceremony gate. **Fixed** — the section
  now carries the complete runnable `step set` command (the reader had to splice it from three
  places), states that the two verbs are interchangeable for `off` / `standard` / `full`, and says why
  `step set` is the one named: it is the only route to `minimal`, the value that forces a gate in.
- **D3 — an unanchored "here", and a trigger phrased in terms of a dispatch body.** The reader reached
  the right answer but had to leave the section to resolve "declares each extra field **here**", and
  flagged that the mandatory-trigger sentence ("a step whose **dispatch body** carries any field
  beyond the generic contract") does not squarely cover a template-dispatched step with one extra
  field — inviting the reading that you declare only if you wrote your own block. **Left as-is with
  reason:** the sentence is accurate, the Input-table-agreement scope resolves it unambiguously, and
  the reader did resolve it. Recorded so the next editor of that paragraph sees the trap.
- **D6 — "fail closed" without a control-flow prescription.** The reader noted that
  `merge_base_unresolved` says "Fail closed: skip without a classification" but, unlike `fetch_failed`
  ("Log warning, skip — do not block refine"), never says whether the consumer halts, warns, or
  escalates. **Left as-is with reason:** prescribing the consumer's control flow is a behaviour
  decision about phase-2-refine, not a truthfulness defect in the return contract D6 was scoped to
  state, and inventing one here would be the restatement-without-substrate pattern this plan exists to
  remove. Recorded in § Residue as a genuine documentation gap for a later plan.

### Round 3 — the pre-PR verification sub-agent, re-dispatched over the round-2 fixes

Thirteen findings, all condition A. The verifier re-ran the full gate independently (`21107 passed`,
`FAILED` count 0, reproduced exactly), re-executed twelve of the ledger's mutations character-for-
character, and re-derived every population. **Two findings are repeats of defects already marked
fixed** — the pattern worth naming in this run.

| # | Source | Finding | Disposition |
|---|---|---|---|
| R1 | round 3 | § Populations bullet "`reads:` is declared by zero implementors" is false in the shipped tree — **D7.1 of this plan added it to five steps**. The section's preamble claims all four populations were "re-derived during this run", with no marker that the tables describe the pre-implementation baseline | **fixed** — § Populations now opens by stating it is the D1 baseline, and a § Post-implementation subsection derives the shipped-tree state |
| R2 | round 3 | Six cells of the population (a) table are `—` where the shipped frontmatter declares a value: `reads` on orders 3, 5, 6, 999, 1000 and `records_facts` on `create-pr` (20) and `emit-landing` (1000). The last two contradict this report's **own finding F1b** | **fixed** — all seven deltas tabled under § Post-implementation with the deliverable that added each |
| R3 | round 3 | The A9(a) ledger row quotes a failure message the test does not emit under that mutation — an earlier assertion in the same test fires first, so the quoted one is never reached. The message had been read off the test source, not the run | **fixed** — the harness now prints the emitted `AssertionError` and every cell is filled from it; the ledger preamble records why |
| R4 | round 3 | **A7 repeating.** § Build gate's re-derived figures (23/56) match no commit on the branch; at HEAD it is 24/57. The figures went stale the moment the commit correcting them landed | **fixed structurally** — the figures now carry the `git rev-parse --short HEAD` that produced them, because a diff-derived count is invalidated by the act of committing the correction |
| R5 | round 3 | "all six sub-steps observed in the stream" — `cmd_verify` runs **three**; six is the coverage-*dimension* count, and the same sentence then lists three | **fixed** — three, with the two counts explicitly separated |
| R6 | round 3 | Population (b) is headed "11 blocks in 7 files" and presented as current under the "re-derived during this run" preamble, while § Deliverables' D5 row says the population is now **0**. Its line numbers locate blank lines and unrelated keys | **fixed** — heading states both states; a § Post-implementation subsection records the zero and marks the line numbers as baseline record, not navigation |
| R7 | round 3 | `branch-cleanup.md:1770` ("no other fact is recorded") and `:1780` ("`work_performed=false` alone") are falsified by **this branch's own D7.3 wiring**, which added `merge_state` to both code blocks directly below them | **fixed** — both sentences state the second fact and why no `action`/`merge_mechanism` accompanies it |
| R8 | round 3 | **F4/A4 repeating, fifth site.** `data-model.md:782` names `steps['pre-push-quality-gate'].lane`; A4 fixed line 730 of the same file and stopped | **fixed** — `default:` prefix added |
| R9 | round 3 | `finalize-step-order-bands.md:37` says "the integers 1–11 are fully occupied"; its own bullet nine lines later says 3–11 are occupied, "leaving only 1–2 free" | **fixed** — the table row now states what the bullet does |
| R10 | round 3 | `configuration.adoc`'s run-at-all `get`/`set` demonstration sets `finalize_without_asking`, which the same document classifies as an auto-continuation knob and explicitly "separate from" run-at-all gates. `phase-6-finalize` carries no run-at-all gate at all | **fixed** — the example now sets `phase-1-init deep_lane`, a real run-at-all gate, and keeps the ceremony-gate read as the contrast |
| R11 | round 3 | **The A9 carve-out was wider than its own rationale.** `doc/plans/` holds live documentation — its README, five epic READMEs, `_template/plan.md`, each plan.md — which CLAUDE.md says "follow the standards unchanged". Excluding the tree stopped policing all of them | **fixed by narrowing to run reports only** — see below |
| R12 | round 3 | The D8/440-G2 row's "no sentence prescribes an unconditional re-fire" is contradicted by `SKILL.md:1766` and by this report's own cold-read row | **fixed** — qualified to steps whose verdict can still be current, naming the absent-stamp row as the deliberate exception |
| R13 | round 3 | Two counts do not reproduce under their stated commands: `grep -c "unconditional rebase"` returns 1 unscoped (0 scoped to the file the row is about), and the convention header is used by **10** docs, not 11 | **fixed** — both commands stated as run, with the scope that makes them true |

**R11 — the carve-out, narrowed to the boundary the repository already draws.** The first carve-out
excluded `doc/plans/` wholesale on the rationale that it holds "records of work that HAS happened".
That rationale does not cover the tree: `doc/plans/README.md` is cross-referenced from `CLAUDE.md`,
`doc/plans/_template/plan.md` propagates into every new plan, and CLAUDE.md states plainly that "the
plan itself and every README follow the standards unchanged" — they are current documentation, and a
retired token in any of them is a live orphan the sweep must still catch.

CLAUDE.md draws the exact line needed, in the same records-versus-documentation terms, when it exempts
a run report from the "No timestamps" / "Current state only" standards: *"a lane run report
(`doc/plans/{epic}/{plan-name}/report-NN.md`) carries a date and an ordinal, because it is a dated
record of one execution rather than documentation of the current state … No other file in `doc/plans/`
takes this exemption."* The carve-out is now exactly that — `doc/plans/**/report-NN.md` and nothing
else — so it is not this module's invention but the repository's own boundary, applied where it
already applies. Verified sufficient: the retired tokens appear in exactly one file under `doc/plans/`,
this report. Four guards hold it, each seen RED (§ The red-first ledger), including a control that
fails if the exclusion ever widens back to the tree.

### Round 4 — sweeping the defect classes rather than re-checking the sites

Ten findings. The round was briefed on the pattern the first three established — **a fix applied at the
sites one round names, rather than across the class, comes back** — and that brief is what produced
findings 1, 6 and 7. The verifier also reproduced the gate independently (`21108 passed`, zero
`FAILED`, coverage line verbatim), replayed five ledger mutations character-for-character, and
re-derived all four populations; those held.

| # | Source | Finding | Disposition |
|---|---|---|---|
| S1 | round 4 | **R2 recurring.** § Post-implementation says "six cells … are superseded" over a table of seven, and an **eighth** was missing: `default:branch-cleanup`'s `records_facts` gained `merge_state` from D7.3, which this report's own **F1a** records. Round 3's fix transcribed the two sites round 3 named | **fixed** — `branch-cleanup` row added, count stated as eight from the rows, preamble corrected to name all three `records_facts` sites |
| S2 | round 4 | § Build gate's green block is labelled "third run … and its **three** guards" over a `21108` figure; that tree carries **four** guards, and the section itself says so 14 lines later. 21107 was the three-guard total | **fixed** — "fourth run of this gate … its four guards" |
| S3 | round 4 | **Condition B.** "Four guards … each seen RED" is false for one: `test_the_rest_of_doc_is_still_swept` goes red under **none** of the three recorded mutations, and has no ledger row | **fixed** — mutated (carve-out swallows all of `doc/`), seen RED with its own distinct message, ledger row (d) added with an sha256-verified restore |
| S4 | round 4 | `SKILL.md:1766` cited for the absent-`head_at_completion` row; that row is at **1768**, and 1766 is the `matches live HEAD` row. The citation never matched — it was written after that file's last edit | **fixed** — 1768 |
| S5 | round 4 | § Collateral check omits `test_lane_refactor_cleanup_sweep.py` (+125/-2) and three other files. Verification §6 asks for the file list, not only the narrative | **fixed** — five rows added |
| S6 | round 4 | **F4/A4/R8 recurring, sites six through eight.** `_config_defaults.py:412` and `:1081` and `test_ceremony_policy.py:73` still name the bare `pre-push-quality-gate` key | **fixed** — and the exhaustion claim first made here was itself false, see **T2** |
| S7 | round 4 | `.claude/skills/finalize-step-plugin-doctor/SKILL.md:27` names `default:finalize-step-pre-push-quality-gate` — an id that resolves to **nothing**; the file is one this branch edits | **fixed** — `default:pre-push-quality-gate` |
| S8 | round 4 | Commit `c92dd11`'s message asserts "all six sub-steps observed", the statement R5 corrected in the report. A commit message is part of the shipped tree | **recorded, not fixable** — see § Residue; rewriting pushed history to correct prose would cost more than the false line does |
| S9 | round 4 | `_orchestrator_inbox.py:808` says `LANDING_REQUIRED_KEYS` "is NOT re-listed in prose elsewhere". Two documents re-list it, and **D8's own two new tests exist to bind them** | **fixed** — the comment now names both surfaces and the tests that bind them |
| S10 | round 4 | § Findings' round-1 preamble says "Ten findings:" over a 17-row table, while commit `65669cb` says "fourteen findings … plus three nits" | **fixed** — the preamble states the row count and reconciles it against the F-numbering |

### Round 5 — the final round, and the exhaustion claim that was not

Five findings plus three minor ones, and a verdict of **`budget-exhausted`**, not `verifier-clear`. The
verifier replayed ledger row (d)'s mutation (the quoted message reproduced exactly), counted the
eight-cell delta table against frontmatter, ran both figure commands verbatim, re-derived all four
populations, checked every D1–D8 Done-when clause that is executable, read all fifteen commit messages
as shipped text, and reproduced the gate character-for-character. **All of that held.** What did not
hold was, once again, counting prose.

| # | Source | Finding | Disposition |
|---|---|---|---|
| T1 | round 5 | The sweep module's own comment says "The three tests below pin each half of this" over **four** guards — omitting exactly the one round 4 found missing from the ledger. S3 fixed the report and left the source comment carrying the same undercount | **fixed** — the comment names four and lists them |
| T2 | round 5 | **The strongest claim this report made, and it was false.** S6's disposition and commit `df64757`'s message both said the unprefixed-step-id class was "swept to exhaustion — the tree-wide grep … returns nothing outside this report". Three sites remained (`test_config_defaults.py` ×2, `test_cmd_ceremony_policy.py` ×1), in the **unquoted-bracket** form `steps[pre-push-quality-gate]`. The sweep behind the claim had matched the quoted and dotted forms only — so the claim rested on a grep that did not cover the class it claimed to exhaust | **fixed** — three sites corrected (nine through eleven), and the claim replaced by a stated scope, below |
| T3 | round 5 | "the run's largest test change (+127 lines)", twice. It is **125/2** and ranks **seventh**; `test_step_prompt_fields_contract.py` (360/51) is nearly three times larger, and a collateral sibling (`test_finalize_steps_lane_rejection.py`, 268/0) is more than twice it. "+127" was the `--stat` total, not insertions | **fixed** — the superlative dropped, the figure stated as `+125/-2` |
| T4 | round 5 | "this branch changes Python … **true at every commit on it**" — false at the first two commits (`a1b11b4`, `28669af`), which touch no `*.py`. The same section says four paragraphs later that per-commit gates ran "ahead of every `*.py`-touching commit", presupposing commits that touch none | **fixed** — scoped to `b935f14` onward, with the two exceptions named |
| T5 | round 5 | § Collateral check still omits `_cmd_baseline_reconcile.py` (32 lines, in no § Expected surface entry) after S5 claimed to complete the list | **fixed** — row added; the change was already explained narratively under F7/A2, so this was a list-completeness gap |
| T6–T8 | round 5 | Three minor: ledger row (d) said "the three mutations **below**" when two are above it; row (d) named one failing test where the mutation fails three; row 160/G2's message cell paraphrases (`missing 'build.py', 'targets'`) rather than quoting the emission | **T6/T7 fixed**; **T8 recorded** — see § Residue |

**T2 — what the class actually is, stated instead of an exhaustion claim.** The sweep behind "exhaustion"
was too narrow, and the claim was also the wrong *shape*: a bare `pre-push-quality-gate` is not by
itself a defect. **210** bare mentions remain and are correct, because two namespaces are in play:

- **The config-key namespace** (`plan.phase-6-finalize.steps`), where the seeded key carries `default:`
  and a bare id resolves to nothing — `step set --step-id pre-push-quality-gate` errors. Every
  reference of the form `steps[…]`, `steps.…` or `--step-id …` belongs here, and **eleven** such sites
  were corrected across F4, A4, R8, S6 and T2.
- **The manifest namespace**, which is canonically bare *by design*: `canonicalize_step_key` strips
  `default:` before comparison, so `_BUILD_EVIDENCE_PHASE_6_STEPS = frozenset({'pre-push-quality-gate'})`
  is correct and prefixing it would break the lookup. Prose naming the step also belongs here.

So the honest statement is scoped, not absolute: **every config-key-path and `--step-id` reference to
this step now carries its prefix**, verified by a grep covering the bracketed (quoted and unquoted),
dotted and `--step-id` forms. The bare mentions that remain are the manifest namespace and prose, where
bare is right. An "exhaustion" claim over a class whose boundary had never been stated is what let the
same defect recur five times; the boundary is now stated.

### Collateral check (Verification §6)

Changed files outside § Expected surface, each explained:

| File | Why |
|---|---|
| `marketplace/.../manage-config/SKILL.md` | D4.3 consequence: the canonical `set-lane` block documents the refusal, and its registry row carried a stale `off`/`auto`/`full` enum and an unprefixed owning-step id (F4). Also the surface the F6a binding now checks |
| `marketplace/.../manage-execution-manifest/standards/manifest-schema.md` | F4 — the third site carrying the unprefixed `pre-push-quality-gate` owning-step id |
| `marketplace/.../manage-execution-manifest/standards/decision-rules.md` | F5c — the third `order 61` restatement, in the bundle 300/G9 edits |
| `marketplace/.../plugin-doctor/references/rule-provenance.md` | F6b — its present-tense `choices=` claim is falsified by D4.3 |
| Two `test/plan-marshall/manage-config/` modules — `test_manage_config_cli.py` and the dissolved-block CLI regression module beside it | D4.3 consequence: both pinned the argparse exit-2 rejection D4.3 replaces. Re-pinned to `status: error` + the routed message. The second is named indirectly on purpose — see § Residue |
| `test/plan-marshall/manage-config/test_finalize_steps_lane_rejection.py` (new) | D4.3's own contract test, plus the F6a replacement binding |
| `test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py` | D8 / 440-G2 consequence: it pinned the superseded "Re-fire (HEAD has advanced)" wording. Re-pinned to the deferral |
| `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_validate.py`, `.../test_validate_loadable.py` | F5a/F5b — stale order annotations in the bundle 300/G8 edits |
| `test/plan-marshall/build-pyproject/test_gate_coverage_parity_substrate.py` (new) | D8 / 160-G2's substrate test. § Expected surface anticipates it as "a parity-cell substrate test for D8 / 160/G2" |
| `test/plan-marshall/test_lane_refactor_cleanup_sweep.py` | **+125/-2, and in no § Expected surface entry.** Not a deliverable: the A9/R11 carve-out and its four guards, forced when the whole-tree gate showed this report could not name the guard it tripped. Narrated in § Build gate and **R11**; listed here because Verification §6 asks for the file list, not only the explanation |
| `test/plan-marshall/build-pyproject/test_gate_coverage.py` | D8 / 160-G2 consequence. § Expected surface names the *directory* but not this module; the collateral row above named only the new substrate file beside it |
| `marketplace/.../plan-orchestrator/scripts/_orchestrator_inbox.py` | Round 4 finding 9: its `LANDING_REQUIRED_KEYS` comment claimed the set "is NOT re-listed in prose elsewhere", which D8's two new binding tests disprove by construction |
| `marketplace/.../manage-config/scripts/_config_defaults.py`, `test/plan-marshall/manage-config/test_ceremony_policy.py` | Round 4 finding 6 — the sixth to eighth sites of the unprefixed `pre-push-quality-gate` id, found by sweeping the class rather than re-checking the named sites |
| `test/plan-marshall/manage-config/test_config_defaults.py`, `test/plan-marshall/manage-config/test_cmd_ceremony_policy.py` | **T2** — sites nine through eleven of the same id, in the unquoted-bracket form the earlier sweeps' greps did not match |
| `marketplace/.../workflow-integration-git/scripts/_cmd_baseline_reconcile.py` | **T5** — D6's owning script, in no § Expected surface entry (which lists six production scripts, not this one). Its change is F7 + A2: five prose sites claiming the probe "performs no writes", narrowed to what it guarantees |
| `.claude/skills/finalize-step-plugin-doctor/SKILL.md` | § Expected surface lists it only as "D2.3 mutation target, restored". It additionally carries a real **D7.1** edit — `reads: [worktree]` — which the surface list did not anticipate |
| `marketplace/.../manage-config/standards/data-model.md` | A4 — the fourth site carrying the unprefixed `pre-push-quality-gate` owning-step id F4 corrected elsewhere. Entered the diff in round 2 |
| `test/plan-marshall/workflow-integration-git/test_baseline_reconcile.py` | A2 — its module docstring was one of the five surviving "non-mutating classifier" restatements. Entered the diff in round 2; docstring only, no assertion changed |

**F9 — why D5's clause is not literally met, and why that is correct.** The clause reads "every `effort
resolve-target` in the former dispatch-site files carries `--workflow`".
`plan-marshall/workflow/planning.md:233` (the light-lane dispatch) is a bare
`effort resolve-target --role phase-3-outline` and was deliberately left alone: it carried **no**
hand-written `[DISPATCH]` block, so it was never in population (b). It is a *zero-emission* dispatch
site — gaps 280/G3 and 280/G7 — which the plan's § Out of scope excludes by name, adding that "D5's
closing sweep is scoped to the hand-written-emission population and does not claim the dispatch-site
population is complete." The Out-of-scope section governs; the clause as written overreaches its own
plan. Recorded rather than silently satisfied.

## Reviewer participation

**Population, derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc, not a
list transcribed here:

```bash
grep -rn "^author_login:" marketplace/bundles/plan-marshall/skills/automatic-review/standards/*.md
```

| Registry doc | `author_login` | `trigger_comment` |
|---|---|---|
| `coderabbit.md` | `coderabbitai` | `@coderabbitai review` |
| `pr-agent.md` | `cuioss-review-bot` | `/review` |
| `sourcery.md` | `sourcery-ai` | `@sourcery-ai review` |

M = **3**. Per-reviewer verdicts, each derived from the stored comment bodies across all three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`), are recorded below once the PR has been opened
and read back.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | **Participated — four passes, 8 findings** | Yes, three times | Reviewed `083068e`, `518b2b5`, `03877a1`. Each pass raised findings against the commit that fixed the previous pass |
| `cuioss-review-bot` | **Participated — clean** | No | One "PR Reviewer Guide": *"PR contains tests / No security concerns identified / No major issues detected"* |
| `sourcery-ai` | **Refused — `refused_structural`** | No | *"your pull request is larger than the review limit of 150000 diff characters"*. Measured: `git diff origin/main...HEAD \| wc -c` → **437,707**, 2.9× the ceiling |

**Coverage shortfall, disclosed rather than absorbed.** Of M = 3, two reviewed and one refused
structurally — and the commit that merged was reviewed by **none of them**.

- **sourcery** cannot be cleared by re-request: the ceiling is a property of the diff, so the only
  remedy is splitting the PR. Re-triggering would have spent a request for the identical answer.
- **coderabbit did not review the head that merged.** `f07f0ea` fixes three findings against
  `03877a1`; its review was blocked by the per-developer rate limit (*"You've used all free OSS
  reviews for now"*), which did not reopen across three retries spaced by the ETAs CodeRabbit itself
  published — 32, 41 and 29 minutes, the last two ~10 hours apart in wall-clock. The operator judged
  the existing reviews sufficient and directed the merge. Recorded because this report's other review
  claims describe the commits that *were* reviewed, and `f07f0ea` was not one of them.

**What the automated reviewers caught that five in-house rounds did not.** The sharpest finding of the
run was CodeRabbit's, against a fix this run had just made: moving Branch F to `loop_back` closed the
lost-cleanup path but sent `state == closed` and unreadable-state observations into a retry against
input that cannot change. Five verification rounds never examined that branch's input population. Its
other findings were the same family the rounds were already producing — counting prose, doc-echo
drift, an under-exercised test — but that one was a behavioural regression this run introduced and
would otherwise have shipped.

## Cost

**Not instrumented, and that is a property of the lane.** There is no token ledger here — `.plan/` is
absent from the clone, so the per-dispatch accounting a local run records was never available. What
follows is what the run's own artifacts support, each countable from git, the PR, or the gate logs.

| Measure | Value |
|---|---|
| Commits on the branch | 22 |
| Files changed | 62 (+3377 / −443) |
| Whole-tree `./pw verify` invocations | **12** — 8 reported `SUCCESS`, 3 ended with `FAILED` lines, 1 was interrupted and restarted |
| Verification sub-agent dispatches | 5 rounds + 4 cold reads = **9** |
| Automated review passes | 4 CodeRabbit, 1 pr-agent, 1 sourcery refusal |
| Findings raised and dispositioned | **60** — 52 across five rounds, 8 across four review passes |
| Wall-clock, first commit to merge | 2026-08-19T19:28Z → 2026-08-20T08:26Z ≈ **13 h**, of which ~10 h was rate-limit wait |

Two of the three red gates were red because a guard caught **this run's own change** — the sweep guard
tripping on the report's text, and the `work_performed` false-carrier guard tripping on the
`loop_back` migration. That is the gate working, not the run thrashing; the third was a ruff `F401`.

The figure worth carrying forward is the gate count. **12 whole-tree runs at roughly six minutes each
is over an hour of gate time**, and the shape that produced it — fix, gate, push, review, fix again —
is the same shape that produced the findings. A cheaper run would have been a less-verified one.

## Contract check (Step 9)

Against `cloud-plan-lane`, step by step. Each row states what was done, not merely that it was.

| Step | Contract | This run |
|---|---|---|
| 1 | Load the lane skill first | Loaded as the first action, before reading the plan |
| 2 | Keep the harness-assigned branch | `claude/step-contract-ordering-refire-cjlzup` kept. The reason is resumability, not convenience: a reclaimed VM re-clones and cannot find a renamed branch |
| 3 | Plan-directory lifecycle | `plan.md` moved into `510-.../`; this report beside it |
| 4 | Implement | D1–D8, plus five behavioural fixes that came out of review |
| 5 | Conditional build gate | Fired — the branch changes Python. Verdict read from the streamed output, never the exit code; two real defects were caught exactly that way while the wrapper exited 0 |
| 6 | Pre-PR verification sub-agent | 5 rounds, the full budget. Exit `budget-exhausted`, **not** `verifier-clear` |
| 7 | PR and review cycle | PR #1309, no `skip-bot-review` (the diff carries `*.py`, bundles and `.claude/skills/**`). Every thread answered; 10 of 11 resolved, 1 left open deliberately |
| 8 | Merge gate | **Deviation, operator-directed — see below** |
| 9 | Report and closing self-check | This document |
| — | `.plan/` never touched | `git status --porcelain .plan/` empty at every commit |
| — | Temp files outside the repository | Scratchpad and `/tmp` only; mutation snapshots written there and restored in a `finally` |
| — | No plugin-cache sync performed or owed | Correct for this lane |

**The one deviation, stated plainly rather than absorbed.** § Step 8 condition 6 gates the merge on
CodeRabbit's review where the PR carries no `skip-bot-review` label, bounded by a retry budget so the
gate *delays* rather than *strands*. This run exhausted that budget: three retries, each placed after
the ETA CodeRabbit published, and the allowance never reopened. The gate's design anticipates delay,
not indefinite blockage. The operator, reading the evidence recorded in § Reviewer participation,
directed the merge on the strength of the reviews already obtained.

The merge is therefore **operator-authorised, not gate-satisfied**. The distinction matters and is not
blurred here: `f07f0ea` shipped unreviewed, and a reader of this report should not infer that every
shipped commit passed a bot review.

## What have we learned (Step 9)

- **A green single-test run is not a green tree, and this run recorded one as the other.** After the
  sweep guard failed, the fix was verified by re-running that one test (`6 passed`) and written up as
  resolved. The next whole-tree gate returned the same failure with **four** hits instead of one,
  because writing the finding up had reintroduced the token three more times. The lesson is not "run
  more tests" — it is that a scoped re-run answers a scoped question, and the report claimed the
  unscoped one.
- **A fix applied at the sites a review names, rather than across the class the defect occupies, comes
  back.** One defect — an unprefixed step id — was declared "fixed at all three sites", then "the
  fourth site", then "fifth", then "sites six through eight", then "nine through eleven". **Five
  rounds, each fixing exactly what it was shown.** What ended it was not another sweep but stating the
  class boundary: which namespace requires the prefix and which is canonically bare. A defect class
  without a written boundary cannot be exhausted, only chased.
- **An exhaustion claim is only as good as the search behind it, and the search is the part nobody
  checks.** "Swept to exhaustion" was written on a grep matching two of the defect's three surface
  forms. It read as the strongest claim in the report and was the weakest thing in it.
- **Quoting a plausible failure message is the same defect as quoting a plausible fact.** The
  red-first ledger carried a message read off the *test source* for a mutation under which that
  assertion never fired — an earlier one failed first. The harness now prints the emitted
  `AssertionError` and the cells are filled from the run.
- **A guard that fails when you fix a bug may be encoding the bug.** The `work_performed`
  false-carrier guard went red because the work-free `done` branch it required had been moved to
  `loop_back` — which *was* the fix. Widening it to terminal outcomes was right, but a guard relaxed
  to accommodate one's own change is the one to distrust most, so the widened form was mutation-tested
  before being trusted.
- **A status check can be green and mean nothing.** CodeRabbit's context reported `success` with the
  description "Review rate limited" — state and meaning in direct contradiction. Twice, the only way
  to know whether a review had happened was to check whether a review *existed*.
- **Counting prose is where a careful run's defects concentrate.** For the final two verification
  rounds, every finding was in this report's own numbers: a seventh-largest change called the largest,
  three tests described where four exist, "true at every commit" false at two commits. The substrate
  work — populations, guards, mutations, the gate — reproduced exactly every time it was re-derived.
  The prose about that work did not.
- **Reviewers with different reach find different things, so a structural refusal is a real gap.**
  Sourcery refused on diff size and its share of the review surface was simply never covered. The PR
  was 2.9× its ceiling; the only remedy is a smaller PR. A 62-file plan is at the edge of what this
  review apparatus can actually inspect, which is an argument for splitting future plans of this size
  rather than a note about one tool's limits.

## Residue

Things this run found, did not fix, and is naming rather than leaving for someone to rediscover.

- **Ledger row 160/G2's failure-message cell paraphrases rather than quotes (T8).** It reads ``missing
  `'build.py'`, `'targets'` ``; the emission is the assertion's own prose plus pytest's *"Extra items in
  the right set: 'targets' / 'build.py'"*. The ledger preamble asserts every cell "is the assertion text
  the mutated run actually emitted", so this one cell contradicts its own preamble. **Left as-is**: the
  mutation, the named test and the substance are all correct and were re-verified in round 5; only the
  transcription is loose. Fixing it means re-running that mutation solely to re-transcribe a cell whose
  meaning is not in doubt. Named here rather than silently tolerated, because it is the same class as
  **R3** — the defect that made this ledger quote emissions in the first place.

- **Commit `c92dd11`'s message carries a false statement this report has since corrected.** It reads
  "all six sub-steps observed in the stream"; `cmd_verify` runs **three**, and six is the coverage-
  dimension count (round 3's **R5**, fixed in § Build gate). The commit is pushed, so correcting it
  means rewriting published history — a real cost, against a line whose only reader is `git log`, and
  whose correction is recorded here and in the section it describes. **Left standing deliberately**,
  and named because a run about truthful signals should not quietly ship one. The general point is
  worth more than this instance: a commit message is part of the shipped tree and is *harder* to
  correct than the file it describes, so a claim inside one should be measured before it is written,
  not after. Round 4 found this by reading `git log -p` as shipped text, which no earlier round did.

- **A residual test module still carries the retired token in its filename.** The `doc/plans/`
  carve-out (A9/R11) stops that name from breaking run reports, but the underlying oddity stands: a
  module under `test/plan-marshall/manage-config/` is named after machinery that was dissolved, so any
  *live* document — `doc/user/`, `doc/developer/`, a skill doc — that needs to cite it by path still
  cannot. Renaming it is the remaining half of the cleanup and is out of this plan's scope. Noted here
  because the carve-out makes the problem quieter, not gone.
- **`baseline-reconcile`'s fail-closed skips prescribe no consumer control flow.** Surfaced by D6's
  cold read. `head_unresolved` and `merge_base_unresolved` say "Fail closed: skip without a
  classification", while `fetch_failed` says "Log warning, skip — do not block refine on transient
  infrastructure issues". The first two therefore leave a consumer author unable to tell whether
  fail-closed means halt refine, warn and continue, or escalate. Deciding it is a phase-2-refine
  behaviour question, not a restatement this plan could make true from existing substrate.
- **The `reason` token set is enumerated in one place only.** The same reader observed that
  `workflow-integration-git/SKILL.md`'s skip table lists a reason (`worktree_unresolved`) that the
  phase-2-refine table does not, and concluded — correctly — that SKILL.md is the complete token set.
  That is true today and is stated nowhere; a consumer switching on `reason` has to infer which of the
  two tables is authoritative.
- **F9 stands as rejected**, with its reasoning in § Collateral check: D5's Done-when clause
  overreaches its own plan's § Out of scope, which excludes the zero-emission dispatch site by name.
- **The preference-emitter admissibility gate is prose where the auditor has code — now staged as its
  own plan.** The one review thread left open on PR #1309. The cross-plan auditor enforces authorship
  admissibility in `_preference_admissible`; the per-plan emitter enforces it by instructing an agent
  in prose, and the routing standard says outright that the prose *is* the implementation. Closing it
  means creating a component that does not exist, which is why it was out of scope here.
  **Checked against every staged plan in this epic before filing** — `500`–`590` return only
  order-comment and documentation mentions of the emitter, none covering enforcement — so it is now
  `doc/plans/truthful-signals/600-preference-admissibility-is-prose-where-the-auditor-has-code.md`,
  carrying the finding, its provenance, and the constraint that `add_finding` must **not** be narrowed
  to reject a missing `bot_kind` (an absent value is the honest state for an unattributed human
  comment and for the pipeline's own).

**Two survivors shipped, both characterised above rather than carried silently:** commit `c92dd11`'s
message (unfixable without rewriting pushed history) and ledger row 160/G2's paraphrased cell. A third
item — `f07f0ea` shipping without a CodeRabbit review — is not residue but a **contract deviation**,
and is recorded as such in § Contract check.
