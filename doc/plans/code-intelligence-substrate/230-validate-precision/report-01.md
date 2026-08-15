# Run report — 230-validate-precision (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/code-intelligence-validation-azwlva`    **PR:** _not yet opened at the time of this revision_    **Outcome:** in progress

## Skills loaded

Read by bundle path — the `plan-marshall` plugin was not needed, and every skill
resolved on the first route.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

`pm-plugin-development:plugin-architecture` was checked for presence but not
read: the change touches a skill *body*, not bundle structure or frontmatter.
No skill was unobtainable.

## Deliverables

### D0 — GATE: classify the FULL unresolved set (mutates nothing)

**Done.** Re-run live in the clone; every number in the plan was treated as a
lead and discarded. Baseline over `--scope marketplace`:

| Figure | Baseline |
|---|---|
| `total_components` | 306 |
| `total_dependencies` | 5301 |
| `resolved` | 4921 |
| `unresolved_count` | **380** |
| `circular_dependencies` | 294 |

All **380** rows were classified — an enumeration, not a sample. Each row was
enriched with its true source file and line text by re-running detection over the
same file set (the row count reproduced the validator's 380 exactly, which is what
makes the enrichment trustworthy), then classified on syntactic evidence from that
line.

Each row is reported under **the shipped guard that excludes it**, named by arm, so
a later reader can re-derive the partition from the code rather than trusting a
label. Script-notation rows first, then the other dependency types:

| Class (excluding guard / arm) | Rows | Share |
|---|---:|---:|
| Decision-log prefix — `(bundle:skill:step)` | 145 | 38.2% |
| Canonical verification-step ID — `default:verify:{canonical}` | 75 | 19.7% |
| **Excluded by no guard — candidate real breakage** | 64 | 16.8% |
| Documentation placeholder | 46 | 12.1% |
| Sub-document or versioned path (`/`, `.`+word arm) | 14 | 3.7% |
| Build coordinate / Gradle task path (`.`, `:` prefix arm) | 14 | 3.7% |
| `import` type — stale module mapping, none excluded | 11 | 2.9% |
| `skill` type — 9 placeholder-excluded, 1 kept | 10 | 2.6% |
| `path` type — 1 kept | 1 | 0.3% |

Sum: **380**.

⚠ **This table was republished after review.** The first version labelled 35
placeholders and folded 28 rows into "build coordinate", which merged two distinct
guard arms and pushed 11 Maven meta-syntactic placeholders
(`groupId:artifactId:{scope,compile}`) into the residual bucket. The plan's
Verification requires per-class counts "so a later reader can tell how the residue
was derived", and labels that do not describe their rows fail that test. The counts
above were re-derived by replaying the 380-row baseline population through the
shipped guard predicates, and were reproduced independently by the verification
sub-agent.

**The plan's "three distinct detector confusions" framing did not survive the
enumeration, and this is the run's most important finding.** The originating
sample named placeholders, subcommands and canonical commands. The full set shows:

1. **The largest class was not named by the plan at all.** Parenthesised
   decision-log prefixes are 38.2% of the set — more than any class the plan
   listed.
2. **The plan's "subcommand" class was a partial description of it.** The plan
   hypothesised "a three-part notation whose final segment is a subcommand of the
   skill's entry script". Measured against the corpus, the subcommand-of-entry-script
   rule covers 69 rows and the decision-log-prefix rule covers 147; they overlap on
   59 and **neither subsumes the other**. Of the 145 decision-log rows, only 59 sit
   on a skill that has a same-named entry script. Two distinct mechanisms share one
   surface.
3. **Two further false-positive families exist** — build coordinates and foreign
   namespaces — that no part of the plan anticipated.

The plan's ⚠ pointer ("the notation parser appears to treat *any* three-part
notation whose middle segment is not reserved as a script") was checked first, as
instructed. It names a real branch (`ComponentId.from_notation`, lines 68–75) but
**that branch is not the cause**: `detect_script_notations` never calls
`from_notation` — it hardcodes `component_type='script'` for every match. The
class is therefore *not* one branch, and the fix was not smaller than the class
suggested.

### Claim labels — every label confirmed or refuted with an artifact

The plan labelled five claims and required each be settled in the clone. None was
carried forward on the plan's word.

