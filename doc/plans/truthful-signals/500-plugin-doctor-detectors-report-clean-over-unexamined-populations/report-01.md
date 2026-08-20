# Run report — 500-plugin-doctor-detectors-report-clean-over-unexamined-populations (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/plugin-doctor-detectors-report-ar5emr`    **PR:** not yet opened    **Outcome:** in progress

> **Verification loop exit:** not yet reached — the loop is open at the time of writing.

**This report is written as the run proceeds and is finalized as the last
pre-merge commit** (contract § Step 8 condition 4). Every section below that
states a figure re-derives it at the moment of the claim; sections marked
*pending* are not yet established and are not to be read as established.

## Skills loaded

Read by bundle path (the plugin is not installed in this session):

| Skill | Route |
|---|---|
| `plan-marshall:ref-code-quality` | `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` |
| `pm-plugin-development:plugin-script-architecture` | bundle path |
| `pm-dev-python:python-core` | bundle path (Python production code) |
| `pm-dev-python:pytest-testing` | bundle path (Python tests) |

`pm-plugin-development:plugin-architecture` was **not** loaded: the change edits
analyzer scripts, references and tests, and adds no skill or bundle structure.
No skill was unobtainable by both routes.

## Deliverables

D1 is the plan's GATE. Its derivation succeeded, so D2–D8 were attempted.

| # | What was done | Commit | Verification state |
|---|---|---|---|
| D1 | Root-anchored anti-vacuity findings survive a scoped run. The population was **re-derived** from `_runner.py` rather than taken from the plan's trio: every rule routed through `scoped(...)` or `suppressed(...)` was enumerated, and each routed analyzer read for a finding anchored at the marketplace root. The derived set is exactly the three the plan named. The fix keys on the finding's **anchor** (`_finding_is_tree_wide`), not on a finding-type list, so a fourth such rule is covered without registration. | `1e66475` | 7 tests; mutation-confirmed (§ Mutation register) |
| D2 | Pin-trap oracle: empty content comparison unrepresentable as a pass; union denominator so a pin superset is a divergence; content counts in the volatile signature; `partial` reachable from the adapter; four-state executor anchor. | `4bab9f8` | 5 guards mutation-confirmed; `partial` seen RED first |
| D3 | Enum notation latch replaced with a per-line search; router-flag placement rule added against each subcommand's OWN flags; leading router flags skipped when locating the verb. | `8889526` | 4 mutants, each killed by the test that names it |
| D4 | Two vacuous tests replaced, each seen RED against the defect it names. | `decd27b` | red observed, both directions |
| D5 | Runner publishes each rule's examined population from the same derivation the findings came from; `analyze_shim_marker` wired into the analyze pass. | `1a4b64c` | 6 tests incl. real-tree clean-run assertion |
| D6 | Router-flag note built from the caller's own argv through the executor notation; CI front-ends name their router flags; fifth (mirror) recurrence signature. | `807c825` | 15 tests incl. the REAL CI parser |
| D7 | `loader_selected_version` reduced to the line it always evaluated, with an eligibility parameter; saturation re-ranked; shape-3 constant renamed and the literal tree pinned; remedy names invocable surfaces; paired observer added. | `f879130` | 57 tests |
| D8 | Brace-less enum form + declarative dict-spec authority + declared coverage; two new incident-reference narration families; mirror rule-pack completed; two retrospective docstrings; one report count. | `e4e3515` | see § Findings |
| — | Round-1 fixes from the cold read and the plan's own coverage check. | `b3786f6` | see § Findings |

### Mutation register

Every new or changed guard, the mutation applied to it, and the observed red —
including the guards added by the verification rounds, which an earlier draft of
this table omitted while still claiming to cover every one. Rows are labelled
`R2`–`R6` by the round that introduced the guard; unlabelled rows are the
original deliverable pass. Each mutation is NARROW by construction: a mutation
that reddens most of the file is not evidence that the guard is pinned, only
that the module still has to import, and two coarse first attempts were
discarded on exactly that ground.

⚠️ **A row here is evidence only that SOME test reddened.** Round 5 shipped a
guard whose row could not be written, because no mutation of it reddened
anything — the guard was inert (RZ-9). A guard with no row is therefore the
signal to check, and the completeness claim above is checked against the round's
new tests rather than asserted: rounds 5, 6 and 7 added ten tests between them and
every one that pins a guard appears below.
D4's *Done when* requires the run to name the mutation used to see each guard
red; D2's 320/G2 additionally requires the red to have been observed **before**
the adapter change landed. Each mutation snapshotted the target's exact bytes to
`$TMPDIR/author-*-mutsweep/` and restored them in a `finally`, with
`git status --porcelain` re-checked clean afterwards. No `git checkout`,
`git restore` or `git stash` was used to undo a mutation — each of those rewrites
the working tree from the index and would have discarded the run's own uncommitted
work along with the mutant.

| Guard | Mutation applied | Observed |
|---|---|---|
| D1 — root-anchor bypass | drop `or _finding_is_tree_wide(f, marketplace_root)` from `_scoped` | 3 failed / 4 passed — all three empty-population guards red |
| D2 — 320/G2 partial scan | **none — red observed FIRST**, against the unmodified adapter | `assert cc.partial is True` → `False`, on `ContentComparison(matched=1, total=2, diverged=1, scanned=2)`: the adapter counted the unreadable source file into `scanned`, so `partial` was unreachable |
| D2 — 320/G1 usable gate | delete the `elif not content.usable:` arm | `test_zero_file_content_comparison_is_indeterminate_not_pass` |
| D2 — 320/G8 union denominator | `union = sorted(source_rels)` (source side only) | `test_pin_superset_of_source_is_a_divergence` |
| D2 — 320/G3 volatile signature | replace the content signature with `None` | `test_samples_differing_only_in_content_are_indeterminate` |
| D2 — 320/G7 split divergence | delete the `EXECUTOR_SPLIT` divergence append | `test_version_split_executor_fails_naming_the_conflicting_versions` |
| D2 — 320/G2 unscanned accounting | `scanned=total` instead of `total - unscanned` | `test_compare_pin_content_partial_scan_when_a_source_file_is_unreadable` |
| D3 — 100/G10 notation latch | restore `if block_notation is None:` | all four shared-fence tests, **including the real-tree one** |
| D3 — 060/G6 placement scope | judge against `entry.subcommands` (the widened union) | `test_router_flag_after_the_verb_is_reported_as_misplaced` |
| D3 — 060/G6 post-verb scan | scan `inv.all_flag_text` instead of `inv.rest` | 2 tests, incl. the correct-spelling control |
| D3 — 060/G7 leading-flag skip | `r'(?P<leading>)'` (empty group) | 2 tests, incl. the same-verb equivalence |
| D4 — 130/G5 backtick exemption | delete the `_offset_in_inline_code` skip | `test_backticked_inline_code_ref_is_exempt` (+3 others) |
| D3 — R2 declarative path derivation | derive the modelled-path set from `_declarative_authority`'s keys instead of `_walk_declarative_specs` | `test_a_dict_spec_subcommand_with_no_choices_is_not_a_blind_spot`, `test_a_nameless_dict_spec_contributes_no_modelled_path` |
| D3 — R3 brace-less member class | admit `]` into the member class (`[A-Za-z0-9_.\-\]]+`) | `test_optional_argument_brackets_are_not_swallowed_into_a_member` |
| D3 — R4 shadowed-receiver skip | replace `if receiver in shadowed.get(id(node), ())` with `if False` | `test_a_parser_rebound_by_a_helper_parameter_is_not_attributed_to_the_root` |
| D3 — R4 mutually-exclusive group inheritance | drop `add_mutually_exclusive_group` from `_PARSER_GROUP_FACTORIES` | `test_choices_on_a_mutually_exclusive_group_resolve`, `test_a_group_built_off_a_shadowed_parser_is_not_attributed_to_the_root` |
| D8 — R3 exemption offset | test the exemption at `m.start()` instead of `_exemption_offset(m)` | `test_reversed_term_of_art_with_a_backticked_ref_stays_exempt`, `test_observed_on_with_a_backticked_ref_is_exempt`, `test_real_marketplace_has_zero_findings` |
| D8 — R3 reversed term-of-art family | delete the family from `_PATTERNS` | `test_reversed_term_of_art_fires` (+3 others, incl. both family-count tests) |
| D8 — R3 dated-narration family | delete the family from `_PATTERNS` | `test_dated_narration_fires`, `test_version_pinned_narration_fires` |
| D3 — R5 argument-group inheritance | drop `add_argument_group` from `_PARSER_GROUP_FACTORIES` | `test_choices_on_an_argument_group_resolve` |
| D3 — R5 scope gate on group inheritance | drop `and owner not in scope_params[id(stmt)]` | `test_a_group_built_off_a_shadowed_parser_is_not_attributed_to_the_root` |
| D3 — R5 laundered group vars | drop `\| laundering` from `_shadowed_receivers`'s returned sets | `test_a_group_built_off_a_shadowed_parser_is_not_attributed_to_the_root` |
| D3 — R5 two-member minimum *(superseded)* | restore `if not members` in place of `if len(members) < 2` | `test_a_one_member_brace_group_is_a_template_slot_not_an_enum` — **neither the mutation target nor this test exists at HEAD.** Round 6 (RZ-10) replaced the collection-time drop with the `single_member_ambiguous` cause and renamed the test; the row is kept, marked, because the register is a record of reds observed, and silently deleting it would hide that a guard was replaced rather than removed. The live guard is the R6 row below. |
| D3 — R5 incomplete-authority paths | `return set()` at the head of `_paths_with_incomplete_authority` | `test_a_parser_handed_to_an_unmodelled_call_makes_that_path_incomplete` |
| D3 — R6 single-member cause | `if False:` in place of `if len(documented) < 2:` (drop at collection again) | `test_a_one_member_group_is_counted_as_ambiguous_not_dropped`, `test_a_truncated_one_member_enum_is_a_declared_gap_not_a_clean_pass` |
| D3 — R6 single-member counted as a blind spot | drop `UNRESOLVED_SINGLE_MEMBER` from `UNRESOLVED_BLIND_SPOT_CAUSES` | the two above, plus `test_real_tree_blind_spot_count_is_published_and_dominated_by_underived_parsers` |
| D3 — R6 laundering scope | return bare group names (`{group for group, _owner in laundering}`) | `test_a_laundered_group_name_does_not_poison_the_same_name_elsewhere` |
| D3 — R6 receiver-position control | `return set()` at the head of `_paths_with_incomplete_authority` | `test_a_parser_in_receiver_position_does_not_make_a_path_incomplete` — the replacement for the inert control of RZ-9, which this same mutation did NOT redden |
| D3 — R7 laundering scope (binding) | key laundering by name only (`{group for group, _func in laundering}`) | `test_a_laundered_group_name_does_not_poison_the_same_name_elsewhere` |
| D3 — R7 mixed-form conflict | delete the conflict branch so a re-declaration overwrites | `test_a_script_mixing_both_declaration_forms_with_different_sets_fails_closed` |
| D5 — R7 clean-run population | drop `enum_population` from the runner's `emit` for this rule | `test_population_publishing_rules_report_their_size_on_a_clean_tree` |

