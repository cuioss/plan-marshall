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

Every new or changed guard, the mutation applied to it, and the observed red.
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

**Independently reproduced.** The round-1 verifier re-ran the D4 and D3 mutations
from its own snapshot directory and confirmed both reds, so these are not this
run's own unchecked claim.

### Collateral outside the plan's Expected surface

The plan's claim-labels row makes recording this the run's obligation: *"a file
touched and not listed is collateral change to be justified in the report"*.

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
- **Not yet re-run on the current head.** Commit `b3786f6` landed after that
  run; it was gated with `./pw quality-gate` (clean on all three tools) plus the
  affected test files, **not** the full suite. The full `./pw verify` is owed on
  the current head before the PR, and again on the merged tree if the base has
  moved. Stated here rather than left implicit: a green recorded against an
  earlier commit is not evidence about this one.

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
| RY-1 | round-4 verifier (V4-1) | **Third consecutive round in which `no_choices_declared`'s meaning was false of its own bucket — and this time the falsifier was a real analyzer defect, not wording.** Five sites declare `choices=` in the same file on the same subcommand, matching the documented set exactly, and the resolver walked past them: four are declared on an `add_mutually_exclusive_group()` receiver the path walk never maps back to its parser, and one on a parser passed into a helper. So the rule's designated authority was PRESENT and unread, while the census reported "authority established as absent". | **Fixed in the resolver rather than in the prose.** Argument-group receivers now inherit their parser's paths — four more enums are now actually compared (resolved 77 → **81**), all matching. The helper case fails closed under a new `authority_incomplete` cause. Audited after: of the 20 remaining sites, the only one whose flag carries `choices=` elsewhere in its file is `manage-tasks update --status`, which genuinely declares none on `update` — so the cause is now true of every site in it. |
| RY-2 | round-4 verifier (V4-7, promoted) | The passed-into-helper shape mis-filed the helper's `choices=` onto the ROOT path, because the assignment walk is module-wide and ignores scope: a `parser` parameter was conflated with a module-level `parser`. Round 4 characterised this as a bounded survivor; it is a latent false-finding source — a root-level flag of the same name would have been compared against a subcommand's authority. | **Fixed rather than characterised.** A receiver shadowed by an enclosing function's parameter is skipped fail-closed. Verified: the root-path keys for the live subject are now empty. Pinned by `test_a_parser_rebound_by_a_helper_parameter_is_not_attributed_to_the_root`. |
| RY-3 | round-4 verifier (V4-2) | **Half-application #5, inside the very file whose new docstring forbids it.** Three siblings still said "makes no enum claim the script can contradict" / "there is nothing to contradict" / "free-form in one subcommand" — the last citing `manage-tasks update --status` as free-form, the exact site round 3 had cited as counter-evidence. | All three fixed. |
| RY-4 | round-4 verifier (V4-3) | **Half-application #4 of the argparse claim, fourth round running** — this time in `templates/execute-script.py.template`, the SOURCE that generates every executor. Round 3 fixed two files in that same skill directory and missed the template. | Fixed. |
| RY-5 | round-4 verifier (V4-4, V4-5) | Round 3's own new prose claimed "every example in this file" uses a placeholder; two examples spell `#103`. And two of the recipe skill's restatements of the signature list survived, contradicting that file's own rule against restating them. | Fixed. |
| RY-6 | round-4 verifier (V4-6) | The nameless-spec test pinned only the early return: deleting the recursion branch left the suite green, while the docstring, comment and commit message all advertised that nested entries are still walked. | Fixed by adding the nested case to the test's fixture and assertion. |
| RY-7 | round-4 verifier (V4-11) | Three files round 3 edited appear in neither the Expected surface nor § Collateral — the obligation established one round earlier. | Rows added. |
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
- **Budget:** five rounds (the contract default — this plan sets no other).
  Rounds used so far: 4. One remains.

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

Per gap id: met / not met / recorded-as-proposal. **Pending completion** — the
checks performed so far are recorded under § Findings (CC-1..CC-3) and the
per-gap table is written before the PR.

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