| Plan claim | Label | Verdict | Artifact |
|---|---|---|---|
| Validator reports a large unresolved set against a much larger total | OBSERVED | **Confirmed** | Re-run live: 380 unresolved / 5301 dependencies / 306 components |
| Placeholders, subcommands and canonical commands each appear in the set | OBSERVED | **Confirmed** | 55 placeholder, 69 subcommand-of-entry-script, 75 canonical, all enumerated |
| The **majority** of rows fall into these three classes | HYPOTHESIS (derived count) | **Confirmed — but only barely** | Union of the three = **199 of 380 = 52.4%**, and only when Maven meta-syntactic segments (`groupId`/`artifactId`) count as documentation placeholders. A bare majority materially understates the work: the other 47.6% is also mostly false positives, from classes the plan never named |
| The three classes are separable in the existing parser without a redesign | HYPOTHESIS | **Confirmed** | Additive guards only; no structural change to detection or the output contract |
| A genuinely-broken residue exists at all | HYPOTHESIS | **Confirmed** | 45 in-namespace rows were genuinely broken: 10 fixed, **35 remain**. The plan's ⭐ empty-residue success path does not apply |

**An asserted absence was verified as an asserted presence would be.** The claim
that the suppressed classes "are not real breakage" is not an argument from their
shape — it is the whole-corpus edge diff below, which shows the suppression removed
no resolved edge whatsoever.

### Regression evidence — no genuine reference was suppressed

The plan's Verification warns that "a precision fix that also suppresses real
findings has made the gate worse, not better". That was tested directly rather than
argued: the pre-change detector (from `origin/main`) and the current one were each
run over the same tree, and their **resolved-edge sets** were diffed.

| | Resolved edges |
|---|---:|
| Pre-change detector | 4928 |
| Current detector | 4965 |
| **Lost** (was resolved, now absent) | **0** |
| Gained | the D2 retargets |

Zero losses across the pre-change resolved set is strong evidence that the guards removed only
non-references — **in one direction**. It is not evidence in the other: a row that
was *unresolved* and wrongly *became resolved* is invisible to this diff by
construction, which is exactly the defect the verification sub-agent found (round-2
finding 1). Both directions are now covered — this diff for losses, and
`TestExclusionsAreProvisional` / `TestMisspelledScriptSegmentIsNotASubcommand` for
wrongful resolution.

### D1 — documentation placeholders are no longer references

**Done.** `NOTATION_PLACEHOLDER_SEGMENTS` recognises meta-syntactic segments
(`bundle`, `skill`, `script`, `subcommand`, `groupId`, `artifactId`, …). Applied
to the `skill` detector as well as the `script` detector, because 10 of the
placeholder rows arrived through `Skill:` and frontmatter rather than script
notation. Asserted by fixture.

### D2 — subcommands are no longer misread as scripts

**Done, and the done-when was read literally.** The plan asks that a subcommand
reference *resolve*, not merely go undetected — so the fix lives in the
**resolution** pass (`_dep_index.py`), not the detector. The plan marked
`_dep_index.py` as HYPOTHESIS; confirmed at outline, it is where `resolved = False`
is set and is the correct site.

`_entry_script_for_subcommand` retargets `bundle:skill:{verb}` onto the skill's
same-named entry script when one exists. Retargeting rather than merely flagging
resolved keeps the graph honest: `rdeps` and `tree` attribute the reference to the
script that owns the verb instead of leaving a dangling node.

**The reach of that retarget is narrow, and the report's first version overstated
it.** Most subcommand-shaped citations in this corpus are written as parenthesised
decision-log prefixes, which the decision-log guard excludes at detection — so they
never reach resolution and are absent from the graph rather than attributed to the
entry script. That ordering was **wrong, and review caught it** — see round-3 finding R‑1. The
retarget is now attempted *before* the provisional drop, so an excluded shape can no
longer hide a genuine verb citation; 59 such rows that were being discarded are now
resolved edges.

The guard is what preserves real findings: `pm-plugin-development:plugin-doctor:validate`
does **not** resolve, because plugin-doctor's entry script is `doctor-marketplace`.

### D3 — canonical command references are no longer script notation

**Done.** `CANONICAL_COMMAND_PREFIXES` mirrors `_CANONICAL_VERIFY_PREFIXES` in
`plan-marshall:manage-config` (`scripts/_cmd_quality_phases.py`), which is the
authority for the `default:verify:{canonical}` step-ID form. Asserted by fixture.

### Beyond the three named classes — a scope decision, stated rather than absorbed

D0 showed the three named classes are **not** the whole false-positive population.
Two further guards were implemented, both at the detector and both the same
mechanism as D1/D3 (suppress a shape that references nothing):

- **decision-log prefix** — the match is wrapped in `(` `)`;
- **embedded in a longer token** — preceded by `.` or `:` (build coordinate,
  Gradle task path), or followed by `/` or `.`+word-char (sub-document path,
  coordinate version). A trailing **sentence** period is deliberately not treated
  as a document suffix, and that distinction has its own test.