**Independently reproduced.** The round-1 verifier re-ran the D4 and D3 mutations
from its own snapshot directory and confirmed both reds, so these are not this
run's own unchecked claim.

### Characterised survivors (condition B)

Behavioural findings deliberately left open. Condition B admits a survivor only
with a proof it cannot occur or a stated bound plus a promise; each is recorded
here with which one it has. None of these changes a test's meaning or a
deliverable's verdict, which condition B forbids leaving open on any terms.

⚠️ These three were raised by round 5 and had **no recorded disposition at all**
until round 6 counted the round record's arithmetic against the Findings table
(RZ-17). The round-5 verifier had classified them as acceptable survivors in its
own verdict; the run simply never wrote them down. An unrecorded survivor is
indistinguishable from an ignored finding, which is the whole point of the
condition.

| Id | Finding | Why it survives |
|---|---|---|
| R5-4 | `_shadowed_receivers` does not model a LOCAL rebind — `def _extra(target): parser = target; parser.add_argument(..., choices=...)` attributes the helper's choices to whatever `parser` resolves to module-wide. | **Bound.** The docstring's stated scope is *parameters*, so no statement in the tree is false because of it. **Zero live instances** — verified over the whole marketplace. The promise: it is the same defect class as RZ-11's laundering and would be closed the same way, by treating a name assigned FROM a shadowed name as shadowed. |
| R5-7 | The same walk does not model `lambda`, comprehension, `for` or `with` bindings. | **Bound.** Outside the docstring's stated scope; zero live instances for all four shapes. Same promise as R5-4 — one binding-aware walk closes the family. |
| R5-8 | `_shadowed_receivers` walks the tree twice per notation (106 calls over 53 notations). | **Proof of no correctness effect**: the function is pure and both callers pass the same `tree`, so the second walk cannot return anything different. Cost measured, not asserted: 1.30 s → 1.44 s over the whole marketplace. |
| RZ-9 (residual) | A parser passed by argument INSIDE a container — argparse's `parents=[base]` — does not reach the incomplete-authority scan, and a `parents=`-built child inherits actions this walk attributes to the parent's paths only. | **Bound.** Zero live sites use `parents=`. Named in `_paths_with_incomplete_authority`'s docstring as an unclosed gap rather than left implied-covered. The promise: closing it means walking container literals in argument position and attributing inherited actions to the child's paths. |

### Collateral outside the plan's Expected surface

The plan's claim-labels row makes recording this the run's obligation: *"a file
touched and not listed is collateral change to be justified in the report"*.

Derived from `git diff --name-only origin/main...HEAD` against the plan's
Expected surface, not from the round record. Two files were missing for five
rounds because the table was maintained finding-by-finding, which records what a
round NOTICED rather than what the branch TOUCHED.

| File | Why | Justification |
|---|---|---|
| `plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` | D6 / 060/G3 | The parse call had to move from `parse_args_with_toon_errors` to `parse_ci_args` for the router-flag note to reach the CI surface at all. The plan's Expected surface names `ci_base.py` as the D6 hand-off point but not the two front-ends that call it; the change is one line plus its import. |
| `plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py` | D6 / 060/G3 | Same, for the other provider. Leaving it would have made the note fire on GitHub and not GitLab — a per-provider inconsistency in a shared contract. |
| `doc/plans/truthful-signals/320-…/report-01.md` | 320/G5 | See CC-2: the gap names this surface, and its claim was false. Condition A admits no deferral. |
| `test/…/plugin-doctor/_plugin_doctor_fixtures.py` | RF-6 | The zero-match coverage guard requires a firing fixture for every registered rule; the new rule had none. Inside the directory the plan calls "a lead". |
| `test/…/plugin-doctor/test_quality_gate_root_anchored_findings.py` | D1 | New file, inside the same lead directory. |
| `plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` | RV-4 / 060/G2 | The plan's Expected surface names only that skill's `standards/agent-behavior-rules.md`, but the always-loaded floor in `SKILL.md` restates the signature count and enumerates the signatures, so adding one there left the floor false. Found by round-2 verification, not by the plan. |
| `pm-plugin-development/skills/recipe-fix-argparse-rejection/SKILL.md` | RW-4 / 060/G2 | Same claim, three more sites in a recipe that explicitly forwards to the signature list. Not in the Expected surface; the plan did not anticipate that the count is restated outside the owning document. |
| `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py` | RW-4 / 060/G6 | Carried the retired argparse claim three times. Not in the Expected surface; D3 corrected the claim only where the plan pointed. |
| `test/plan-marshall/tools-script-executor/test_execute_script.py` | RW-4 / 060/G6 | Same claim, stating a test's meaning. Not in the Expected surface. |
| `plan-marshall/skills/script-shared/scripts/argparse_surface.py` | RX-4 / 060/G6 | The retired argparse claim, third round of sweeping. Not in the Expected surface. |
| `plan-marshall/skills/tools-script-executor/SKILL.md` | RX-4 / 060/G6 | Same claim; this file contradicted itself 156 lines later. Not in the Expected surface. |
| `test/plan-marshall/tools-script-executor/test_dispatch_boundary_error.py` | RX-4 / 060/G6 | Same claim in a test docstring. Not in the Expected surface. |
| `plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` | RY-4 / 060/G6 | The SOURCE template that generates every executor — the claim's fourth surviving site, found in round 4. Not in the Expected surface, and the plan could not have anticipated it: the claim's reach was only established by sweeping for it four times. |
| `pm-plugin-development/skills/recipe-fix-argparse-rejection/SKILL.md` | RY-5 / 060/G2 | Two further restatements of the signature list, contradicting that file's own rule. |
| `test/…/plugin-doctor/test_analyze_manage_invocation.py` | RÅ-8 / 060/G6 | The retired argparse claim in a test docstring, in the same lead directory as two files already listed here. Missed by this table for five rounds while its own directory's siblings were recorded — found by round 7 diffing the branch against `origin/main` rather than reading the rounds. |
| `doc/plans/truthful-signals/060-…/report-01.md` | RÅ-8 / 060/G2 | Edited for the coverage check (§ Coverage check records why): that report claimed signature #2 already named the new shape, which is the opposite shape. Same justification as the `320-…` row above, and it should have been added at the same time. |
| `pm-plugin-development/skills/plugin-doctor/scripts/_runner.py` | RÅ-3 / 040-G1 | The gate published no `population_size` for `canonical-enum-choices-drift`, so a clean run reported a bare `findings: 0` while two reference docs claimed the opposite. Wiring it needed the runner, which the plan's D5 item names for two rules and not this one. |


### Proposals recorded, not decided

Both are deliberate non-decisions the plan assigns to an operator (§ Out of
scope). **Neither was shipped as a change.**

**P1 — narrow the back-tick exemption in `no-incident-references` (130/G2).**
A back-ticked incident reference is exempt from every narration family whatever
the surrounding prose, so a removed reference can be reinstated by adding two
backticks and the gate stays green. The narrowing the gap describes: suspend the
inline-code skip when an incident noun stands within a short window on either
side of the match, or when the line is a heading.

