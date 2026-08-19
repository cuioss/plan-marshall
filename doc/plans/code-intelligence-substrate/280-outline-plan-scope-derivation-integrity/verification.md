# Verification — 280-outline-plan-scope-derivation-integrity

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory before this audit)
**Tree state:** `2d5da71` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** PR [#1283](https://github.com/cuioss/plan-marshall/pull/1283), squash-merged as `aeab5ab`
**Overall verdict:** CONFIRMED WITH GAPS

The shipped code does what the plan's arm B asked for, and the two central mechanisms — the
published `worktree_state` discriminator and write-set-derived classification — are real, correct on
every input I exercised, and covered by tests that go red when the production code is mutated. The
gaps are: an incompletely discharged D5 population rule (two stub sites in the swept corpus that were
never converted and never declared as exclusions), **six** stale documentation surfaces the run's own
beyond-diff sweep should have caught, one regression test that has since stopped discriminating the
defect it names, and four inaccurate counts/omissions in the run report.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | Gate: confirm each defect at HEAD, record the split | 8 claims adjudicated; 6 confirmed, 1 closed-at-HEAD, 1 "NOT SITED"; arms A/B enumerated; request-classification → arm B | Arms enumerated in the report and mirrored in the successor spec; the closed item (change-type composition) verified independently closed by #1221, which predates this run; claim 8 carries no verdict | **PARTIAL** — D0's *Done when* says "each defect carries a confirmed/refuted verdict"; one does not. Disclosed, and closed later by plan 350 |
| D1 | Derive bucket / module / change type from the write-set | Bucket clause done; change-type clause "dropped — closed at HEAD"; prose clause done; `module` explicitly not changed | `deliverable_write_set`, `extract_declared_bucket`, `_check_declared_bucket`, prose-in-haystack all present and exercised; `module` derivation unchanged; bucket adjudicated in one direction only | **PARTIAL** — two of three headline fields delivered, the third disclosed as not-defective-at-HEAD; the bucket clause is half-adjudicated by design |
| D2 | Outline completeness is CLOSURE, not existence | Not addressed; implicitly arm A | Not in the #1283 diff. Delivered later by plan 350 (#1295) as its D1–D3 | **N/A (arm A)** — contract-conformant under the mandated split, but report-01 never says where D2 went |
| D3 | A closure claim is a hint, never a licence | Not addressed anywhere in the report | Not in the #1283 diff. Delivered later by plan 350 as its D4 | **N/A (arm A)** — same; the report's silence is a traceability defect, not a scope breach |
| D4 | Pre-flight integrity for the derivation order | Clause 1 done; clause 2 "partially done, narrowed deliberately", reverted with measured evidence | Clause 1 fully delivered and correct across all six consumer sites; clause 2 not delivered — a `disabled` plan's footprint is still reported permanently unresolvable | **PARTIAL** — disclosed, deferred to arm A, and arm A did not scope it either |
| D5 | Tests, each red pre-fix + population-derived characterization corpus | Three new suites; "Every stub SITE is covered"; exclusion table with four rows | Suites exist and are non-vacuous (mutation-proven, below). The corpus claim is **false**: two stub sites in the swept population still return the retired boolean and appear in no exclusion row | **PARTIAL** — the test half holds, the population rule does not |

## Per-deliverable detail

### D0 — the gate

- **Required (plan):** *"each defect carries a confirmed/refuted verdict and the two arms are
  enumerated."* The split is pre-decided; D0 records the cut and drops what already shipped.
- **Claimed (report):** eight rows, six CONFIRMED, one CLOSED-at-HEAD, one NOT SITED; arm A handed to
  `350-outline-derived-set-closure-integrity`; the request-classification material explicitly to arm B.
- **Found:**
  - The arms are enumerated in report-01 § The cut and are mirrored in
    `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/plan.md:96-127`,
    whose D1–D4 are exactly 280's D2 and D3.
  - Row 5 ("change type taken from the first deliverable — CLOSED at HEAD") independently verified:
    `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:1854`
    returns `change_type_scope_conflict`, and it landed in `6f7f9c7` (#1221), which
    `git merge-base --is-ancestor 6f7f9c7 aeab5ab~1` confirms predates this run. The "expect closed
    items" warning was honoured, not asserted.
  - Row 2's consumer list ("named rather than counted") re-derived: exactly six production call sites
    read `has_worktree`/`worktree_state` —
    `manage-execution-manifest.py:684`, `integrate_into_main.py:174`, `_cmd_baseline_reconcile.py:89`,
    `_cmd_force_push.py:69`, `git-workflow.py:1013`, `_references_core.py:210`. The report's own
    correction (F32: "seven" was a comment miscount) is accurate.
  - Row 8 ("the routing decision's pre-override input is overwritten by its output") carries the
    verdict **NOT SITED** — neither confirmed nor refuted.
- **Checks run:** `git log`/`git merge-base` for the closed item; grep re-derivation of the
  `has_worktree` consumer set; read of 350's plan and report-01.
- **Verdict:** **PARTIAL.** Seven of eight defects carry a verdict; one does not, which is a literal
  miss on the *Done when*. It is disclosed as such and was subsequently sited by plan 350
  (`350/report-01.md:47`, `_cmd_planning_lane.cmd_scope_estimate_heuristic`), so the residue is now
  closed.

### D1 — derive the bucket, module and change type from the write-set

- **Required (plan):** *"each derived field is computed from the write-set, asserted by a fixture
  where intent and write-set disagree."* Three named clauses: a read-only reference must not flip a
  bucket; change type composed across deliverables; drift check reads the analysis prose.
- **Claimed (report):** clause 1 done via `deliverable_write_set` + `extract_declared_bucket` +
  `_check_declared_bucket` (one direction only, disclosed); clause 2 dropped as closed at HEAD;
  clause 3 done via a `number → prose` map folded into `_build_haystack`. `module` explicitly not
  changed.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py:456`
    — `deliverable_write_set`, `intent != read`, unmarked entry counted as a write, `mutation_scope`
    unioned in (the union arrived later, with plan 350).
  - `_plan_parsing.py:34` — `_BUCKET_COMMENT_PATTERN` anchored to `^\*\*Profiles:\*\*` (the F33 fix),
    `_plan_parsing.py:516` `extract_declared_bucket`, `_plan_parsing.py:284` carries `declared_bucket`
    onto the record.
  - `manage-solution-outline.py:206` `_check_declared_bucket`, called at `:340`; the `module_testing`
    check at `:327-337` reads the write-set with **no** non-empty guard (the F34 fix).
  - `_cmd_qgate_mechanical.py:125` `_load_deliverables` returns `(deliverables, prose_by_number,
    parseable)`; `:441` `_build_haystack` folds `prose` in at `:486-487`; `:523` passes it per
    deliverable. `phase-4-plan/SKILL.md:825` documents the prose in the haystack and points at the
    `_PLANNING_KEYWORDS` constant instead of inlining it (F12 + F36).
  - The one-direction reasoning is sound and I verified its premise in the aggregator itself: stage 1
    of `_classify_paths_via_extensions`
    (`manage-execution-manifest.py:290-301`) splits documentation paths out before any extension runs,
    and the collapse at `:394-415` yields `documentation_only` for an all-documentation role set. So
    "every write is documentation by suffix ⇒ the aggregator's bucket is `documentation_only`" is a
    fact about the shipped classifier, not an approximation.
  - `module` derivation is genuinely unchanged — no `module`-deriving code appears in the #1283 diff.
- **Checks run:** `pytest test/plan-marshall/manage-solution-outline/test_write_set_derived_classification.py`
  → 21 passed; mutation of the case-normalisation in `_check_declared_bucket` → 1 failed (below);
  mutation of the prose fold in `_build_haystack` → 2 failed (below); read of the aggregator's
  stages 1–4.
- **Verdict:** **PARTIAL.** The two clauses the run claims are delivered are delivered and correct.
  The `module` field named in the deliverable headline is not derived from anything and is disclosed
  as such. The bucket adjudication covers one of two directions, disclosed, with the un-decidable
  direction reasoned at the site.

### D2 — outline completeness is CLOSURE, not existence

- **Required (plan):** referrer/projection/claim-versus-index closure; run the declared sweep before
  freezing the write-set; detect `{declared scope wide, write-set narrow}` mechanically; assert
  `detector_population ⊇ fix_set_population` with a positive-population guard.
- **Claimed (report):** nothing — D2 is never mentioned. It falls under arm A by the cut table.
- **Found:** absent from `aeab5ab`. Present now via plan 350 (#1295):
  `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py` (added by
  `63943f5`), consumed at `_cmd_qgate_mechanical.py:674-675`, with the normative population line
  written out at `_cmd_qgate_mechanical.py:705-727`.
- **Verdict:** **N/A (arm A).** The plan mandated the split and said the shipped plan is one arm, so
  not shipping D2 is contract-conformant. The traceability defect is that report-01's Deliverables
  section carries no row saying so.

### D3 — a closure claim is a hint, never a licence

- **Required (plan):** *"a downstream re-check runs regardless of an upstream closure assertion,"*
  verified adversarially.
- **Claimed (report):** nothing. The string "D3" does not appear in report-01.
- **Found:** absent from `aeab5ab`; delivered by plan 350 as its D4
  (`350/report-01.md:162-174`), and visible now in the `_cmd_qgate_mechanical.py:32-38` module
  docstring — the closure checks sit in the unconditional Step 8 script, which the surgical-scope
  bypass cannot reach.
- **Verdict:** **N/A (arm A).** Same disposition and same traceability defect as D2.

### D4 — pre-flight integrity for the derivation order

- **Required (plan):** *"the consumer branches on the discriminator, and a footprint-derived
  precondition is evaluated at planning time rather than at finalize."*
- **Claimed (report):** clause 1 done — `derive_worktree_state` is the single owner, the producer
  publishes from it, the parser fails closed, `PlanContext` gains `worktree_state`, `has_worktree`
  means "materialized". Clause 2 "partially done, and narrowed deliberately": the widening was
  implemented, measured, and reverted for two reasons (a droppable finalize step; non-hermeticity).
- **Found — clause 1, all confirmed:**
  - `file_ops.py:709` `derive_worktree_state`, the closed vocabulary at `:676-682`.
  - `file_ops.py:685` `is_truthy_metadata`, used at `:747` (F24), with
    `_handshake_commands.py:70-81` delegating to it.
  - `file_ops.py:890` `_parse_get_worktree_path_output` returns the published discriminator and
    **raises** at `:949-956` on an absent or unrecognised state — fail-closed, not a guess.
  - `_status_query.py:560` — the producer derives its published state through the same function.
  - `file_ops.py:1029` `worktree_state`, `:1051` `has_worktree` (`== MATERIALIZED` only), `:1097`
    `_resolve_worktree_face` (materialized → persisted path, both other states → `cwd_checkout_root()`).
  - Six consumers carry it: `manage-execution-manifest.py:684`, `integrate_into_main.py:174`,
    `_cmd_baseline_reconcile.py:89` (branches on the *state*, not the boolean — the F4 fix),
    `_cmd_force_push.py:69`, `git-workflow.py:1013`, `_references_core.py:210`.
  - `manage-solution-outline.py:1108-1123` keeps only the genuine-failure degrade, with a comment
    stating it no longer covers the pre-materialization window — the "learned the lesson, not the
    example" requirement.
- **Found — clause 2, not delivered:** `extension_base.py:565-596` still returns `None` (footprint
  unresolvable) for both `pending` and `disabled`, with the non-derivation stated as a deliberate
  cross-cutting deferral in the docstring at `:588-596`. The mechanism the report cites for the
  revert is real: `manage-execution-manifest.py:736-789` drops `pre-push-quality-gate` on a
  `not_necessary` verdict and only on that verdict.
- **Checks run:** mutation of `has_worktree` to `!= WORKTREE_STATE_DISABLED` →
  `test_plan_context_resolver.py` went red on 2 cases (below); reads of all six consumer sites.
- **Verdict:** **PARTIAL.** Clause 1 is complete and correct. Clause 2's literal *Done when* is not
  met; the shortfall is disclosed with measured evidence and handed to arm A, which recorded it as
  **not scoped** (`350/actual-state.md:130`), so it is still open.

### D5 — tests

- **Required (plan):** every test verified to fail pre-fix, **plus** a characterization-corpus rule:
  the corpus is population-derived from the live corpus directory, every fixture enumerated, every
  **exclusion** justified explicitly. *"An unstated exclusion is indistinguishable from an
  endorsement of the behaviour on the excluded case."*
- **Claimed (report):** three new suites; corpus enumerated by
  `grep -rn "_query_worktree_path\|_parse_get_worktree_path_output" test/ --include=*.py`;
  "**Every stub SITE is covered**, and the coverage is structural rather than per-file"; a
  four-row exclusion table.
- **Found — the suites:** all three exist and are non-vacuous under mutation (see § Test adequacy):
  - `test/plan-marshall/tools-file-ops/test_worktree_state_discriminator.py` (233 lines; the
    11-case coercion parametrization F24 names is at `:104-137`; the F25 fix — each state paired
    with the path the producer actually publishes — is at `:168-189`).
  - `test/plan-marshall/manage-solution-outline/test_write_set_derived_classification.py` (21 cases).
  - `test/plan-marshall/manage-tasks/test_qgate_keyword_drift_reads_prose.py` (5 cases).
- **Found — the corpus, re-derived by me at this HEAD:** the same sweep returns 25 files across
  exactly the 13 bundles plus `test/_shared` the report names — that enumeration is accurate. The
  shared derivation helper is real: `test/_shared/_resolve_project_dir_fixtures.py:73`
  `worktree_query_result` routes every stub through the production `derive_worktree_state`.
- **Found — the corpus claim is false.** Two stub sites still hand the seam the retired boolean:
  - `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:166` (an **autouse**
    fixture, so all 17 tests in the module run through it):
    `lambda _plan_id: (True, str(Path.cwd()))`
  - `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:563`:
    `lambda _plan_id: (True, str(PROJECT_ROOT))`

  Both appear in the swept population, in a bundle (`manage-tasks`) the report's own population list
  names, and in **no** exclusion row. `git show aeab5ab:test/.../test_freshness_notation_crosscheck.py`
  confirms both were present, unchanged, at the merge commit — the file landed on `main` in `e2b6665`
  (#1279) at 19:29 UTC, before #1283 merged at 20:05 UTC. This is the identical shape as F20, two
  more instances, undetected.
- **Verdict:** **PARTIAL.** The red-before-green half holds. The population rule — the half D5 exists
  to enforce — is not discharged: the sweep found these sites, the write-up did not account for them,
  and the report's coverage sentence asserts the opposite.

## Correctness review

I read the whole of `derive_worktree_state` / `is_truthy_metadata` /
`_parse_get_worktree_path_output` / `PlanContext`, all six worktree consumers,
`_check_declared_bucket` / `_write_set_is_all_documentation` / `deliverable_write_set` /
`extract_declared_bucket`, and `_load_deliverables` / `_build_haystack` / `_check_keyword_drift`,
looking specifically for fail-open branches, guards that cannot fire, unguarded `None`, and
order-dependence.

**No behavioural defect was found in the shipped production code.** Specifically checked and clean:

- **Fail-closed where the plan demands it.** `_parse_get_worktree_path_output` raises on an absent or
  unrecognised `worktree_state` (`file_ops.py:949`) rather than reconstructing it from the primitives
  riding alongside — the re-derivation the plan exists to remove. Verified by
  `test_absent_state_fails_closed` / `test_unrecognised_state_fails_closed`.
- **Both ends of the pair guarded** (`file_ops.py:741-752`): the flag through `is_truthy_metadata`
  (so the string `'false'` is not True), the path `.strip()`ped before it is tested (so `'   '` is
  not a working-tree root). I confirmed the asymmetry F24 names is gone by reading both branches.
- **`has_worktree` cannot silently widen.** `worktree_state == MATERIALIZED` only; the sentinel
  short-circuits to `disabled` before any shell-out (`file_ops.py:1047-1049`).
- **`_check_declared_bucket` cannot fire on the un-decidable direction.** `declared == documentation_only`
  returns early (`manage-solution-outline.py:246-247`) before the documentation predicate runs, so the
  three shapes F21 named (infra-config-only, docs+infra-config, template-rendering-to-docs) cannot
  reach the error path. Its stated premise is true of the shipped aggregator (verified against
  `manage-execution-manifest.py:290-415`).
- **The `module_testing` check has no non-empty guard** (`manage-solution-outline.py:328`), so the
  wholly-`(read)` deliverable — the sharpest case — is reported. F34's fix is present, not just
  described.
- **`deliverable_write_set` is `None`-safe**: non-dict entries skipped, non-string paths skipped,
  dedup by `seen` (`_plan_parsing.py:501-513`).

Two things are worth naming even though neither is a live defect:

1. **A documented fail-open with no signal.** `_write_set_is_all_documentation`
   (`manage-solution-outline.py:184-203`) returns `None` on `ImportError` and the caller treats that
   as "no contradiction" (`:248-249`), so the whole bucket check disappears silently. In practice the
   import resolves — the executor puts every skill's `scripts/` dir on `PYTHONPATH`
   (`generate_executor.py:1247`, `collect_script_dirs`), and the test suite reaches the error path
   for real — so the branch is currently unreachable. Recorded as G11.
2. **One half of a documented normative rule is unimplemented.**
   `phase-3-outline/standards/outline-workflow-detail.md:315` states *"A missing or wrong bucket
   comment is a Q-Gate finding."* This plan implemented the *wrong* half (in one direction). A
   **missing** `<!-- bucket: -->` comment is still reported by nobody: `_check_declared_bucket`
   returns `[]` when `declared` is falsy, and no other consumer of `declared_bucket` exists. Recorded
   as G10; this is pre-existing rather than introduced.

## Documentation-surface sweep

The run's own beyond-diff sweep (F5–F12, F26–F30, F37) set out to remove every rationale the
discriminator change made false. Six survive it. They are listed here so each gaps entry traces to a
row in this document rather than only to the summary paragraph.

| # | Surface | Retired claim it still makes | Gap |
|---|---|---|---|
| 1 | `manage-solution-outline.py:947-949` (`_stamp_read_provenance` docstring) | the `get-module-context` degrade covers the pre-materialization window | **G4** |
| 2 | `manage-solution-outline/SKILL.md:245` (+ the field table at `:242`) | the `worktree_fallback` exists *because* a `pending` plan has no worktree yet | **G5** |
| 3 | `manage-config/SKILL.md:511` | `decision: unknown` because "the worktree is not yet materialised" | **G13** |
| 4 | `manage-config/scripts/_cmd_build_map.py:144` | same claim, in the docstring of the handler row 3 documents | **G13** |
| 5 | `manage-execution-manifest/standards/decision-rules.md:237` | `_resolve_footprint` returns `None` "(the worktree is not yet materialised)" | **G13** |
| 6 | `phase-6-finalize/standards/finalize-step-security-audit.md:38` | "An UNRESOLVABLE footprint (the worktree not yet materialised)" | **G13** |

Rows 1–2 contradict a comment or a test in the same change: `manage-solution-outline.py:1109-1123`
states the opposite of row 1, and `test_get_module_context.py:517` asserts
`data['worktree_fallback'] is False` for `worktree_state: pending`, agreeing with the comment and not
with the docstring.

Rows 3–6 are the `disabled`-plan half of the same conflation. Each explains an unresolvable footprint
by pre-materialization alone, which is false for a plan that will never have a worktree — the exact
wrongness F5 recorded and fixed in the reason string, and which
`extension_base.py:579-581` names in so many words: *"a statement that is not merely unhelpful for such
a plan but false, since no worktree will ever be materialised for it."*

⛔ **Row 3 is inside a file this run edited.** `git show aeab5ab -- .../manage-config/SKILL.md` changes
exactly two lines — the reason string at `:548` and the `unknown` explanation at `:1429`, which now
reads *"whether because the plan's worktree is `pending` … or `disabled` (it never will)"*. The run
corrected one statement of the claim and left the other, nine hundred lines above it, contradicting the
correction in the same file.

**Population of this sweep, published.** The set was derived mechanically over every `*.md` and `*.py`
under `marketplace/`: lines matching `not yet materiali[sz]ed|not materiali[sz]ed yet|worktree is not
yet`, restricted to those within three lines of `unresolvab|decision: unknown|returns ``None``|
`unknown``. That returns six candidates. `extension_base.py:579` is excluded because it quotes the
retired string in order to reject it, and
`workflow-integration-git/SKILL.md:655` because it is a `--branch`-omitted `INVALID_INPUT` row in an
unrelated context. Rows 1–2 do not use that phrasing and were found by reading the two
`worktree_fallback` surfaces directly; a zero from the phrase sweep would therefore not have been
evidence of a clean tree, which is why both methods were run.

## Test adequacy

Coverage mapping:

| Deliverable | Covering tests |
|---|---|
| D1 bucket / write-set | `test_write_set_derived_classification.py` (21 cases, incl. the three non-provable shapes from F21 and the F23 case-insensitivity regression) |
| D1 prose haystack | `test_qgate_keyword_drift_reads_prose.py` (5 cases, incl. the paired negative) |
| D4 discriminator | `test_worktree_state_discriminator.py` (state machine + payload reader), `test_plan_context_resolver.py` (per-state faces), plus per-consumer suites |
| D5 corpus | `test/_shared/_resolve_project_dir_fixtures.py` derivation helper |

**Mutation evidence — every mutation was taken from a byte snapshot (`$TMPDIR/verify-280-mutsweep/`
for the first audit, `$TMPDIR/adv-280-mutsweep/` for the adversarial re-run) and written back from that
snapshot; `git status --porcelain` was confirmed empty for each mutated file afterwards, and for the
whole tree at the end of each pass. No `git checkout`/`restore`/`stash` was used at any point.**

M1–M4 were run by the first audit and **re-run independently** during adversarial review, from a fresh
byte snapshot, with identical results. M5–M10 are additional mutations the first audit did not run;
they exist to answer "can each guard this plan shipped go red at all?" rather than to re-check a
result. Each targets a different shipped guard, so a green row would name a guard with no test behind it.

| # | Mutation | Result |
|---|---|---|
| M1 | `_build_haystack`: delete the `if prose: parts.append(prose)` fold | **RED** — 2 failed (`test_prose_text_reaches_the_haystack`, `test_keyword_present_only_in_prose_is_not_flagged`, the latter reporting `assert 2 == 0` drift findings, exactly the pre-fix number the report records) |
| M2 | `_load_deliverables`: empty-deliverables branch (`_cmd_qgate_mechanical.py:166`) returns `True` instead of `False` | **GREEN — 5 passed**, and on re-run the *whole* `test/plan-marshall/manage-tasks/` suite is green too: **496 passed**. No test in the owning bundle discriminates the F35 defect (see below) |
| M3 | `_check_declared_bucket`: drop `.lower()` from the comparison | **RED** — 1 failed (`test_bucket_comparison_is_case_insensitive`) |
| M4 | `has_worktree`: `!= WORKTREE_STATE_DISABLED` instead of `== WORKTREE_STATE_MATERIALIZED` | **RED** — 2 failed (`test_each_state_resolves_its_own_face[pending]`, `test_has_worktree_is_false_while_pending`) |
| M5 | restore the F34 guard: `if 'module_testing' in profiles and write_set:` | **RED** — 1 failed (`test_wholly_read_only_deliverable_does_not_satisfy_module_testing`) |
| M6 | `is_truthy_metadata` → bare `return bool(value)` (the F24 defect) | **RED** — 2 failed (`test_the_flag_is_coerced_not_merely_truth_tested[str-false]`, `[str-False]`) |
| M7 | `_parse_get_worktree_path_output`: disable the unrecognised-state raise (`if False:`) | **RED** — 2 failed (`test_absent_state_fails_closed`, `test_unrecognised_state_fails_closed`) — the fail-closed branch is reachable and pinned |
| M8 | test-side: replace the `test_freshness_notation_crosscheck.py:166` autouse stub with `('materialized', '/nonexistent/xyz')` | **GREEN — 17 passed**, confirming the first audit's basis for treating G1/G2 as latent |
| M9 | `_write_set_is_all_documentation`: `all(...)` → `any(...)` | **RED** — 1 failed (`test_the_same_bucket_over_a_code_write_is_not_rejected`) — the F21 narrowing is guarded |
| M10 | `_check_declared_bucket`: delete the `declared == documentation_only` early return | **RED** — 2 failed (`test_read_only_code_reference_does_not_flip_a_docs_only_bucket`, `test_bucket_comparison_is_case_insensitive`) |

Also applied and reverted: the exact fix G1/G2 propose (`worktree_query_result(True, …)` at both sites
plus the import) — **17 passed**, so the proposed action is executable as written and its stated risk
("none expected") holds.

**Both branches of every shipped guard were checked for reachability.** `derive_worktree_state`'s four
returns, `_parse_get_worktree_path_output`'s two raises, `_resolve_worktree_face`'s
materialized/other split plus its self-contradictory-payload raise (reachable through the subprocess
boundary, since the parser validates the state and the path independently — pinned by
`test_materialized_with_empty_path_raises` at `test_plan_context_resolver.py:163`), `has_worktree`'s
single comparison, and `_check_declared_bucket`'s four exits. Exactly one branch is unreachable in
practice — the `ImportError` arm of `_write_set_is_all_documentation` — and it is recorded as **G11**.

**M2 is a finding.** `test_heading_less_deliverables_section_is_unparseable`
(`test_qgate_keyword_drift_reads_prose.py:147`) asserts `result['ambiguous'] is True` for a
heading-less Deliverables section. At the merge commit that assertion was carried by `parseable`
alone — `git show aeab5ab:.../_cmd_qgate_mechanical.py` line 653 reads `ambiguous = not parseable`.
Plan 350 (#1295) widened it to `ambiguous = not parseable or not population_complete`
(`_cmd_qgate_mechanical.py:728`), and the fixture's task references a deliverable the outline does not
have, so the closure population is incomplete and `ambiguous` is True regardless. The test now passes
against the exact pre-fix implementation it was written to pin. Recorded as G6 (attributable to
#1295, observable now).

**Two stub sites are the retired shape.** I proved the discarded-value mechanics directly rather than
by argument, per the contract amendment this run itself proposed:

```
$ uv run python -c "... file_ops._query_worktree_path = lambda pid: (True, '/tmp/some-worktree') ..."
worktree_state = True
has_worktree   = False
worktree_path  = /home/user/plan-marshall     # cwd_checkout_root(), not the stub's path
```

A `(True, path)` stub therefore routes its consumer to the checkout root and reports
`has_worktree=False` — the F20 mechanics exactly. I then replaced the autouse stub at
`test_freshness_notation_crosscheck.py:166` with `('materialized', '/nonexistent/xyz')` and re-ran:
**17 passed**, so the stubbed path is not load-bearing for these particular tests today (the sha
computation is separately stubbed). The defect is therefore latent rather than active: the tests are
green either way, and would keep being green while silently exercising the wrong branch the moment a
consumer starts branching on `worktree_state`. Recorded as G1/G2 at low severity for that reason.

## Report accuracy

Verified true (each re-derived, not copied):

- The arm cut, the arm-B assignment of the request-classification material, and the handover target.
- D0 row 5 (change-type composition already closed at HEAD) — closed by #1221, verified ancestor.
- D0 row 2's six named `has_worktree` consumers — exactly six exist.
- The corpus **enumeration** (13 bundles + `test/_shared`) — my sweep returns the same set.
- Every fix claimed for F1–F12, F14, F16–F18, F21–F30, F33–F37 that I spot-checked in the tree:
  `worktree-handling.md:67-79` names all three states with a `pending` row; `:274-277` distinguishes
  them and tells consumers when to branch on the state; `tools-file-ops/SKILL.md:147/151/157` names
  four faces and catalogues both new public functions; `plugin-doctor/references/rule-catalog.md:906`
  no longer justifies the gate with the retired rule; `resolve_project_dir.py:21-22` and `:102-109`
  name the three states and no longer list "missing worktree metadata" as a raise cause;
  `manage-config/SKILL.md:548` and `:1429` carry the re-synced `unknown` reason;
  `phase-4-plan/SKILL.md:825` points at `_PLANNING_KEYWORDS` instead of inlining it.
- Step 8 Bridge: `git show aeab5ab --name-status -- doc/plans` returns exactly three paths — the
  `R100` rename of this plan's own `plan.md`, `report-01.md`, and the arm-A successor spec. No status
  file, no ledger, no other plan's directory. Claim holds verbatim.
- Reviewer participation: GitHub confirms five inline review threads from `coderabbitai`, **all five
  resolved**, each carrying `✅ Addressed in commit 5d3673f`. The PR is merged
  (`merged_by: cuioss-oliver`, `merged_at: 2026-08-17T20:21:27Z`) from branch
  `claude/code-intelligence-substrate-scope-qgljp1` — the harness-assigned form the report says it kept.
- 44 changed files, +2455/−244 — matches the PR record exactly.

False, stale, or overstated:

1. **"Every stub SITE is covered, and the coverage is structural rather than per-file."**
   (§ The characterization corpus.) False at the merge commit and false now — two sites in
   `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` (lines 166 and 563) were
   in the swept population, were never converted, and appear in no exclusion row. The sentence
   immediately below it — *"'Site', not 'module', and the distinction cost two defects"* — is the
   correction the run made after F20, and it did not go far enough: the *same* module-level blind
   spot left two more sites behind in the *same* bundle. **G3.**
2. **"the diff changes production Python in six bundles plus eight test modules"** (§ Build gate).
   Re-derived from `aeab5ab`: production `*.py` changes land in **nine** skills (all inside the
   `plan-marshall` bundle) — `manage-execution-manifest`, `manage-references`,
   `manage-solution-outline`, `manage-status`, `manage-tasks`, `plan-marshall`, `script-shared`,
   `tools-file-ops`, `workflow-integration-git` — and **23** test modules changed, not eight. The
   plan's own claim-label table says *"Never carry a count forward … re-derive from the live tree at
   the moment of consumption."* **G7.**
3. **"Six commits, every one carrying the `Co-Authored-By: Claude` trailer"** (§ Contract check, row
   "4 Implement"). The PR carries **11** commits (`commits: 11` from the GitHub API; all 11 listed and
   all 11 do carry the trailer, so the trailer half of the claim holds). Six was correct when the row
   was written — four more commits landed afterwards and the row was never re-derived. **G8.**
4. **D2 and D3 have no disposition anywhere in the report.** The strings "D2" and "D3" do not appear
   in `report-01.md` at all. A reader of the report alone cannot tell whether they were dropped,
   deferred, or forgotten; only the successor spec reveals that they became 350's D1–D4. **G9.**
5. **"the tree now collects 20544 tests"** (§ Build gate) — not a defect. It is explicitly framed as
   re-derived at the moment of the claim. At this HEAD `pytest --collect-only` over `test/` reports
   **21084 collected**, consistent with the ~18 PRs merged since. Recorded so the drift is not
   mistaken for a discrepancy.
6. Ambiguous, not counted as a finding: § Reviewer participation says the Step 8 shortfall disclosure
   *"fired before auto-merge was armed, stating coverage as 2-of-3"*, while the commit that carried
   that disclosure (`15f1988`, 18:51 UTC) says *"Coverage is 1 of 3 and the report says 1 of 3."*
   CodeRabbit's review landed at 18:59 and the coverage rose to 2-of-3 before the merge at 20:21, so
   the final table is right; whether the disclosure the operator saw said 1-of-3 or 2-of-3 cannot be
   settled from the artifacts available to me. **UNVERIFIABLE.**

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| 1. Arm A of the split, handed to `350-outline-derived-set-closure-integrity` | **Closed** | `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/` exists with `plan.md`, `report-01.md`, `report-02.md`, `actual-state.md`; `_qgate_closure.py` landed in `63943f5` (#1295) |
| 2. A `disabled` plan's footprint is derivable but reported unresolvable | **Open** | `extension_base.py:565-596` still returns `None` for `disabled`; arm A explicitly recorded it **not scoped** at `350/actual-state.md:130` |
| 3. Claim 8 (routing decision's pre-override input) never sited | **Closed** | Sited by plan 350: `350/report-01.md:47` names `_cmd_planning_lane.cmd_scope_estimate_heuristic` and the `_read_scope_estimate` consumer |
| 4. Only one bucket contradiction is adjudicated | **Open, by design** | `manage-solution-outline.py:226-237` states the un-decidable converse and leaves it to the aggregator; `TestNonProvableShapesAreNotAdjudicated` pins the three shapes as accepted |
| 5. `_invariants._worktree_materialized` still derives from the primitive `worktree_path` | **Open** | `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py:429-447` — reads `metadata.get('worktree_path')` and the phase set, never `derive_worktree_state`. Consistent with the report's stated reason (it answers a phase-axis question), so this is open-as-declared rather than a regression |

The report's proposed contract amendment ("if the clause asserts what a function RETURNS, run the
function") was **not** self-approved and was said to ship separately. It did:
`8729db9 chore(cloud-plan-lane): carve out the Bash discipline; require running an asserted return (#1285)`.

## Out-of-scope and collateral

All three exclusions were respected:

- **The task-artifact emission defect** — nothing in the `aeab5ab` diff touches artifact emission;
  the only `manage-tasks` production file changed is `_cmd_qgate_mechanical.py`.
- **The plan-efficiency calibration table** — untouched; no `plan-retrospective` or metrics file
  appears in the diff.
- **Moving the worktree creation point** — untouched. The change reads state; no worktree is created,
  and `extension_base.py:588-596` explicitly declines to widen footprint derivation for that reason.

One collateral change that is declared rather than silent: F15 records a `for` loop in a single Bash
call, violating the repository's no-shell-constructs rule, "recorded, not undone". Under the
`doc/plans/` lane carve-out in `CLAUDE.md` that rule does not bind, so this is a self-reported
non-violation rather than a breach.

No file outside the plan's expected surface was changed without a finding row explaining it. The
`manage-tasks` and `manage-execution-manifest` surfaces, marked HYPOTHESIS in the plan, were both
reached and both are accounted for.

## Method and coverage

**What I did.** Read the epic README, `plan.md` and `report-01.md` in full. Located the merge commit
(`aeab5ab`) and read its diffstat and per-file diffs. Read every production symbol the report names,
at its site. Re-derived every count I state: the `has_worktree` consumer set, the characterization
corpus sweep, the production-skill and test-module counts in the diff, the whole-tree collection
count, the PR's commit count and review threads (GitHub MCP). Ran three test files. Performed four
production mutations plus one test-side mutation, each restored from a byte snapshot in
`$TMPDIR/verify-280-mutsweep/`, with `git status --porcelain` confirmed clean for each file
afterwards and for the whole working tree at the end.

**Guard against false negatives.** Every "grep found nothing" result was confirmed against a positive
control: the boolean-stub search that found the two `test_freshness_notation_crosscheck.py` sites was
run in the same shape that returns the twenty-plus converted `worktree_query_result` sites, so a zero
would have been distinguishable from a filter mistake.

**What I could not check.**

- The pre-fix red-before-green table (§ Verification, 5 of 18 cases). The PR was squash-merged and the
  branch commits are not in this clone, so I cannot re-run the suites against the pre-implementation
  tree. I substituted mutation testing against the shipped tree, which establishes the same property
  (the tests discriminate the defect) for three of the five named cases. **UNVERIFIABLE** for the two
  bucket-adjudication cases, whose pre-fix behaviour ("no bucket adjudication existed") is trivially
  true and unfalsifiable now.
- The verification sub-agent's "3005 passed" and the `./pw verify` figures (`20509 passed, 14 skipped`,
  `8:18`, mypy over 410/764 files). Point-in-time build output with no artifact in the tree.
  **UNVERIFIABLE**; not treated as findings.
- Whether the Step 8 shortfall disclosure the operator saw said 1-of-3 or 2-of-3 (see § Report
  accuracy item 6). **UNVERIFIABLE.**
- I did not run `./pw verify`; per the audit brief that is out of scope.