Rationale, since this is past the plan's letter: the plan's Goal is that findings
be "precise enough to gate on", and its Out-of-scope excludes *redesigning the
detection layer*, not *recognising more members of the same family*. Shipping only
the three named classes would have left 181 of 380 rows (47.6%) as noise — the
union of those three is 199 rows — and made D6's own question unanswerable. **What was deliberately NOT done** — see D6 — is the
one change that would have suppressed the rest, because it fails open.

### D4 — re-baseline and report the real unresolved set

**Done.** 380 → **62**, with `resolved` rising 4921 → **4965** and
`total_dependencies` falling 5301 → 5027. `total_components` is unchanged at 306 and
`circular_dependencies` is unchanged at 294, so the comparison is like-for-like on
both axes the validator reports.

Per the plan's Dependency note, the index's file coverage was confirmed before
re-baselining: component discovery globs `scripts/*.py` (not `rglob`), so nested
`scripts/{subdir}/` modules are not components. That coverage was **not changed by
this run**, so the baseline and the re-baseline are measured on the same footing.

The residue is **not empty**, so the plan's ⭐ empty-residue path does not apply.
It splits cleanly:

| Residue | Rows |
|---|---:|
| First segment IS an indexed bundle — actionable findings | 35 |
| First segment is NOT an indexed bundle — untriaged, see D6 | 27 |

**Fixed** (unambiguous staleness, each verified against the notation the
repository itself already uses — 10 rows):

| Was | Now | Rows | Evidence |
|---|---|---:|---|
| `plan-marshall:workflow-integration-git:merge_lock` | `plan-marshall:manage-locks:merge_lock` | 6 | `integrate_into_main.py` records the move; `automatic-review/SKILL.md` already invokes the new form |
| `plan-marshall:manage-task:manage-task` | `plan-marshall:manage-tasks:manage-tasks` | 3 | Skill is `manage-tasks`; entry script `manage-tasks.py` |
| `plan-marshall:plan-marshall:ref-workflow-architecture` | `plan-marshall:ref-workflow-architecture` | 1 | It is a skill, so the notation is two-part |

A further stale example — `plan-marshall:commands:tools-fix`, a command that does
not exist — was corrected in the same file D6 edits.

**Filed** — 35 rows, enumerated in full (each needs a decision or a design change
this plan excludes; the plan's Out-of-scope explicitly declines a blanket fix
obligation):