*The live sites the narrowing would newly surface* — re-derived at HEAD by
running the matcher with the inline-code skip disabled and subtracting the sites
that fire with it enabled.

⚠️ **This figure has moved three times during this run, and every move was
self-inflicted.** The gap document says two. It measured six once D8's two new
narration families widened the exempt population; **seven** at round 2's head,
because a docstring example round 2 wrote with a real `#NNNN` reference became a
live match of the very family it was describing; and **five** now, once that
example and a pre-existing one were spelled as placeholders. The figure is a
function of the tree at the moment it is taken — including of this run's own
prose — so it is re-derived here rather than carried, and a later reader should
re-derive rather than quote it.

At HEAD the five are:

| # | Site | Snippet | Genuine narration? |
|---|---|---|---|
| 1 | `plan-marshall/skills/phase-6-finalize/standards/finalize-step-preference-emitter.md:100` | ``failure mode `#990` `` | **YES** — incident narration in a normative standard, exempt only because the reference is quoted. This is 130/G2's real subject. |
| 2 | `pm-dev-frontend/skills/javascript/standards/jsdoc-essentials.md:109` | ``` `@since 1.2.0` ``` | No — a JSDoc **tag documentation example**. |
| 3 | `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py:92` | ``` ``plan-marshall#123`` ``` | No — that analyzer's own **specification prose**. |
| 4 | `…/_analyze_test_conventions.py:99` | ``` ``plan-marshall#123`` ``` | No — same specification, second occurrence. |
| 5 | `…/_analyze_test_conventions.py:101` | ``` ``pre-#812`` ``` | No — the surrounding sentence says so outright: *"a schema-state literal the corpus asserts on, not a citation of 812"*. |

**One of five is a real finding; four are false positives, three of them a
detector's own specification prose.** The narrowing as the gap describes it would
make `no-incident-references` fire on a sibling analyzer's specification of the
shapes IT matches. That is a stronger argument against the narrowing than the
convention-amendment reason alone.

If an operator still wants site 1 addressed, the cheap remedy is to fix that one
sentence (the mechanism is already stated beside it), not to narrow a
project-wide exemption whose false-positive rate on this corpus is 4-in-5.

A suppression entry is the wrong remedy here: the rule ships **unconditional**
by explicit design — no prefix is registered under `no-incident-references` in
`config/default-suppression.yml` — and the exemption is published across the
rule catalogue, the provenance table, a named test, and a sibling rule that
states the same posture. Narrowing it is an amendment to a stated convention,
which a run with no operator cannot approve.

**P2 — broaden the pin-trap shape-3 condition (320/G4).** The implemented
condition can only fire when a non-pin dir sorts HIGHER than the pin, so the
literal tree the plan's shape 3 named — an older stale unmarked dir beside a
correct newest pin — is a PASS. The alternative is to broaden the condition to
report two unmarked dirs regardless of which the loader follows. Whether that
tree is a finding or the benign post-sync window before the retention sweep runs
is a policy call about what counts as a finding. This run **pinned the current
behaviour** with `test_shape3_literal_older_stale_beside_newest_pin_is_a_pass`
and renamed the constant to describe the condition the code evaluates
(`SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR`), so whichever way the policy goes, the
present behaviour is recorded rather than assumed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — this
change edits Python under `marketplace/bundles/` and `test/` — so the full
`./pw verify` applies.

- **`./pw verify` green** at the D8 commit (`e4e3515`): `21402 passed, 14
  skipped` in 412.51s, with `ruff … All checks passed!`, `mypy … Success: no
  issues found in 416 source files`, and `SPDX-header check passed`.
- **`./pw verify` green** at the round-5 commit (`570c6ca`): `21420 passed, 14
  skipped` in 445.94s, with ruff, both mypy passes (416 production / 784 test
  files), the SPDX check and the marketplace-wide plugin-doctor pass all clean.
- **Nine commits landed between those two runs**, six of them touching `.py`
  (`b3786f6`, `a38c52a`, `0e07c43`, `a09e46f`, `a6ec688`, `93f95dc`), and this
  section named only the first of them for several rounds — an entry that was
  accurate when written and never re-derived. It is derived from
  `git log e4e3515..HEAD` at each update now.
- **`./pw verify` green** at the round-6 commit: `21422 passed, 14 skipped` in
  437.59s, and at the round-7 commit: `21424 passed, 14 skipped` in 438.59s —
  both with all six dimensions clean.
- **Owed on the merged tree** once the base moves — the full run is re-taken
  after the rebase onto PR #1314. Stated rather than left implicit: a green recorded against an
  earlier commit is not evidence about this one, and commit `570c6ca`'s own
  message said "Full verify green" while the section it shipped denied it.

**Stale-base re-verification (§ Step 8 condition 2): pending.** `origin/main`
has already advanced past this branch's merge base (66b686b → 0682705) while the
run was in progress, so the condition will apply; the count, the shape used, the
tested merge commit and the gate's result on it are recorded before arming.

### Per-commit gate

Every commit touching `*.py` was preceded by `./pw quality-gate`, each reporting
`ruff … All checks passed!`, `mypy … Success: no issues found`, and
`SPDX-header check passed`. Two commits took no gate and needed none: the plan
directory move (`2c67ed2`, a `git mv` with no content change) and the initial
branch push (no content at all).

## Findings

Recorded per instance. `RF-*` are the run's own findings; `CR-*` came from the
cold-read verifier; `CC-*` from the plan's own coverage check against the gap
documents.

