# Run report — 510-finalize-step-contract-ordering-and-refire-currency (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/step-contract-ordering-refire-cjlzup`    **PR:** _pending_    **Outcome:** _in progress_

> **Verification loop exit:** _pending_

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

- **`reads:` is declared by zero implementors** — D7.1's asserted absence, re-verified.
- **`destroys:` is declared by exactly two** — `default:branch-cleanup` → `[worktree]`,
  `default:archive-plan` → `[plan-directory]` — D2.5's two anchors, re-verified as present.
- **`create-pr` (20) → `era-stamp-fill` (21) → `ci-verify` (22)** — D2.1's adjacency holds today.
- **`mutates_source: true` AND `order > default:pre-push-quality-gate.order` (5)** resolves to
  `default:finalize-step-simplify` (8), `default:finalize-step-security-audit` (9),
  `project:finalize-step-era-stamp-fill` (21), `plan-marshall:automatic-review` (30),
  `default:sonar-roundtrip` (40) — D8 / 230-G1's correct membership.
- `default:lessons-capture` declares `mutates_source: false` — the wrong example 230/G1 names.

### (b) The hand-written `[DISPATCH]` emission population — **11 blocks in 7 files**

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

### (c) The per-implementor input-table `Required` row population — **1 row outside the contract**

```bash
python3 $TMPDIR/derive_pop_c.py . pop_a.json   # header-parsed Required column, never a fixed index
```

Across the 26 implementor docs, tables carrying a `Required` column yield 9 rows, of which **3** sit
in a table whose first header cell is `Prompt-body field` (the repository-wide convention header —
11 docs tree-wide use it verbatim) and **6** sit in `plan-retrospective`'s CLI `| Parameter |
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

### The red-first ledger (D2, and D3's declaration guard)

One row per mutation. Every mutation was applied through a harness that snapshots the target's BYTES
to an agent-private scratch path and restores them in a `finally` — never `git checkout`/`restore`,
which would rewrite the file from the index and discard this run's unstaged work. `git status` was
re-checked after each sweep; every target came back clean.

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
| 440/G2 | Lead sentence now defers the ACTION as well as the membership; the `differs from live HEAD` row points at Step 3's classifier; the closing summary is qualified. The `matches` and `field absent` rows left alone as the plan directs | done — no sentence in § Resumability prescribes an unconditional re-fire |
| 440/G3 | Located both sentences at `:1100` and `:1105` and routed each by `use_merge_queue` | done — `grep -c "unconditional rebase"` returns 0 |
| 410/G1 | Rewrote § (e)'s closing sentence from the presence-only test to the recognized-identity form, changing nothing else in the section | done |
| 410/G4 | Scoped the `default` claim in § (d), `audit.py`'s `_UNATTRIBUTED_MODULE` comment AND its `_preference_module` docstring, and `preference-pattern-detector.md`. Verified the other producer is real and live at `lessons-capture.md:132` (*"the `default` module is the first-class home for cross-cutting"*), and left that file unchanged as the plan directs | done |
| 300/G8 | Corrected the seed annotation `# order 61` → `# order 992`, the order the step's standards doc declares (`finalize-step-preference-emitter.md:7`). No assertion and no seed position changed | done |
| 300/G9 | Rewrote the sort-rationale parenthetical to name the order the step carried **at the time of the incident** with an explicit past-tense marker, plus the order its standards doc declares today | done |

## Build gate

**Python-change verdict.** `git diff --name-only origin/main...HEAD -- '*.py'` returns **19 files** (6
production scripts, 13 test modules) out of 48 changed. The gate therefore fires.

**Result.** `UV_PYTHON=3.12 UV_HTTP_TIMEOUT=600 ./pw verify` — the full three-sub-step form, not the
narrower calls, so `test-compile` (mypy over the whole `test/` tree) is included:

```text
21101 passed, 14 skipped in 350.69s
coverage: COMPLETE over the dimensions below — checked over full scope:
  mypy(production) [415 files, cache disabled], ruff [marketplace/bundles, test, .claude],
  SPDX headers [marketplace/bundles, test, .claude, marketplace/targets, build.py],
  plugin-doctor [marketplace-wide], mypy(test) [780 files, cache disabled],
  module-tests [whole-tree pytest]
```

Read from the streamed output rather than the exit code, per the lane contract: the coverage line
names all six dimensions as checked, and reaching `module-tests` at all proves `quality-gate` and
`test-compile` both passed — `verify` exits early on either, as this run observed directly when a ruff
`F401` stopped an earlier gate at the ruff step with exit code still 0.

Per-commit gates ran ahead of every `*.py`-touching commit. One found a real defect: after D4.3
removed `choices=` from `--lane`, ruff reported `F401 _RESOLVED_ASK_LANE_VALUES imported but unused`
**while the wrapper still exited 0** — the "read the output, not the exit code" case, caught by reading.
The fix removed the restatement rather than the import: the help string now interpolates the constant.

**Stale-base re-verification (§ Step 8 condition 2)** — recorded at the merge gate below.

## Findings

One row per instance. Source is the verification round that raised it.

### Round 1 — the pre-PR verification sub-agent

The verifier independently re-derived populations (a), (b) and (d), **executed** the resolver three
ways and the manage-config CLI, re-derived every character count and the Settle occupancy, read the
`baseline-reconcile` implementation and `_cmd_step`, ran 3246 tests, and read every new guard for
vacuity. It reported the new guards non-vacuous. Ten findings:

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
| F8 | round 1 | Collateral check and report sections unfinished | **fixed** — § Collateral check below; the report's remaining sections completed |
| F9 | round 1 | D5's Done-when clause "every `effort resolve-target` in the former dispatch-site files carries `--workflow`" is not literally met | **rejected, with reason** — see § Collateral check |

### Collateral check (Verification §6)

Changed files outside § Expected surface, each explained:

| File | Why |
|---|---|
| `marketplace/.../manage-config/SKILL.md` | D4.3 consequence: the canonical `set-lane` block documents the refusal, and its registry row carried a stale `off`/`auto`/`full` enum and an unprefixed owning-step id (F4). Also the surface the F6a binding now checks |
| `marketplace/.../manage-execution-manifest/standards/manifest-schema.md` | F4 — the third site carrying the unprefixed `pre-push-quality-gate` owning-step id |
| `marketplace/.../manage-execution-manifest/standards/decision-rules.md` | F5c — the third `order 61` restatement, in the bundle 300/G9 edits |
| `marketplace/.../plugin-doctor/references/rule-provenance.md` | F6b — its present-tense `choices=` claim is falsified by D4.3 |
| `test/plan-marshall/manage-config/test_cmd_ceremony_policy.py`, `.../test_manage_config_cli.py` | D4.3 consequence: both pinned the argparse exit-2 rejection D4.3 replaces. Re-pinned to `status: error` + the routed message |
| `test/plan-marshall/manage-config/test_finalize_steps_lane_rejection.py` (new) | D4.3's own contract test, plus the F6a replacement binding |
| `test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py` | D8 / 440-G2 consequence: it pinned the superseded "Re-fire (HEAD has advanced)" wording. Re-pinned to the deferral |
| `test/plan-marshall/manage-execution-manifest/test_manage_execution_manifest_validate.py`, `.../test_validate_loadable.py` | F5a/F5b — stale order annotations in the bundle 300/G8 edits |
| `test/plan-marshall/build-pyproject/test_gate_coverage_parity_substrate.py` (new) | D8 / 160-G2's substrate test. § Expected surface anticipates it as "a parity-cell substrate test for D8 / 160/G2" |
| `.claude/skills/finalize-step-plugin-doctor/SKILL.md` | § Expected surface lists it only as "D2.3 mutation target, restored". It additionally carries a real **D7.1** edit — `reads: [worktree]` — which the surface list did not anticipate |

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
| _pending_ | | | |

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