| Finding | Rows | Why filed rather than fixed |
|---|---:|---|
| `plan-marshall:extension-api:extension_base` | 11 | The mapping names the wrong skill — the module is at `script-shared/scripts/extension/`. Correcting the name alone does not resolve it, because nested script dirs are not components. Needs the coverage decision, not a rename |
| `pm-plugin-development:plugin-doctor:{validate,fix,analyze}` | 13 | `doctor-marketplace.py` exposes `analyze`/`fix`/`report`/`quality-gate`/`list-components`/`test-conventions`/`contracts` — there is no `validate`, and the documented `fix apply`, `analyze cross-file` chains do not map onto it. Establishing the consolidated CLI's real surface is a separate job; guessing would document commands that do not run |
| `_BUCKET_B_NOTATIONS` holds two unresolvable notations | 2 | **Production behaviour, not documentation.** `execute-task/scripts/inject_project_dir.py` matches on `plan-marshall:workflow-integration-git:git` and `plan-marshall:workflow-pr-doctor:pr-doctor`; the real scripts are `git-workflow.py` and `pr_doctor.py`, so project-dir injection cannot fire for either. The sibling entries in the same frozenset do resolve, which is what makes these two look wrong rather than stylistic. Changing dispatch behaviour is beyond a precision plan |
| `plan-marshall:tools-integration-ci:{github,gitlab}` | 2 | The Executor Mapping sections document a `github`/`gitlab` script; the real entry script is `ci.py`. The correct replacement depends on how `ci.py` dispatches providers |
| `plan-marshall:manage-findings:manage_findings` | 1 | The underscored script segment plugin-doctor's `manage-findings-invocation-invalid` rule already raises. Restored as a finding by round-2 fix 1; the doc site itself is a rule-catalogue example, so correcting it belongs with that rule's owner |
| Six one-off references | 6 | `domain-extension-api:validate_manifest`, `plan-marshall:plan-marshall:_invariants` (private module, deliberately not a component), `plan-marshall:recipe-` (ASCII-art placeholder), `pm-dev-java:build-maven:maven` and `pm-dev-java:java-core:java-core` (illustrative hypotheticals), `pm-plugin-development:README.md` (a relative link in an *asset template*, resolved against the template's own location rather than its destination) |

### D5 — precision regression test

**Done, with the assertion exact.** `TestPrecisionRegressionFixture` builds a
synthetic bundle holding **one instance of each excluded class plus one genuinely
broken reference** and asserts `unresolved_count == 1` — not "at least one", and
not "no placeholders". A companion assertion names *which* row survives, so the
count cannot be satisfied by the wrong finding.

Per the plan's Verification, each class also has its own case
(`TestNonReferenceColonTriples`, `TestPlaceholderSkillReferences`), and the
genuinely-broken case is verified to **still** be reported
(`TestSubcommandResolution`, plus `test_validation_fails_while_the_real_break_stands`).

**Red-before-green was observed, not assumed.** With the two source files stashed
and the tests unchanged, 13 of the then-18 new tests failed; against the unfixed
detector the fixture reported 6 unresolved targets rather than 1. The 5 that passed
are the deliberate controls asserting real notation is still detected — correctly
green both before and after.

**30 new test functions**; the file's collected total is **95** (from 65), and the
inventory suite is **187 passed**. Whole-suite at this revision: **20075 passed,
14 skipped**. (Function count and collected-case
count coincide here — none of these tests is parametrized.)

### D6 — documentation

**Done, shipped in this plan.** `tools-marketplace-inventory/SKILL.md` gains
"What counts as a reference" (the five excluded families, each with an example and
a reason) and "Precision of `validate`".

**Is the output gate-grade? Partly, and the page says exactly which part.**
Findings inside the marketplace-bundle namespace are precise enough to act on.
Two limits are documented rather than papered over:

- 27 residue rows sit outside the bundle namespace and are untriaged.
- Nested script modules are not components, so references to them cannot resolve.

`validation_result` is therefore documented as a **fail-closed report, not a
zero-tolerance gate**, with an explicit instruction not to wire it to a build step
that must stay green.

**The quality-gates page was deliberately not changed.** The plan's D6 says the
page "must say so" *if* it becomes a gate. It has not, so the condition does not
fire — and `doc/developer/build.adoc` makes no claim about this validator today, so
nothing there is now false. This is a reasoned non-edit, not a skipped step.

**The obvious remaining fix was considered and rejected.** Suppressing a
three-part token whose first segment names no indexed bundle would clear all 27
untriaged rows in a few lines. It was not done because it **fails open**: a
reference into a bundle that was deleted or renamed would vanish silently, which is
precisely the failure a gate must not have. `ref-code-quality`'s error-handling
standard names this shape directly — a gate must fail closed rather than emit an
unsubstantiated clean verdict. The fail-closed alternative is to *partition* rather
than drop (report `unknown-bundle` separately from `missing-component`), which
changes the output contract and is the operator's call, not this run's.

### Split-guard verdict (required at outline)

Seven deliverables, past the guard. **Verdict: not split.** The natural cut the
plan names — (D0+D1+D2+D3) then (D4+D5+D6) — would have put the enumeration and the
fixes in one PR and the re-baseline in another, but D4's re-baseline is the only
evidence that D1–D3 worked, and D5's fixture is the regression lock for the same
change. Splitting would have shipped a precision claim in one PR and its evidence in
another. Total diff is five source files plus docs.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` returns three files
(`_dep_detection.py`, `_dep_index.py`, `test_resolve_dependencies.py`), so the
Python path applies and the full gate ran.

`./pw verify` — **SUCCESS**, re-run after every round of fixes including the last.
All three sub-steps ran and were read from the tool output, not the exit code:
`ruff … All checks passed!`, `mypy … Success: no issues found in 405 source files`
(production), `mypy(test) … 750 source files`, `SPDX-header check passed`,
plugin-doctor marketplace-wide `total_issues: 0` with an empty `issues[]`, and
**`20075 passed, 14 skipped`** with no failures or errors.

`./pw quality-gate` was additionally run before each `*.py`-touching commit, clean
each time.

**Lockfile churn was backed out, not committed.** `./pw` rewrote `uv.lock` under the
session interpreter on every invocation; it was reverted before each commit and the
deliverable paths were staged explicitly. No commit in this branch touches `uv.lock`.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | D0 enumeration | The plan's three-class model is incomplete: the largest class (decision-log prefixes, 38.2%) is unnamed by the plan | **Reported + fixed** — two further guards implemented; scope decision stated above |
| 2 | D0 enumeration | The plan's "subcommand of the entry script" and the actual decision-log-prefix mechanism are distinct, overlapping rules (69 vs 147 rows, 59 shared) | **Reported + both implemented** |
| 3 | D0 enumeration | The plan's ⚠ "one branch may be the whole of this class" pointer names a real branch (`from_notation`) that is not on the detector's path at all | **Reported** — checked first, as instructed; hypothesis refuted |
| 4 | D4 residue | `PYTHON_MODULE_MAPPINGS['extension_base']` names the wrong skill (11 rows) | **Filed** — needs the nested-script coverage decision |
| 5 | D4 residue | `_BUCKET_B_NOTATIONS` holds two notations that resolve to no script, so project-dir injection cannot fire for them | **Filed** — production behaviour change, out of scope |
| 6 | D4 residue | plugin-doctor's documented `validate`/`fix`/`analyze` invocations do not match its consolidated CLI (13 rows) | **Filed** — correct surface must be established first |
| 7 | D4 residue | `tools-integration-ci` Executor Mapping documents `github`/`gitlab` scripts; the entry script is `ci.py` (2 rows) | **Filed** |
| 8 | Self-review | The first draft of D6's own documentation added 4 new unresolved rows by writing literal example triples | **Fixed** — families named instead of exemplified; re-measured at zero rows from that file |
| 9 | Coverage confirmation | Component discovery globs `scripts/*.py`, so nested modules are importable but unresolvable — the mechanism behind finding 4 | **Reported** |

Findings 1–3 are the ones the plan's D0 gate exists to produce, and each is
recorded per instance above rather than bundled into "the plan was roughly right".

## Verification sub-agent — round 2 findings

An independent read-only sub-agent verified the committed work against the plan.
It reproduced every published figure exactly (baseline `306 / 5301 / 4921 / 380`,
HEAD `306 / 4998 / 4937 / 61` as committed at that revision, D0 table summing to
380, the residue split 34/27),
proved the D5 fixture **non-vacuous** by disabling each guard independently
(each raises the fixture 1 → 2; all-off gives 6, corroborating the red-before-green
claim), and confirmed the `from_notation` refutation and the D6 conditional
non-edit. It then found eight defects. All eight were accepted; none was rejected.

| # | Finding | Severity | Disposition |
|---|---|---|---|
| 1 | D2 retargeted **any** unknown third segment, so `plan-marshall:manage-findings:manage_findings` — which plugin-doctor's `manage-findings-invocation-invalid` rule exists to raise, and which was unresolved at baseline — was reported **resolved**. A suppressed genuine finding, and it falsified a sentence shipped in `SKILL.md` | **Correctness** | **Fixed** — `_entry_script_for_subcommand` now rejects a script segment that is the skill's own name in the wrong case style; `SKILL.md` corrected |
| 2 | Fail-open: **any** parenthesised reference was dropped unconditionally, so a genuinely-broken reference written parenthetically escaped the gate | **Correctness (latent)** | **Fixed** — see the provisional change below |
| 3 | Fail-open: `bundle:skill:script.py` was dropped by the `.`+word arm | **Correctness (latent)** | **Fixed** — same change |
| 4 | D2's stated rationale ("`rdeps`/`tree` now attribute those references") overstated its reach: the decision-log guard pre-empts most subcommand citations at detection, and only 6 rows reach the retarget | **Reporting accuracy** | **Fixed** — D2 section above now states the interaction and the measured figure |
| 5 | D0's published classification was not reproducible as labelled — 35 vs 46 placeholders, and one row merged two guard arms while burying 11 Maven placeholders | **Reporting accuracy** | **Fixed** — table republished by guard arm, with the correction flagged |
| 6 | `doc/adr/002-…adoc:140` still stated the retired `plan-marshall:workflow-integration-git:merge_lock` in present tense — an **untouched file**, invisible to the marketplace-scoped validator and to the doc-corpus engine, and reached by an xref from the paragraph this run edited | **Stale claim beyond the diff** | **Fixed** |
| 7 | `test_from_notation_command` asserted on `plan-marshall:commands:tools-fix`, the nonexistent command this run corrected elsewhere. It passed because `from_notation` is a pure parser, so neither the local gate nor CI could catch it | **Test fixture keeping a retired value alive** | **Fixed** — retargeted to a command that exists |
| 8 | The D5 fixture omitted the sub-document-path arm, so a regression there failed only a unit test and not the exact-count assertion | **Test coverage** | **Fixed** — fixture now instantiates all six documented classes and still asserts exactly one finding |

**Finding 8b — the same self-inflicted-noise defect recurred, and is recorded as a
second instance rather than folded into the first.** Round 1's finding 8 was that
this run's own documentation added unresolved rows by writing literal example
notations. Fixing round-2 finding 1 required documenting the misspelling defect, and
the fix wrote the defective notation literally — adding it straight back as a real
finding (62 → 63). Caught by re-measuring rather than by review. The example is now
described rather than spelled, and the count re-verified at **62 with zero rows
attributable to this run's own docs**. Two instances of one defect is a pattern:
*documenting a notation defect inside the corpus that detects notation defects
requires typesetting the example, every time.*

**Findings 2 and 3 changed the design, for the better.** Both were the same defect:
an exclusion that fires on **shape alone** cannot distinguish a non-reference from a
genuine reference that merely looks like one. Exclusions are now **provisional** —
a match on an excluded shape is marked rather than discarded, and the index drops it
only when it also names no component. A provisional match that names a real
component is kept as an ordinary resolved edge. Shape decides where to look;
existence decides. This makes every guard fail-closed by construction rather than by
the absence of a counter-example in today's corpus, and it is directly asserted by
`TestExclusionsAreProvisional` (two fail-open cases plus two controls).

**A blind spot in this run's own regression evidence.** The resolved-edge diff
reported above checks for edges that were resolved and are now gone. Finding 1 ran
in the opposite direction — a row that was **unresolved** and wrongly **became
resolved** — which that diff cannot see by construction. The sub-agent caught what
the run's self-check was structurally unable to. Post-fix the count is 62 rather
than 61, and the extra row is the restored `manage_findings` finding.

## Verification sub-agent — round 3 findings

The round-2 fixes were re-verified by a second independent dispatch. It reproduced
every figure, confirmed fixes 1, 2/3, 5, 7 outright, and found that three of the
eight round-2 dispositions were **incomplete or wrong**. Two more defects were then
found by this run's own re-measurement while fixing them.

| # | Finding | Source | Disposition |
|---|---|---|---|
| R‑1 | The provisional drop ran **before** the subcommand retarget, so a genuine verb citation wearing an excluded shape was discarded — 59 rows in the live corpus. The shipped sentence "the exclusions cannot hide a real reference" was **false by the codebase's own definition of a real reference** | Sub-agent | **Fixed** — retarget is attempted first; the sentence is now true and scoped to the table it describes |
| R‑2 | The retarget assumed the entry script is named *exactly* like the skill. Nine skills spell it with underscores (`plan-doctor:plan_doctor`, `extension-api:extension_api`, …), and plugin-doctor's own rule catalogue explicitly rejects that assumption | Sub-agent | **Fixed** — both case styles are tried |
| R‑3 | Round-2 finding 8 was **not actually fixed**: the fixture's sub-document instance sat on the skill *with* an entry script, so disabling that arm left the count at 1. The disposition was literally true and functionally wrong | Sub-agent | **Fixed** — instance moved to the entry-script-less skill; all six arms now verified to bite |
| R‑4 | `doc/adr/002-…adoc:249` still named `workflow-integration-git/scripts/merge_lock.py`, a path that does not exist — the *same* ADR the round-2 fix had already edited two paragraphs earlier | Sub-agent | **Fixed** |
| R‑5 | `CANONICAL_COMMAND_PREFIXES` documented itself as mirroring manage-config's authority but carried one of its two prefixes | Sub-agent | **Fixed** — both mirrored |
| R‑6 | `SKILL.md` claimed "nothing distinguishes these structurally from notation" for the 27 untriaged rows. False: `_analyze_notation_staleness.py` already ships an executor-anchored, fail-closed discriminator | Sub-agent | **Fixed** — claim corrected and the existing mechanism named |
| R‑7 | Five **pre-existing** unconditional drops remain non-provisional (comment lines, URLs, `http`/digit segments). The comment-line skip alone discards 9 real resolvable notations. Not introduced here, but the new contract section omitted them | Sub-agent | **Disclosed** in `SKILL.md`; closing them deferred |
| R‑8 | Six report figures were stale or self-contradictory (residue 34 vs 35, "6 rows / 3 targets" vs 5/2, test counts, and a `./pw verify` figure that predated the round-2 commits) | Sub-agent | **Fixed** — every figure re-derived at this revision |
| R‑9 | **Third instance of the self-inflicted-noise pattern, in fields never measured.** The run had checked only *unresolved* rows. The round-2 finding-7 fix put a real command notation in `SKILL.md`, creating a 9-node **cycle** (`circular` 294 → 295), and four `notation-staleness` findings from a rule not wired into `quality-gate` | Sub-agent | **Fixed** — worked examples are now *named rather than spelled*; `circular` is back to the baseline 294 |
| R‑10 | The R‑2 fix **introduced a false resolution**: applied to a `PYTHON_IMPORT`, it retargeted the stale `extension_base` mapping onto the sibling `extension_api` script, silently resolving 11 genuine findings | This run's re-measurement | **Fixed** — retarget restricted to written script notation; the 11 rows are findings again, with a regression test |
| R‑11 | The R‑1 fix **introduced a spurious self-loop**: an entry script documenting its own verbs retargeted onto itself, manufacturing a circular dependency (`circular` 294 → 295) | This run's re-measurement | **Fixed** — self-edges are not recorded |

**The pattern worth naming.** R‑10 and R‑11 were both *caused by the fixes for
R‑1/R‑2* and caught only because every figure was re-measured after changing them —
not by reasoning about the change. Three separate times in this run, a fix to the
detector silently moved a number somewhere else. The lesson is mechanical rather
than moral: **after touching a classifier, re-measure every field it feeds — not
just the one the fix was about.** R‑9 is the same lesson in the reporting direction:
"zero rows from my own docs" was verified against `unresolved` only, while
`circular` and a second lint engine moved unwatched.

## Verification sub-agent — round 4 findings

A third independent dispatch verified the round-3 fixes. It confirmed the self-edge
skip is clean (all 26 skipped rows were already excluded, and both call paths compare
the right thing), the dual-case entry-script lookup is safe (no skill has both
spellings; the nine underscore-only skills are unaffected), and the prefix mirror is
inert-but-faithful. It found that **the R‑1 fix had over-corrected**, plus three
reporting defects.

| # | Finding | Disposition |
|---|---|---|
| R‑12 | **The R‑1 reorder bypassed every detection guard for any skill with an entry script.** 38 of 43 retargets were guard-bypassing, and 6 were wrong — five sub-document paths became false edges onto `manage-lessons` (whose entry script registers no `references`/`standards` verb), plus one step id | **Fixed** — the retarget is now attempted only for a shape whose third segment *can* be a verb. A decision-log prefix qualifies; a placeholder, canonical command, or sub-document path never does, because its third segment is a directory or a meta-variable. `Dependency.provisional` became `Dependency.exclusion`, recording *which* shape matched, so the distinction is data rather than a comment |
| R‑13 | The D5 fixture was **still vacuous for the `.`+word arm** — the recurrence round-2 #8 and R‑3 had each aimed at and missed | **Fixed** — a seventh instance added; each of the two embedded sub-arms is now disabled *separately* and both raise the count |
| R‑14 | **Fourth instance of self-inflicted noise**: `SKILL.md` spelled a real notation 26 lines below this run's own newly-added rule against doing so, creating both an edge and a lint finding | **Fixed** — measured against `origin/main` in a worktree: both revisions now report the **same two** notation findings, so this run adds zero |
| R‑15 | **The R‑6 fix replaced one false claim with another.** `_EXECUTOR_NOTATION_RE` belongs to the `notation-bundle-skill-drift` rule, not `notation-staleness`; and `notation-staleness` itself skips notations whose `scripts/` directory is absent — the very membership-based fail-open the same paragraph rejects | **Fixed** — the correct rule is named, and the paragraph now records that adopting it narrows the class by narrowing what counts as a reference |
| R‑16 | Three report figures stale (`59` retargets → 38; pre-change edge count `4931` → 4928; test counts), and the D4 Filed table enumerated 34 of 35 rows | **Fixed** — every figure re-derived at this revision; the missing row now has its own entry |
| R‑17 | **The "what have we learned" proposal named the wrong root cause.** It attributed `uv.lock` churn to an old session interpreter; the real cause is that `origin/main`'s lockfile pins `ruff>=0.16.1` while `pyproject.toml` requires `>=0.16.2`, so *any* `uv run` re-syncs it | **Fixed** — the proposal now states the actual mechanism |

**R‑12 is the third time a fix in this run introduced a defect**, after R‑10 and
R‑11. All three were over-corrections of the previous round's finding, and all three
were found by *measuring the corpus after the change* rather than by reasoning about
it. The countermeasure that actually worked, every time, was enumerating what the
change did to the whole corpus — not inspecting the diff.

## Reviewer participation

Population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`
registry doc, cross-named by `.github/workflows/pr-agent.yml`. Read from the
registry, never transcribed: **M = 3**.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `coderabbitai` | _pending — PR not yet opened_ | | |
| `sourcery-ai` | _pending — PR not yet opened_ | | |
| `cuioss-review-bot` | _pending — PR not yet opened_ | | |

The diff touches `*.py` **and** `marketplace/bundles/**`, so `skip-bot-review` does
NOT apply — a skill is code and is reviewed as code. Verdicts, the N-of-M coverage
figure, and the § Step 8 shortfall disclosure are filled in from the three comment
surfaces before the merge gate.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not
  expose a token counter to the running agent, so no figure is stated rather than
  an estimated one.
- **Wall-clock:** not measured — this session exposes no start timestamp to the
  agent, so no total is stated. The one directly-measured component is
  `./pw verify` at **476s**, which the build reported itself.
- **Population:** this single Claude Code cloud session's interactive usage.
  ⛔ **Not comparable to a plan-marshall `metrics.toon` total**, which counts an
  orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing
  boundary. This session shares neither that boundary nor that tree, so the figures
  cannot be reconciled and no parity is implied.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | Done | Named above; all resolved by bundle path |
| 2 Branch | Done | `claude/code-intelligence-validation-azwlva` on `origin` — **harness-assigned**, kept as-is. It was absent from the remote on arrival and was pushed as the first action, before any edit |
| 3 Plan directory | Done | `doc/plans/code-intelligence-substrate/230-validate-precision/plan.md`, moved with `git mv`; numeric prefix preserved; first-instruction block present on arrival, no repair needed |
| 4 Implement | Done | Four commits, each carrying the trailer |
| 4 Per-commit gate | Done | `./pw quality-gate` clean before each `*.py`-touching commit — ruff/mypy/SPDX lines read individually, not the exit code |
| 4 Pushed | Done | Pushed after every commit; `git status -sb` reports no `ahead` |
| 5 Build gate | Done | Git-derived verdict: 3 `*.py` files changed → full `./pw verify` → SUCCESS |
| 6 Verification sub-agent | In progress | Dispatched read-only before PR creation; findings recorded above when it reports |
| 7 PR cycle | Not yet done | PR not yet opened at this revision |
| 8 Merge gate | Not yet done | Pending the review cycle |
| 8 Bridge | Done | No status or bookkeeping write outside this plan's own directory |
| 9 This check | Done | This table |
| 9 What have we learned | Done | Below |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this session).
**Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a cloud run neither performs nor records one.

## What have we learned (Step 9)

**One contract change is proposed, and this run produced the evidence.**

**Evidence.** § Step 4 requires the quality gate before any commit touching `*.py`,
and § Step 5 warns that `./pw` rewrites `uv.lock`. Both are stated. What neither says
is that they **compound**: the gate must run *before* the commit, and running it is
what dirties `uv.lock`. Every gated commit in this run therefore arrived at `git add`
with churn already present, and § Step 5's own clean-tree re-assertion then flags it
as a defect in the run. This run backed the lockfile out before each of eight
commits; the contract never says to.

⚠ **The first version of this proposal named the wrong cause, and verification
caught it.** It repeated § Step 5's explanation — "`./pw` rewrites `uv.lock` under a
session interpreter below the project's floor" — as though that were the mechanism
here. It is not. The committed `uv.lock` on `origin/main` pins `ruff` at
`>=0.16.1` while `pyproject.toml` requires `>=0.16.2`, so **any** `uv run` re-syncs
that one metadata line regardless of interpreter version. The observation that the
churn is real stands; the diagnosis in the contract does not cover it.

**Proposed edit.** In § Step 4 "Commit and push", after the existing `git add -A`
prohibition, add: *"Expect `uv.lock` to be dirty whenever you have run the gate —
`./pw` re-syncs it, and not only under an old interpreter: a lockfile pin that has
drifted from `pyproject.toml` re-syncs on every `uv run`. Revert it
(`git checkout -- uv.lock`) as part of committing rather than when you happen to
notice, and re-check before Step 5's clean-tree assertion."*

**Not proposed, though tempting.** § Step 6's beyond-diff sweep worked as written
and caught a real defect in this run's own documentation (finding 8) — no change
warranted. The three-surface comment rule and the participation table likewise
behaved as specified.

Presented to the operator for approval. Per § Step 9 it ships as a **separate
`chore/` PR** touching only the skill, never in this plan's PR, and without
`skip-bot-review`.

## Residue

- **Filed, in priority order:** the `_BUCKET_B_NOTATIONS` dispatch bug (2 rows,
  production behaviour — highest value); the `extension_base` mapping plus the
  nested-script coverage decision (11 rows); plugin-doctor's documented CLI surface
  (13 rows); `tools-integration-ci` Executor Mapping (2 rows); six one-offs.
- **The untriaged 27.** Rows outside the bundle namespace. The fail-closed way
  forward is to partition `validate` output by reason (`unknown-bundle` vs
  `missing-component`) rather than suppress by bundle membership; that is an output-contract
  change and belongs to whoever owns the gate decision.
- **Gating.** The sibling editor-facing plan is gated on this one. It may now
  proceed against findings **inside** the bundle namespace. It must not surface the
  untriaged 27 into an editor until they are partitioned or triaged — that would
  reproduce this epic's archetype at exactly the point the plan warns about.