| # | Source | Finding | Disposition |
|---|---|---|---|
| RF-1 | red-first, D4 | The first replacement fixture for `test_backticked_inline_code_ref_is_exempt` was **itself vacuous**: `` the `#812` failure mode `` puts a backtick BETWEEN the reference and the noun, which breaks the term-of-art pattern before the exemption is ever consulted. The mutation sweep caught it — disabling the inline-code skip left the test green. | Fixed: the whole narration phrase is quoted (`` `#812 failure mode` ``). Both earlier framings are named in the test's docstring so the next author does not repeat either. |
| RF-2 | self-review, D2 | `Path.rglob` over a path that does not exist does **not** raise — it yields nothing — so an ABSENT source directory was reported as `empty_comparison` rather than `source_unreadable`. The same launder-an-absence-into-an-observation defect the module exists to prevent, one level down. | Fixed: `_relative_file_set` tests `is_dir()` before walking. |
| RF-3 | self-review, D6 | `_after_verb` re-derived the leading-router-flag split by re-running the pattern over `leading + rest`, which greedily swallows the POST-verb flags too — a misplaced flag would have been invisible to the rule written to find it. | Fixed: the split is carried explicitly on `_Invocation` (`leading` / `rest`) rather than re-derived. |
| RF-4 | self-review, D8 | The brace-less enum member class `[^\s{}\|]+` swallowed the optional-argument closing bracket, reading `[--mode local_and_remote\|local_only]` as a member named `local_only]` and manufacturing **two drift findings on the real tree** out of punctuation, against correctly-documented flags. | Fixed: members restricted to identifier characters. Both false findings gone; real-tree findings back to 0. |
| RF-5 | self-review, D8 | The two new narration families made the analyzer **fire on its own comments** — the module's existing examples use a literal `#NNNN` placeholder for exactly this reason and the new ones did not. | Fixed: placeholders throughout, with the reason stated in the comment so the next editor keeps it. |
| RV-1 | round-1 verifier (F1–F4) | **The CR-2 fix moved the falsehood instead of removing it.** The split keyed on authority-key presence, and an absent key covers TWO states, not one: "the modelled parser declares no `choices=`" AND "no parser was modelled at all". A script whose parser is built by an **imported** helper (`script-shared`'s build-CLI factory) has no `ArgumentParser()` in the file the notation names, so **44 of the 68** sites filed as `no_choices_declared` — "NOT a blind spot" — were sites whose `choices=` exist and sit unread in another module. Verified independently: `build-gradle/SKILL.md:68` documents `run --mode {actionable,structured,errors}`, and `script-shared/scripts/build/_build_cli.py:179` declares exactly that `choices=`. The claim was restated in three places and in this report's own CR-2 row. | Fixed: a third cause, `parser_surface_not_derived`, keyed on whether the subcommand path was modelled at all; `blind_spots` published directly. **The first attempt at this was itself wrong — see RW-1.** Corrected figures under RW-1. |
| RV-2 | round-1 verifier (F11) | `_exemption_offset` also widened the `observed_on` family's exemption — its pattern begins at `Observed` and may carry 80 characters before the reference, so a back-ticked reference there fired before and is exempt now — while the docstring asserted only the reversed form was affected. Verified by execution: on `` Observed on the run log: `#812` was the culprit. `` the match start is 0 (outside the span) and the reference offset is 26 (inside it). | Widening **kept and disclosed**, not reverted: it makes `observed_on` consistent with the project-wide convention it was the sole exception to. Bounded — **zero** `observed_on` lines in the derived population have a verdict the change flips — and pinned by a test plus its bare-reference control. Docstring and catalogue corrected. |
| RV-3 | round-1 verifier (F5) | `rule-catalog.md` still asserted the false argparse claim D3/060/G6 exists to retire — corrected in `_entry_from_surface`'s docstring and left standing one file away. | Fixed. |
| RV-4 | round-1 verifier (F6) | `persona-plan-marshall-agent/SKILL.md` — the always-loaded floor — said "four" signatures and enumerated four, so the floor never mentioned the signature D6 added. The same enumeration-lead-in defect D6 corrected one file away. | Fixed: five, with the mirror named. |
| RV-5 | round-1 verifier (F7) | plugin-doctor `SKILL.md` enumerated four mirror-drift rules; the pack is six. | Fixed. |
| RV-6 | round-1 verifier (F8, F9) | The incident analyzer's own module docstring documented 4 of 6 families and omitted the version-constraint carve-out the catalogue had gained. | Fixed. |
| RV-7 | round-1 verifier (F10) | `_analyze_argument_naming.py`'s "Rule IDs registered" list and Public-API scan list both omitted the rule this run added. | Fixed. |
| RV-8 | round-1 verifier (F12) | The catalogue scoped the offset change to form 5, omitting form 2. | Fixed with RV-2. |
| RV-9 | round-1 verifier (F14) | A test docstring named the live fence's invocations in a way that reads as making `set-tier-0` the first; it is `get-tier-0`, which is *why* the latch left those sites unresolved. | Fixed. |
| RV-10 | round-1 verifier (F21) | `--paths` was described on the command's own doc as having one whole-tree exception; D1 added a second. Not false in itself, but the sentence reads as exhaustive and is the surface an operator consults. | Fixed: both classes named. |
| RV-11 | round-1 verifier (F22) | `ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED` had provenance and a firing fixture but **no `rule-catalog.md` entry**, unlike every sibling. No guard covers the catalogue, so nothing failed. | Fixed: entry added. |
| RW-1 | round-2 verifier (V2-15) | **Round 1's fix to CR-2 was itself wrong**, in the same shape twice over. `_derived_subcommand_paths` read its path set from the authority map's keys, and that map only gains a key when an arg carries `choices` — so a dict-spec subcommand declaring nothing but `help` contributed no path and was filed `parser_surface_not_derived`, i.e. a blind spot, when it is the one cause that is not. The conflation the census was written to end, committed inside the census. Live subject: `untrusted-ingestion/SKILL.md:57` (`validate --schema`), whose dict spec models `('validate',)` in plain sight. | Fixed: `_walk_declarative_specs` derives MODELLED paths independently of `choices`. Corrected figures: **blind_spots 50** (was 51), `parser_surface_not_derived` **43** (was 44), `no_choices_declared` **25** (was 24). Pinned by `test_a_dict_spec_subcommand_with_no_choices_is_not_a_blind_spot`. |
| RW-2 | round-2 verifier (V2-1..V2-5) | Round 1's replacement for the "two families" claim was **a different wrong mechanism, restated in three more places than before**. Executed per pattern: **four** of six families have a match beginning before the reference (`plan_marshall_ref`, `observed_on`, `temporal_narration`, `incident_term_of_art_reversed`), not two. The conclusion held for the wrong reason. | Fixed at all four sites plus a stale skip comment round 1 left beside the call it describes. The docstring now states the real discriminator — *can a backtick sit BETWEEN the match start and the reference* — which is a property of the pattern, not a count, and says so explicitly because the count is what a maintainer adding a seventh family would reuse. Three tests pin it by execution. |
| RW-3 | round-2 verifier | The RV-2 bound ("zero `observed_on` lines flip") is **true but VACUOUS**: the population contains zero `observed_on` matches at all, so it is not evidence of harmlessness. And the change was described as a widening only; it also **narrows** — a quoted opener with a bare reference was exempt and now fires. | Both corrected in the docstring, the vacuity flagged with a ⚠️ rather than left reading as measured evidence. The narrowing example I first wrote was **refuted by executing it** (the match start was outside the span, not inside); the shipped example is the one execution confirms. |
| RW-4 | round-2 verifier (V2-6..V2-10) | **Three of round 1's eleven fixes were half-applied** — the named site corrected, sibling sites asserting the same thing left standing. RV-4: four more "four signatures" statements in `recipe-fix-argparse-rejection/SKILL.md` (two of them enumerations omitting exactly the signature D6 added), plus `_analyze_argument_naming.py`'s own module docstring and a `test_analyze.py` block comment. RV-3: the retired argparse claim three times in `_analyze_manage_invocation.py` and in two test docstrings — where it states a **test's meaning**. | All fixed. Counts removed rather than corrected where the list is owned elsewhere, since a restated count goes stale the moment one is added there — which is how the missing control went unnoticed while the block claimed to cover them all. |
| RW-5 | round-2 verifier (V2-11) | RV-10 was half-applied and **F21 was therefore not fixed**: the `--paths` argparse `help=` string still read as exhaustive. This is the prose-bearing-string-literal class — documentation that lives as code, so a doc sweep never opens the file and a code sweep never reads the sentence, and it is the surface an operator reads directly. | Fixed: both unfiltered classes named in the help text. |
| RW-6 | round-2 verifier (V2-12) | `blind_spots` was claimed as published "on the analyzer's output" in two places; it existed only on `derive_coverage`, so a reader of a FINDING had to do exactly the re-derivation the sentence promised they need not. | Fixed: findings now carry `details.unresolved_notation_blind_spots`; both claims corrected. |
| RW-7 | round-2 verifier (V2-13) | "the flag's `choices=` exist and sit unread **in another module**" is false for a substantial share of the underived-parser sites: several have `choices=` in the SAME file, unreachable for a different reason, and some have none anywhere. | Fixed in three places. The cause now asserts only what it means — the surface was not modelled — and no longer claims where the choices live. The row originally published a count here; it was wrong (round 4, V4-8) and is dropped rather than corrected, since the point does not need it. |
| RW-8 | round-2 verifier (V2-14) | `persona-plan-marshall-agent/SKILL.md` was edited by round 1 and is neither in the plan's Expected surface nor in § Collateral. | Fixed: row added below. |
| RX-1 | round-3 verifier (V3-1) | **`no_choices_declared`'s published meaning was false of the sites in it.** It read "describes a free-form value, so there is genuinely no enum claim to contradict — the ONLY non-blind-spot cause". Verified against four sampled sites, all refuting: `untrusted-ingestion validate --schema` is constrained by `SCHEMAS.get()` → *Unknown schema*; `manage-tasks update --status` by a five-member tuple test; two `manage-execution-manifest record-step` flags by `VALID_*` constants. Their documented enums ARE real claims — enforced somewhere this rule does not read, by design. And this is the bucket round 2's headline fix moved a site INTO. | Fixed at four sites. The cause now states what it means — this rule's authority (`choices=` and nothing else) is established as ABSENT rather than unestablished — and says explicitly that this is a statement about the rule's authority, not about the flag. |
| RX-2 | round-3 verifier (V3-2) | **A mechanism round 2 invented and never ran.** The `parser_surface_not_derived` bullet listed "a parser passed INTO a helper" as a cause. Executed on that exact shape: the caller's own `add_parser` models the path, so only the authority key is missing and the site lands in `no_choices_declared` instead. The bullet describes a state the code cannot produce. | Fixed: the bullet is removed and replaced with the fact, plus a note that it was verified by execution. The two surviving mechanisms are confirmed live. |
| RX-3 | round-3 verifier (V3-3, V3-4, V3-10) | **My own docstring examples were live matches of my own rule.** The narrowing example round 2 wrote carried a real `#NNNN`, making it the ONLY `observed_on` match in the whole population — so the "ZERO matches, vacuous bound" claim was false, and its verdict flipped under the very change it illustrated. A pre-existing `#948` example did the same for `incident_term_of_art`. Both silently moved the P1 figure. | Fixed: both spelled as placeholders; the worked example moved to the test, where the file is outside the population. Measured after: `observed_on` and `incident_term_of_art` raw matches are now **0**, so the vacuity claim is now true. P1 re-derived (above). The module comment now says why backticks are not a substitute — an exempt match is still a match. |
| RX-4 | round-3 verifier (V3-5, V3-6) | **RV-3 and RV-4 were STILL half-applied after round 2 corrected them.** The retired argparse claim survived in `argparse_surface.py`, `tools-script-executor/SKILL.md` (which contradicted itself 156 lines later), and three test docstrings; the stale signature count survived on the References line of the file round 2 had just edited three times. | All fixed. |
| RX-5 | round-3 verifier (V3-9) | The `--paths` docstring lead-in said "Two rules behave specially" — and the second entry is not a rule but a property of the finding. | Fixed. |
| RX-6 | round-3 verifier (V3-11) | **`_walk_declarative_specs` injected the PARENT path for a spec whose `name` is absent or non-literal** — for a top-level entry, the root `()`. A documented root-level flag on such a script would then read `no_choices_declared`, i.e. authority-established-absent, although the parser was never reached. Round 2's change widened the aperture: before it, such a dict contributed a path only when it also declared `choices`. Zero live instances, but zero is smallness, not characterisation. | Fixed rather than characterised: a nameless spec contributes no path and is still recursed into. Pinned by `test_a_nameless_dict_spec_contributes_no_modelled_path`. |
| RX-7 | round-3 verifier (V3-7, V3-8, V3-12, V3-13) | Four smaller false statements, including two restatements of the "choices in another module" claim inside the file whose own text forbids that restatement, and a "12 of the 43" figure that is 10 under the reading its own sentence needs. | Fixed; the figure is dropped rather than corrected, since the sentence's point does not need it. |
| RY-1 | round-4 verifier (V4-1) | **Third consecutive round in which `no_choices_declared`'s meaning was false of its own bucket — and this time the falsifier was a real analyzer defect, not wording.** Five sites declare `choices=` in the same file on the same subcommand, matching the documented set exactly, and the resolver walked past them: four are declared on an `add_mutually_exclusive_group()` receiver the path walk never maps back to its parser, and one on a parser passed into a helper. So the rule's designated authority was PRESENT and unread, while the census reported "authority established as absent". | **Fixed in the resolver rather than in the prose.** Argument-group receivers now inherit their parser's paths — four more enums are now actually compared (resolved 77 → **81**), all matching. The helper case fails closed under a new `authority_incomplete` cause. Audited after: of the 20 remaining sites, the only one whose flag carries `choices=` elsewhere in its file is `manage-tasks update --status`, which genuinely declares none on `update`. ⚠️ **The audit's closing sentence — *"so the cause is now true of every site in it"* — did not follow and was false.** The audit searched each site's OWN file; three `phase_handshake --phase` sites have their `choices=` in an IMPORTED module (`input_validation.add_phase_arg`), which that search could not see. Round 5 caught it; see RZ-1. The bucket is 2 sites at HEAD and both were re-checked by reading their argparse declarations directly. |
| RY-2 | round-4 verifier (V4-7, promoted) | The passed-into-helper shape mis-filed the helper's `choices=` onto the ROOT path, because the assignment walk is module-wide and ignores scope: a `parser` parameter was conflated with a module-level `parser`. Round 4 characterised this as a bounded survivor; it is a latent false-finding source — a root-level flag of the same name would have been compared against a subcommand's authority. | **Fixed rather than characterised.** A receiver shadowed by an enclosing function's parameter is skipped fail-closed. Verified: the root-path keys for the live subject are now empty. Pinned by `test_a_parser_rebound_by_a_helper_parameter_is_not_attributed_to_the_root`. |
| RY-3 | round-4 verifier (V4-2) | **Half-application #5, inside the very file whose new docstring forbids it.** Three siblings still said "makes no enum claim the script can contradict" / "there is nothing to contradict" / "free-form in one subcommand" — the last citing `manage-tasks update --status` as free-form, the exact site round 3 had cited as counter-evidence. | All three fixed. |
| RY-4 | round-4 verifier (V4-3) | **Half-application #4 of the argparse claim, fourth round running** — this time in `templates/execute-script.py.template`, the SOURCE that generates every executor. Round 3 fixed two files in that same skill directory and missed the template. | Fixed. |
| RY-5 | round-4 verifier (V4-4, V4-5) | Round 3's own new prose claimed "every example in this file" uses a placeholder; two examples spell `#103`. And two of the recipe skill's restatements of the signature list survived, contradicting that file's own rule against restating them. | Fixed. |
| RY-6 | round-4 verifier (V4-6) | The nameless-spec test pinned only the early return: deleting the recursion branch left the suite green, while the docstring, comment and commit message all advertised that nested entries are still walked. | Fixed by adding the nested case to the test's fixture and assertion. |
| RY-7 | round-4 verifier (V4-11) | Three files round 3 edited appear in neither the Expected surface nor § Collateral — the obligation established one round earlier. | Rows added. |
| RZ-1 | round-5 verifier (V5-1) | **Fourth consecutive round in which `no_choices_declared` was false of its own bucket, and the second running in which the falsifier was a real analyzer defect.** Three `phase_handshake --phase` sites were filed "authority established as ABSENT" while `input_validation.add_phase_arg` declares `choices=PHASES` matching the documented enum exactly. Round 4's audit missed them because it searched each site's own file and these `choices=` are in an imported module. | **Fixed in the resolver.** A parser handed to a call this walk cannot model now marks that PARSER'S path authority-incomplete (`_paths_with_incomplete_authority`). ⚠️ **Two claims first written here were wrong and are corrected by round 6.** (i) *"The three sites moved"* — **17 moved**: `no_choices_declared` fell 20 → 2 and `authority_incomplete` rose 1 → 18, across six notations, with `blind_spots` 51 → 68. The three `phase_handshake` sites are the ones that MOTIVATED the fix, not its extent; the figure `18 → 2` in commit `570c6ca`'s message is likewise wrong, and wrong against evidence the round-5 verifier had already supplied (*"3 of the 20"*) — it was read off a census taken **after** the fix was already on disk, which is this plan's own stale-figure signature. (ii) *"both mutation-confirmed"* — one of the two was the `_ARGPARSE_CONSTRUCTION_CALLS` control, which round 6 showed could not be reddened by any mutation of the guard it named, because the guard was inert (see RZ-9). It is replaced by a test written against the structural reason, which the sweep does redden. |
| RZ-2 | round-5 verifier (V5-2) | **Half-application #6, in the same docstring round 4 had just edited.** The `parser_surface_not_derived` bullet still said a passed-into-helper site "lands in `no_choices_declared` instead — verified by executing that shape", which RZ-1's fix made false. | Fixed at all three sites that asserted it: the module docstring, the `authority_incomplete` bullet, and `rule-catalog.md`. The corrected claim names the three live instances rather than asserting a mechanism. |
| RZ-3 | round-5 verifier (V5-3) | **The shadowing guard was defeated by one indirection.** `grp = parser.add_mutually_exclusive_group()` inside `def _extra(parser)` gave `grp` the module-level parser's ROOT paths, so a `grp.add_argument(..., choices=...)` was filed against the root — the wrong-authority comparison `_shadowed_receivers`' docstring promises is impossible. No live instance; zero guard. | Fixed: group inheritance is scope-gated and a group off a shadowed owner is itself reported shadowed. Both branches asserted, and the fixture builds the parser BEFORE the helper on purpose — the first draft passed for a source-ORDER reason and left the gate deletable, caught by the mutation sweep. |
| RZ-4 | round-5 verifier (V5-5) | `rule-catalog.md` claimed a token is an enum "only when it parses into two or more members" and the module claimed a placeholder metavar makes no enum claim. **Both false**: the braced pattern had no member minimum while its brace-less sibling required a pipe. Live: `manage-config/SKILL.md:1212` `--scope {phase}.{role}\|plan\|…` entered the population as the one-member enum `{phase}`. | **Fixed in the collector, not the prose** — the minimum is applied to the parsed member SET, so it covers both notations and collapsing duplicates. Population 152 → 151. One pre-existing control fixture spelled its drift with one member and was widened to two, its intent unchanged. |
| RZ-5 | round-5 verifier (V5-6) | The `add_argument_group` half of `_PARSER_GROUP_FACTORIES` was unpinned — deleting it left the suite green while every `choices=` on a named group went unread. | Fixed: `test_choices_on_an_argument_group_resolve`, mirroring its mutually-exclusive sibling. Mutation-confirmed. |
| RZ-6 | round-5 verifier (V5-9) | Report RY-1's closing sentence — *"so the cause is now true of every site in it"* — did not follow from the audit it cites and was false (see RZ-1). | Fixed: the row now states what the audit established, why it could not see the imported-module case, and what is true at HEAD. |
| RZ-7 | round-5 verifier (V5-10) | § Mutation register claimed to cover "every new or changed guard" over a table holding only the original deliverable pass — the guards added in rounds 2, 3 and 4 had no rows. | Fixed: eleven rows added, each an OBSERVED red from a fresh sweep, not recollection. Two first-attempt mutations reddened most of the module and were discarded as non-evidence before the narrow replacements were run. |
| RZ-8 | round-5 verifier (V5-11) | § Coverage check said "Twenty-nine gap ids" over a **28-row** table: **320/G5 had no verdict row.** This plan's own subject, committed in the document that checks for it. | Fixed: 320/G5 verified against its literal *Done when* (both arms) and given a row; the tally is corrected to 28 met + 1 proposal over 29 rows. |
| RZ-9 | round-6 verifier (V6-7) | **A guard that guarded nothing, with a control test that could not fail.** `_ARGPARSE_CONSTRUCTION_CALLS` skipped argparse's own calls in `_paths_with_incomplete_authority` — but that scan inspects only ARGUMENTS, and every argparse call carries the parser as the RECEIVER, so no call could ever reach the skip. Deleting it left the whole-tree census byte-identical and the suite green, including the test written to pin it. | Removed rather than kept as reassurance. The control is rewritten against the structural reason (a receiver-position parser yields no incomplete path) with the discriminating half — the same parser moved to argument position DOES mark its path — so the sweep now reddens it. The one argparse shape that passes a parser by argument, `parents=[base]`, is named as an unclosed gap rather than implied covered. |
| RZ-10 | round-6 verifier (V6-6) | **A silent narrowing, in the analyzer whose subject is silent narrowing.** Round 5's two-member minimum DROPPED one-member groups at collection, defended by a comment saying such a group "carries no drift signal anyway". False: `--kind {bug}` against a live `choices=['bug','improvement']` is this rule's own headline truncated-oracle shape, and it was reported clean. No published figure said the token had been examined and skipped. | **Fixed by counting, not by dropping.** One-member groups stay in the population under a new `single_member_ambiguous` cause, included in `blind_spots`: the notation genuinely cannot tell a template slot from a truncated enum, so the honest act is to declare the ambiguity, not to resolve it silently. Census: population 151 → 152, blind spots 68 → 69. Two tests, mutation-confirmed. |
| RZ-11 | round-6 verifier (V6-8) | **The fix for round 5's laundering discarded a correct authority.** `_group_vars_off_shadowed_owner` returned bare group NAMES, unioned into every `add_argument`'s shadowed set — so one helper binding `grp` marked the name shadowed file-wide, including a correctly-attributed module-level `grp = p_add.add_argument_group('g')`. A false negative manufactured by the guard against false positives. Zero live instances. | Fixed: the `(group, owner)` pair is carried and a group is laundered only where its owner is shadowed too — the scope the shadowing itself has. Both directions pinned in one test. |
| RZ-12 | round-6 verifier (V6-1, V6-2) | **A fail-closed skip that does not exist**, claimed in two files: *"the flag resolves to MORE THAN ONE distinct `choices=` set across the script → SKIP"*. The authority is keyed by `(subcommand_path, flag)`, so `add --kind` and `remove --kind` resolve independently and are each compared. True before the authority was path-scoped, false after, and the same module says so 727 lines later. | Fixed in the module docstring and `rule-provenance.md`, restated as what the code does: only a conflicting re-declaration of the SAME `(path, flag)` is ambiguous. Half-application #7. |
| RZ-13 | round-6 verifier (V6-4) | **`no_choices_declared`'s prose false of its own bucket for the FIFTH consecutive round** — and this time caused by round 5's own fix. Two of the three sites the bullet used as worked examples (`manage-tasks update --status`, `manage-execution-manifest record-step --phase`) were moved into `authority_incomplete` by commit `570c6ca` itself. | Fixed with the two sites actually in the bucket, plus a standing instruction to re-derive the examples whenever the census moves. The recurrence is now named in the bullet rather than silently corrected a fifth time. |
| RZ-14 | round-6 verifier (V6-3) | The `authority_incomplete` bullet said *"the live instances are the three `phase_handshake` `--phase` sites"*. There are **18, across six notations** — the sentence was written from the sites that motivated the fix rather than from the census it produced. | Fixed with the full attribution, and `phase_handshake` demoted to the worked example it is. |
| RZ-15 | round-6 verifier (V6-5, V6-9, V6-17) | Three smaller false statements: `rule-provenance.md` still listed the placeholder-metavar case as a fail-closed SKIP (round 5 removed it from the module for the reason that it never enters the population at all — half-application #8); `_split_enum_members`' worked example had both halves backwards; and RY-1 cited a finding id that does not exist. | All three fixed. |
| RZ-16 | round-6 verifier (V6-10) | `_DefaultingParams.__missing__` was unreachable — the walk recurses with `ast.iter_child_nodes`, reaching exactly what `ast.walk` reaches; `__missing__` fired **zero** times over the whole marketplace, and deleting the subclass left the suite green. A defensive branch describing a state that cannot arise, whose declared return type also hid the defaulting from a caller annotated for a plain `dict`. | Removed. A missing key is a real bug and now raises. |
| RZ-17 | round-6 verifier (V6-11..V6-13, V6-15, V6-16) | Five report defects: "eleven rows added" was twelve; the register's completeness claim was false again at HEAD; RZ-1's "both mutation-confirmed" was false (see RZ-9); § Build gate named the wrong commit set; and **three of round 5's eleven items (R5-4, R5-7, R5-8) had no recorded disposition at all**. | All fixed. The three undisposed items were characterised survivors in the round-5 verifier's own verdict and are now recorded as such below, which is what condition B requires of a survivor. |
| RÅ-1 | round-7 verifier (V7-6) | **Round 6's fix for round 5's laundering leaked in the same shape.** Keying by `(group, owner_name)` narrowed the scope to "any function with a parameter of that name", not to the binding. With `grp` laundered inside `def _b(parser)`, an unrelated `def _c(parser)` calling the honest module-level `grp.add_argument(..., choices=...)` had its authority discarded and every site on the script downgraded. Third attempt at the same guard; the previous two were module-wide and name-pair. | **Fixed by keying on the binding's own enclosing FUNCTION**, which is the scope a local binding actually has. Three shapes asserted, including the cross-function read the name-pair keying got wrong. Mutation-confirmed. ⚠️ The verifier's stated reproduction (two fixtures differing only in `_b`'s parameter name) does **not** reproduce; the defect needs the honest group's `add_argument` to sit inside another function. The finding is real, its published mechanism was not, and it was confirmed by constructing the shape rather than by trusting either. |
| RÅ-2 | round-7 verifier (V7-5) | *"an explicit `add_argument(..., choices=...)` for the same (path, flag) is the one that wins"* — false. A differing re-declaration takes the conflict branch and resolves the key to `None`; the explicit call does not win, it destroys the resolution. Vacuous when the two agree, so false in the only case where it is testable. | Fixed, with both arms pinned by a new test. Two of my own first fixtures failed to set up the conflict at all (a spec passed by NAME, and a parser not built from `ArgumentParser()`), and each looked like a refutation of the verifier — the claim was only settled by a fixture where both forms demonstrably reach the same key. |
| RÅ-3 | round-7 verifier (V7-7) | **This plan's own D5 defect, uncorrected for a third rule, with two reference docs asserting the remedy.** `canonical-enum-choices-drift`'s coverage keys ride on FINDINGS, so on a clean tree — the only state a passing gate is ever in — the gate emitted `{'rule': …, 'findings': 0}`: a clean result over a population the reader is told nothing about. Meanwhile `rule-catalog.md` said *"a clean sweep states what it could not check"* and `rule-provenance.md` said a clean result *"cannot read as coverage over an unread population"*. | Fixed by wiring the runner, as D5 did for the other two: `analyze_canonical_enum_drift_with_population` returns findings and size from ONE derivation, and the rule joins `POPULATION_PUBLISHING_LABELS`. Both reference sentences now say what the two surfaces actually carry. Mutation-confirmed against the clean-tree publication test. |
| RÅ-4 | round-7 verifier (V7-8) | The normative fail-closed list opened *"Every path that cannot reach a confident authority resolves to SKIP:"* over **four** bullets, while the census names **seven** causes — the three omitted being the largest (`parser_surface_not_derived` 43, `authority_incomplete` 18, `single_member_ambiguous` 1), i.e. 62 of 71 unresolved sites. | Fixed: the list states the count, points at the full enumeration, and names the three it does not repeat, with an instruction not to shorten it back. Separately disclosed in `rule-catalog.md`: an enum above its block's first invocation is dropped at collection and counted by no cause — zero live sites, but the same shape as the one-member drop RZ-10 corrected. |
| RÅ-5 | round-7 verifier (V7-1, V7-2) | **Half-application #9, both inside the file round 6 had just rewritten.** Round 6 stopped filtering one-member groups at collection but left three sentences saying it still did: the fail-closed preamble ("both filtered at collection"), the pattern comment ("applied to the parsed member set in `_enum_sites_in_skill`"), and `_split_enum_members`' docstring ("the caller's two-member minimum is what rejects it"). The module contradicted itself in three places, and `rule-catalog.md` had it right. | All three fixed against the code. |
| RÅ-6 | round-7 verifier (V7-3) | **Half-application #10.** Round 6 deleted `_ARGPARSE_CONSTRUCTION_CALLS` and left two prose sites gating on it — one of them a TEST docstring, which states a test's meaning and is therefore not eligible as a survivor on any terms. Both described a name-list discriminator the code does not have; the real one is the parser's POSITION in the call. | Both fixed. The test docstring now states the structural reason its body actually checks. |
| RÅ-7 | round-7 verifier (V7-4) | *"18 sites across six notations"* — the sentence's own enumeration lists **seven** and sums correctly to 18. My correction of RZ-14 got the site count right and the notation count wrong, and copied it into two report rows. | Fixed at all three sites. |
| RÅ-8 | round-7 verifier (V7-9..V7-13) | Five report defects: a budget line still saying "0 of the grant. A sixth round is warranted" after round 6 had landed and was recorded above it; **V6-14, V4-9 and V4-10 with no id recorded** (the arithmetic RZ-17 introduced, failing on rounds 4 and 6); a mutation-register row naming a test and a target that no longer exist; and **two touched files missing from § Collateral for five rounds**. | All fixed. § Item accounting now tabulates every round's ids so the check is a table rather than a claim, § Collateral is derived from `git diff` against `origin/main` rather than from the round record, and the superseded register row is marked rather than deleted. |
| RF-6 | full verify, D6 | The new `ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED` rule had no provenance row and no firing positive fixture; two whole-tree guards failed. | Fixed: provenance row added; firing fixture added to `build_fixture_corpus`. |
| CC-1 | coverage check vs 360/G3 | That gap's *Done when* is a literal `grep -n -i 'retention.pin\|degraded fallback'` returning nothing. The rewritten docstring USED both phrases while explaining they were fiction, so the stated condition was not met. | Fixed: the paragraph describes what the body once computed without the two banned phrases. Condition now met (`grep` exits 1). |
| CC-2 | coverage check vs 320/G5 | That gap requires that **no surface** still claims the backward-resolution divergence is "practically unreachable". `320-.../report-01.md` still did. | Fixed: replaced with what the mechanism actually is. **Collateral, justified**: the file is outside this plan's Expected surface, but it is a location the gap itself names, and the claim is false — condition A admits no deferral. |
| CC-3 | coverage check vs 320/G5 | `320-.../verification.md` also matches "practically unreachable". | **Rejected — not a defect.** The match is inside that document's `**Contradicted:**` section, which QUOTES the claim in order to refute it. That surface already corrects the claim; editing it would delete the correction. |
| CR-1 | cold read, item 3 | **The operator remedy named a command that does nothing.** Step (2) gave `plan-marshall:marshall-steward:cache_retention sweep` as the command that prunes superseded version dirs. `sweep` is a read-only **dry run** unless `--apply` is passed (`cache_retention.py`: *"Perform the unlink. Without this flag the sweep is a read-only dry run."*). An operator following the remedy literally gets a report of what would be removed, sees no error, and moves to step (3) believing the prune happened — the false-clean shape this module exists to prevent, committed by its own remedy text. | Fixed: the step gives the full invocation including `--apply` and states what the flag's absence means. The remedy test asserts the `--apply` form. |
| CR-2 | cold read, item 4a | **The declared-coverage figure was published but not actionable.** All 75 unresolved sites landed in one bucket, `no_choices_or_unresolvable_choices`, merging two things of opposite risk: a flag declaring no `choices=` (no enum claim to contradict — not a blind spot) and a `choices=` the resolver could not reduce (a real claim left unverified — a blind spot). The module docstring separated them in prose while the published field merged them. Causes with zero occurrences were also omitted, so an absent cause was indistinguishable from one folded into a neighbour. | Fixed **in two steps, and the first fix was wrong** — see RV-1. |

### Cold reads (plan § Verification)

Four texts were read **cold** by an independent sub-agent — without this plan,
without the gap documents, and without the diff — and asked what a reader would
DO with each. Readings taken:

1. **Router-flag error note (D6).** Correct: the reader produced the exact
   working invocation, through the executor convention, with their own values in
   it, and reported nothing left to guess. No bare `*.py` path, verb supplied.
2. **Fifth recurrence signature (D6).** Correct and, critically, **two different
   answers** — before the verb for the CI surface, after it for
   `manage-architecture`. The reader named the bidirectional cross-references as
   what stopped them generalizing the first signature into a flag-level fact.
3. **Pin-trap operator remedy (D7).** **Failed** on step 2 — see CR-1. Steps 1
   and 3 were directly typeable.
4. **Declared coverage (D8) and the anti-vacuity claim (D1).** The
   enum-coverage statement **failed**: the reader could state the size and shape
   of the excluded set but **could not name it concretely** — see CR-2. The
   shim-marker recall statement passed, and the reader reproduced the permitted
   inference and both forbidden ones unprompted from the measured 4-of-25 pair.

### Round record

- **Round 1** — two verifiers: a code/deliverable verifier and a cold-read
  verifier. The cold read returned CR-1 and CR-2; the code verifier returned
  RV-1..RV-11. All fixed (`b3786f6`, `fdfb054`, `a38c52a`).
- **Round 2** — one verifier, aimed at what round 1's OWN FIXES made false.
  Returned RW-1..RW-8. **Round 1's failure signature repeated exactly**: three of
  its eleven fixes were half-applied, and one replaced a wrong mechanism with a
  different wrong mechanism restated in more places than before. Both of round
  1's headline fixes — the coverage split and the exemption-offset explanation —
  were themselves defective.
- **Round 3** — one verifier, aimed at whether round 2 repeated round 1's
  pattern. **It did.** Returned RX-1..RX-7: round 2's headline prose introduced
  two new falsehoods (RX-1's aggravation, RX-2's impossible mechanism), one
  self-refuting example (RX-3), and left RV-3 and RV-4 half-applied for a second
  time — one of them on the References line of a file round 2 had just corrected
  three times.
- **Findings are STILL not narrowing.** Nine of round 3's thirteen items were
  about the shipped bundle and test surface, not this report. A published figure moved
  again (P1: six → seven → five), for the same reason each time — a measurement
  carried across a population the run's own commit had altered.
- **Round 4** — one verifier, asking whether round 3 repeated the pattern. **It
  did, and the strongest finding was a real analyzer defect rather than
  wording**: for the third consecutive round `no_choices_declared` was false of
  its own bucket, this time because the resolver walked past `choices=` declared
  on an `add_mutually_exclusive_group()` receiver. Returned RY-1..RY-7. Two
  findings were fixed in the RESOLVER — four more enums are now actually
  compared — rather than by re-wording the claim a fourth time.
- **Findings are still not narrowing**, and the rate is flat: round 4 was 11
  items, 7 on the shipped surface (64%), against round 3's 13 items with 9
  shipped (69%).
- **Round 7** — one verifier. Returned 13 items, **8 on the shipped surface
  (62%)**. The absolute count fell (17 → 13); the shipped share did not. The
  headline was again a structural defect in the previous round's own fix, in the
  same shape as the defect it replaced: **three attempts at the laundering scope,
  each leaking differently** (module-wide → name-pair → binding). Round 7 also
  found this plan's own subject uncorrected for a third rule — the gate published
  no population for `canonical-enum-choices-drift`, while two reference documents
  asserted that it did. Half-application recurred for the ninth and tenth time,
  both inside files commit `6ab55a1` had itself edited.
- **One round-7 finding did not survive checking.** V7-6's published mechanism
  did not reproduce as written; the underlying defect was real and was confirmed
  by constructing the shape it actually needs. Recorded because a verifier's
  reasoning is evidence to test, not to adopt — the same standard this run
  applies to its own.
- **Round 6** — one verifier, the first of the operator's granted rounds.
  Returned 17 items, **10 on the shipped surface (59%)**. The share fell; the
  absolute shipped count rose (10 against round 5's 8). Three were structural
  defects in round 5's own new code: an **inert guard** whose deletion left the
  whole-tree census byte-identical and its own control test green (V6-7), a
  laundering set that poisoned a name **module-wide** and discarded a correct
  authority (V6-8), and a one-member exclusion that was a **silent narrowing**
  of the very census this analyzer publishes (V6-6). Half-application recurred
  for the seventh and eighth time, and `no_choices_declared`'s prose was false of
  its own bucket for the **fifth** consecutive round — this time because round
  5's own commit moved two of the three sites the prose used as worked examples.
- **Round 5** — one verifier, asking whether round 4 repeated the pattern. **It
  did.** Returned eleven items; the strongest was again a real analyzer defect
  (RZ-1) and again on `no_choices_declared`, false of its own bucket for the
  FOURTH consecutive round. Two further resolver defects followed (RZ-3's
  laundered shadowing, RZ-4's missing member minimum), and three findings were
  against this report rather than the code (RZ-6..RZ-8), including a coverage
  table one row short of the count above it.
- **Findings are still not narrowing, and round 5 was the worst yet by share:**
  8 of 11 items on the shipped surface (73%), against round 4's 7 of 11 (64%)
  and round 3's 9 of 13 (69%). Half-application recurred for the **sixth** time.
- **Budget:** five rounds (the contract default), then an operator grant of up to
  five more — *"continue with up to 5 rounds if sensible"*. **Rounds used: 5 of
  the default and 2 of the grant (rounds 6 and 7); 3 of the grant remain.** This
  line said "0 of the grant. A sixth round is warranted" for a round after round
  6 had landed as commit `6ab55a1` and was recorded above it — a prospective
  sentence left standing as a record of the past. Re-derive it from the round
  bullets above whenever a round closes.

#### Item accounting

Every round's item count, and where each id is dispositioned. Round 6 introduced
this check (RZ-17) after finding three round-5 items with no row; round 7 ran the
same arithmetic over rounds 4 and 6 and found three more, so it is tabulated
rather than asserted.

| Round | Items | Ids | Unaccounted |
|---|---:|---|---|
| 4 | 11 | V4-1..V4-11 | none — **V4-9 and V4-10 had no id in this report until round 7 (V7-11)**. Both were report-text defects and both were in fact fixed: V4-9 (the RW-7 row's "enumerates the three mechanisms", which RX-2 had reduced to two) and V4-10 ("nine of round 3's twelve items", which is thirteen). Fixed in the text, unrecorded as findings. |
| 5 | 11 | R5-1..R5-11 | none — R5-4, R5-7, R5-8 are in § Characterised survivors (added by RZ-17) |
| 6 | 17 | V6-1..V6-17 | none — **V6-14 had no id until round 7 (V7-10)**. It is the stale-figure finding, dispositioned inside RZ-1's correction rather than given a row of its own. |
| 7 | 13 | V7-1..V7-13 | none — RÅ-1..RÅ-8 below |

## Reviewer participation

*Pending — no PR yet.* The expected reviewer population is derived at PR time
from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
registry doc, never transcribed here.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** *pending* (recorded from run start/end at finalization).
- **Population:** whatever is recorded will count **this single Claude Code
  cloud session's usage as the harness counts it**. That is **not** comparable
  to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's own per-task billing boundary — a boundary
  a single interactive cloud session does not share. The two figures are not
  made comparable here, and no parity is implied.

## Coverage check against the gap documents

Twenty-nine gap ids, each checked against **its own gap document's literal
*Done when*** — not against this plan's restatement of it, which is a paraphrase
and diverged in three places (060/G2, 320/G9, 320/G10, all below).

| Gap | Verdict | Evidence |
|---|---|---|
| 040/G1 | **met** | Clean-tree gate publishes the size; `test_population_publishing_rules_report_their_size_on_a_clean_tree` asserts it with `findings == 0` alongside. |
| 040/G2 | **met** | § D3 of `040/report-01.md` now reads 46 collected cases across 21 functions; pytest collects 46, `grep -c 'def test_'` gives 21. |
| 040/G6 | **met** | Scoped run over a zero-population tree reports non-zero; `test_empty_population_finding_survives_scoped_run[thinking-directive]` pins it. Mutation-confirmed. |
| 050/G1 | **met** | Both retired sentences gone; `test_measured_recall_over_the_real_marked_population` asserts 25 anchors / 4 detectable against the tree. |
| 050/G2 | **met** | Wired into the analyze pass (the option the plan preferred); `test_shim_marker_rule_is_reachable_from_the_analyze_pass` covers it, so the catalogue claim is now true rather than corrected away. |
| 050/G5 | **met** | Same publication as 040/G1, asserted for `analyze_shim_marker`. |
| 060/G2 | **met** | Signature added with the mirror cross-reference. Second half — *"`060/report-01.md` § D1(c) no longer claims signature #2 names this shape"* — was **NOT met until this check found it**; that report still claimed signature #2 "already names this exact signature". Corrected. |
| 060/G3 | **met** | Executed with the gap's literal argv `['checks','status','--plan-id','X']` against the real `ci_base` parser: stderr carries `--plan-id` and `belongs BEFORE the subcommand`. Pinned by `test_real_ci_parser_reports_a_router_flag_written_after_the_verb`. |
| 060/G5 | **met** | Executed with the gap's literal argv: the example names `find`, not `<subcommand>`, and carries no bare `*.py`. Two tests assert both. |
| 060/G6 | **met** | Executed with the gap's literal fixture: after-verb → one `ARGUMENT_NAMING_ROUTER_FLAG_MISPLACED`; before-verb → none. |
| 060/G7 | **met** | Same fixture written flag-first → no `ARGUMENT_NAMING_FLAG_UNKNOWN`. |
| 100/G6 | **met** | Both rule ids in `rule-catalog.md` and `plugin-doctor/SKILL.md`; stated count "Six" equals the six `###` subsections. |
| 100/G7 | **met** | `derive_population` collects all six brace-less sites (verified by name), and the analyzer publishes the unresolved fraction with a per-cause census — the gap's second arm. |
| 100/G10 | **met** | Both tests pass; no site carries a subcommand the invocation above it does not name (asserted over the real tree); `analyze_canonical_enum_drift` still returns 0 findings. |
| 130/G2 | **recorded as proposal** | The plan forbids narrowing in this run. Proposal recorded under § Proposals with its live sites re-derived at HEAD. The gap's own *Done when* describes the narrowing and is deliberately unmet. |
| 130/G3 | **met** | All three literal sentences fire, the version-constraint negative does not, the real-tree anchor is green with no suppression entry. |
| 130/G5 | **met** | Mutation-confirmed: with the skip disabled the exemption test fails; restored, it and the paired positive pass. |
| 320/G1 | **met** | `total == 0` → `indeterminate`; a test drives `compare_pin_content` with a nonexistent `source_dir` and asserts the distinguishable reason. |
| 320/G2 | **met** | A test drives the ADAPTER (not the constructor) into `partial is True` with `PARTIAL scan` in `render()`. Red observed first, against the unmodified adapter. |
| 320/G3 | **met** | Two observations differing only in `content` → `indeterminate`, with an agreeing-content control. |
| 320/G4 | **met** | The literal tree has an asserted verdict (PASS); the shape constant is renamed to the condition the code evaluates; the alternative is recorded as a proposal, not taken. |
| 320/G5 | **met** | `loader_selected_version(dirs, frozenset({'0.1.100'}))` returns the OLDER dir; `test_loader_returns_an_older_dir_when_the_newest_is_ineligible` asserts it against a forward control, and `test_loader_is_none_when_eligibility_excludes_every_dir` pins the empty-pool arm. The gap's second arm — *no surface still claims the divergence is "practically unreachable"* — is checked by grep: the two remaining matches are `320/gaps.md` (stating the defect) and `320/verification.md`'s `**Contradicted:**` block (quoting the claim to refute it). See findings CC-2 and CC-3. |
| 320/G6 | **met** | No docstring claims marker-aware selection; `loader_selected_version` is one expression with no marker-independent branch. The gap's literal grep for `retention.pin\|degraded fallback` exits 1. |
| 320/G7 | **met** | Version-split → `fail` naming both versions; unreadable → `indeterminate`. |
| 320/G8 | **met** | Pin superset → `diverged == 1`, `extra_in_pin == 1`, `evaluate` → `fail`. |
| 320/G9 | **met** | All three steps name an invocable surface. The gap names `test_fail_verdict_states_operator_remedy_including_no_restart_and_in_run` as the test that must assert it; **this check found the assertion was only in a sibling test** and added it there too. Round 1's cold read separately found step (2) named a command that does nothing without `--apply`. |
| 320/G10 | **met** | The gap names the export **`observe_twice`**; this run first shipped it as `observe_pair`. **Renamed by this check** so the literal name is satisfied. Covered by a fake-sleep + mutating-fixture test yielding `indeterminate`, with a quiet-tree control, and `evaluate`'s docstring names it as the supported producer. |
| 360/G3 | **met** | The gap's literal grep exits 1; the docstring names the marker-free model; saturation is out of the load-safety conjunct; the two tests are renamed for marker-insensitivity. |
| 460/G5 | **met** | The gap's literal grep over `test/plan-marshall/plan-retrospective/*.py` returns only `test_chat_provenance.py:270`, which the gap itself declares out of family. |

**28 met, 1 recorded-as-proposal (130/G2, as the plan directs)** — of the met
set, 320/G4 carries a note (its alternative is likewise a recorded proposal).
Twenty-nine rows, one per gap id named by the plan.

⚠️ **320/G5 had no verdict row until round 5's verifier counted the table
against its own lead-in.** The gap was met and its two findings (CC-2, CC-3) were
recorded, so the omission was the tally's alone — twenty-eight rows under a
sentence claiming twenty-nine, which is this plan's own subject committed in the
document that checks for it.

⚠️ **Three gaps were not literally met until this check ran**, and all three were
places where the plan's paraphrase omitted something its gap document required:
060/G2's retraction in a sibling plan's report, 320/G9's named test, and
320/G10's exported symbol name. Checking against the plan's restatement rather
than the gap's own text would have recorded all three as met.

## Interaction with PR #1314 (test-module-budget campaign)

Flagged by the operator mid-run: PR #1314 restructures the test corpus and this
branch must rebase onto it once it lands. Assessed at the time of writing —
**#1314 is open and unmerged**, `mergeable_state: clean`, 281 files,
+50848/−42993; `origin/main` is at `0682705`, which does not contain it.

The overlap with this branch is **two files**, both from D8's 460/G5 item:

| File | What #1314 does | Consequence |
|---|---|---|
| `test/plan-marshall/plan-retrospective/test_analyze_logs.py` | **deleted outright** (2440 lines removed, 0 added) | this run's docstring fix is lost on rebase and must be re-applied |
| `test/plan-marshall/plan-retrospective/test_analyze_logs_behavior.py` | survives, +3/−2 | this run's fix conflicts or needs re-application |

The deleted file's `test_per_column_mix_of_measured_and_unmeasured` moves to
`test_analyze_logs_dispatch_boundary_context_load_columns.py`, where it **still
carries the stale "three-way read" docstring**, as does
`test_analyze_logs_behavior.py`. So both 460/G5 sites survive #1314 unfixed and
re-applying is a re-edit at two known anchors, not a merge resolution.

Nothing else is exposed: #1314 touches neither `test/conftest.py` nor any file
under `test/pm-plugin-development/plugin-doctor/`, which is where this run's
remaining test work sits.

Two consequences recorded now so they are not forgotten at rebase time:

- A rebase **rewrites every commit SHA on this branch**. No commit message here
  quotes a same-branch SHA, so none goes stale — but the commit column in
  § Deliverables above does, and is re-derived after the rebase by pairing old
  to new with `git range-diff origin/main...{old} origin/main...{new}` (by patch
  content, never by subject).
- The full `./pw verify` is re-run on the **rebased** tree. #1314 restructures
  281 test modules; a green run on the pre-rebase tree is evidence about a tree
  that no longer exists.

## Contract check (Step 9)

*Pending — performed and appended as the last pre-merge commit.*

## What have we learned (Step 9)

*Pending.*

## Residue

*Pending — completed at finalization.*
