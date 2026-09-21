# Verification — 300-freshness-gate-cannot-distinguish-test-authored-evidence

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** audited at `2d5da71` on `claude/code-intelligence-substrate-analysis-kah884` (concurrent
audit agents share this working tree and have since advanced `HEAD` with `doc/plans/`-only commits;
no file this audit examined changed)
**Landed as:** `e2b6665` — *fix(manage-tasks): cross-check freshness-gate evidence against resolved builds (#1279)*
**Overall verdict:** CONFIRMED WITH GAPS

The shipped mechanism is real, correct on every path I could drive, and non-vacuously tested in
both directions — I proved the refusal direction and the comparison target by mutating production
code and watching the suite go red. What is wrong is a cluster of **mechanism claims in shipped
documentation** (what the crawl shells out to), **three test gaps on code the verification rounds
themselves added**, **one latent coupling** between the executor's stamp allow-list and the
architecture's build classifier that nothing pins (G9 — not a live bug: the two sets agree today),
and **five stale claims inside `report-01.md`** — three of them the very "two rounds vs three rounds"
drift the report predicted it would contain.

⚠ **Corrected by adversarial review** (see § Adversarial review): this document originally also
charged the shipped crawl-cost *measurement* as wrong, and said "four" stale report claims while
listing five. The cost charge did not reproduce and is withdrawn; the count is corrected to five.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Establish what the gate checked; settle the fail-direction; refuse the doc-only carve-out in shipped reasoning | All three questions answered from the implementing source; fail-direction split; carve-out refused in source | All three answers re-derived first-party (pre-fix module driven, `build_record` fields read); split fail-direction and carve-out refusal are in `_freshness_crosscheck.py:44-91` | CONFIRMED |
| D2 | Is the producer half owned or unowned? | Discriminator EXISTS (`_is_build_class_notation` + `_BUILD_EXECUTING_SUBCOMMANDS`); provenance half unowned and stated as indefinitely defended | Both confirmed at `execute-script.py.template:329,334,1609`; `build_record` carries no provenance field | CONFIRMED |
| D3 | The match becomes auditable — record names notation **and** the row it matched | `matched_notation`, `matched_entry_index`, `matched_plan_id`, `timestamp_iso`; asserted by test | Present at `_cmd_pre_commit_verify_freshness.py:236-259, 329-338`; `test_fresh_record_names_the_matched_row` + parsed-index case pass and are mutation-sensitive | CONFIRMED |
| D4 | The match becomes cross-checked against **the plan's** architecture-resolved canonical build commands | Implemented, but as the **project-wide union over every module**, disclosed as a departure (R3-15) | Confirmed as described: `resolve_project_build_notations` unions every module; `plan_id` is never read. The literal *Done when* names a plan-scoped set; the shipped set is wider | PARTIAL (disclosed departure) |
| D5 | Tests (a) unrelated-only behaves per D1, verified to silently pass pre-fix; (b) multi-notation still passes; (c) record contains the notation | 17 + 8 test functions, 25 collected; pre-fix silent pass witnessed | 25 collected and green, re-derived; all three demands mapped to real, non-vacuous cases; the pre-fix silent pass independently **reproduced** by me | CONFIRMED |

## Per-deliverable detail

### D1 — what the gate checked, and the fail-direction

- **Required (plan):** answer (a) does it compare the matched notation against resolved canonical
  commands or only assert a row exists, (b) is the matched notation in the decision record, (c) is
  there a provenance field — *from the implementing source*; settle the fail-direction with reasoning;
  state that a doc-only carve-out was considered and REFUSED.
- **Claimed (report):** (a) only asserts a row exists; (b) partly — notation and timestamp yes, row
  identity no; (c) no provenance field. Fail-direction split: refutation → fail closed, inability →
  pass with the inability recorded. Carve-out refused *in shipped source*.
- **Found / checks run:**
  - I extracted the pre-change module (`git show e2b6665^:…/_cmd_pre_commit_verify_freshness.py`)
    and drove it against a one-row ledger (`notation: plan-marshall:build-npm:npm`, `status:
    success`, matching `worktree_sha`) in this Python-only repository. Output:
    `status: fresh`, `matched_notation: plan-marshall:build-npm:npm`, message
    `"… Gate permitted."` — no warning, no reason. (a) and (b) are **both confirmed exactly as
    reported**, first-party rather than taken on trust.
  - (c) `_ledger_core.build_record` (`manage-change-ledger/scripts/_ledger_core.py:135-148`) takes
    `notation, plan_id, args, exit_code, status, worktree_sha, log_file, command, duration_seconds,
    outcome, timestamp_iso`. No writer-identifying field. Confirmed.
  - Fail-direction and its reasoning: `_freshness_crosscheck.py:44-69`. Doc-only carve-out refusal:
    `_freshness_crosscheck.py:71-91`, a titled docstring section, and its supporting artifact is real
    — `test/plan-marshall/test_triage_loop_back_target.py:37` does parse
    `plan-marshall/workflow/triage.md`.
- **Verdict:** CONFIRMED. The plan offered two fail-directions and the run took a principled split
  rather than one of them; the split is argued in shipped source, which satisfies "and say why".

### D2 — is the producer half owned?

- **Required (plan):** establish first-party whether the stamp carries a subcommand discriminator.
- **Found:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:329`
  (`_BUILD_EXECUTING_SUBCOMMANDS = frozenset(['run'])`), `:334` (`_is_build_class_notation`, the
  prefix ∧ subcommand conjunction), `:1609` (`if _is_build_class_notation(notation, subcommand) and
  not _mentions_help(script_args):`). Exactly the lines the report cites, unchanged.
- **Verdict:** CONFIRMED. D2's table then required either staging the unowned half or stating that
  the gate must defend against bogus rows indefinitely. The run took the second branch explicitly
  (report § D2), which is a permitted answer. No plan owning test isolation exists anywhere under
  `doc/plans/` — I checked all seven epics — so the "stage it" branch was indeed not taken.

### D3 — the match becomes auditable

- **Required (plan):** when the gate is satisfied the record names the matched notation **and** the
  evidence row it matched; asserted by test.
- **Found:** `_evidence_fields` at `_cmd_pre_commit_verify_freshness.py:236-259` and its use at
  `:333`. Fields: `matched_entry_index`, `matched_notation`, `matched_plan_id`, `timestamp_iso`,
  plus `notation_cross_check`, `expected_notations`, `worktree_root`, `ledger_path`.
- **Checks run:** `test_fresh_record_names_the_matched_row` and
  `test_matched_index_addresses_the_parsed_row_not_the_file_line` pass. Mutation: forcing the
  cross-check's refusal branch to return `CORROBORATED`/`chosen: 0` turned four cases red including
  the parsed-index-adjacent ones — the record fields are load-bearing, not decorative.
- **Verdict:** CONFIRMED.

### D4 — the match becomes cross-checked

- **Required (plan):** compare the matched notation against **the plan's** architecture-resolved
  canonical build commands — explicitly *not* against notations appearing in this plan's ledger rows.
  *Done when:* an unrelated notation is surfaced per D1's direction **and** a legitimate
  multi-notation plan still passes.
- **Found:** `_freshness_crosscheck.cross_check_candidates` (`:250-343`) comparing against
  `_cmd_client_query.resolve_project_build_notations` (`_cmd_client_query.py:781-830`), which unions
  the build notation of every command of every module the crawl reports, classified by
  `_cmd_client_build.build_notation_for_executable`.
- **Checks run:**
  - I ran the live resolver against this repository: it returns exactly
    `frozenset({'plan-marshall:build-pyproject:pyproject_build'})` — the report's figure, re-derived.
  - The comparison target is the architecture, not the ledger — confirmed by reading the call chain;
    no ledger row is ever consulted for the expected set.
  - Both directions are asserted and non-vacuous (see § Test adequacy).
- **Verdict:** PARTIAL. The mechanism works and is defensible, but the shipped comparison set is the
  **project-wide union over every module**, where the deliverable's literal wording is "the plan's"
  resolved commands. The run disclosed this (report R3-15 and the commit message) rather than
  presenting it as compliance, which is the right handling — but the *Done when* as written is not
  what shipped, so it is recorded here as a departure rather than a pass.

### D5 — tests

- **Required (plan):** (a) unrelated-notation-only evidence behaves per D1's direction, **and is
  verified to silently pass against pre-fix code**; (b) a legitimate multi-notation plan still
  passes; (c) the decision record contains the matched notation.
- **Found / re-derived at this claim:**
  - `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` — **17** `def test_`
    declarations; `test/plan-marshall/manage-architecture/test_project_build_notations.py` — **8**.
    `uv run python -m pytest <both files> -o addopts="" -q` → **25 passed in 7.30 s**. The report's
    17 / 8 / 25 are all correct.
  - (a) `test_unrelated_notation_is_refused`; (b) `test_multi_notation_project_still_passes` and
    `test_related_row_behind_an_unrelated_one_still_passes`; (c)
    `test_fresh_record_names_the_matched_row`. All present, all red under mutation.
  - (a)'s pre-fix proof obligation: **independently reproduced** (see D1 above). This is the plan's
    own stated proof that the new test is not pinning the defect, and it holds.
  - Structural-stale: `test_mutated_worktree_stays_stale_with_its_own_reason` and
    `test_failed_build_for_current_sha_keeps_its_build_status_reason` both assert
    `'notation_cross_check' not in result`, so the cross-check demonstrably never reaches those rows.
- **Verdict:** CONFIRMED for the three enumerated demands. Separate test gaps exist on code the
  *verification rounds* added — see § Test adequacy; they are not D5 failures but they are gaps.

## Correctness review

I read every line of `_freshness_crosscheck.py`, `_cmd_pre_commit_verify_freshness.py`, the two new
functions in `_cmd_client_query.py`, and the `_parse_build_executable` split in `_cmd_client_build.py`,
looking specifically for fail-open branches, guards that cannot fire, unguarded `None`, and
order-dependence.

**No functional defect found in the shipped code paths I could drive.** Specifically checked and
found sound:

- The three-valued verdict never collapses: `resolution_reason is not None` returns `UNVERIFIED`
  before the membership loop, so an empty resolved set can never reach the `REFUTED` return
  (`_freshness_crosscheck.py:313-320`). The empty-set-as-refutation trap the module's own docstring
  warns about is genuinely closed.
- `chosen` is a position, never an object identity, and every branch that reaches the indexing sets
  it to `0` or an `enumerate` position (`:314-330`); the `REFUTED` branch returns first. The
  unguarded indexing at `_cmd_pre_commit_verify_freshness.py:333` is therefore reachable only with a
  valid position. R2-11's decision not to guard it is correct as of this tree.
- `_candidate_notation` folds a missing / non-`str` notation to `''`, and `'' in expected` is false
  for any real notation set, so a notation-less row can never corroborate (`:244-247`).
- Both cross-check `stale` routes omit `observed_status`, and `SKILL.md:299-307` documents exactly
  that. The `REFUTED` message's `", ".join(expected_notations)` cannot be empty on that branch
  (a non-empty set is a precondition of reaching it).
- The `Path.cwd()` fallback on `WorktreeResolutionError` (`:415-418`) is pre-existing and is
  documented as a real limitation at `SKILL.md:429` rather than papered over.

**One latent coupling found, not a live bug** (recorded as G9): the producer's stamp predicate is a
**prefix** allow-list (`_BUILD_CLASS_PREFIXES`, four `plan-marshall:build-*:` prefixes) while the new
consumer's classifier is an **exact-key** map (`_BUILD_NOTATIONS`, four full notations).

⛔ **My original arithmetic here was wrong and is corrected by adversarial review.** I labelled the
nine-element *prefix-matching* population "DOMAIN (stampable)" and reported a five-element
divergence. Stampable is a **conjunction** — prefix ∧ subcommand ∈ `_BUILD_EXECUTING_SUBCOMMANDS`
(`{'run'}`) — as the executor template's own comment states at `:311-313` (*"It is NOT sufficient on
its own"*). Re-derived from `test/_shared/_build_class_roster.py`:

```text
PREFIX-MATCHING (not stampable): build-gradle:extension, build-gradle:gradle, build-maven:extension,
                     build-maven:maven, build-npm:extension, build-npm:js_coverage,
                     build-npm:npm, build-pyproject:extension, build-pyproject:pyproject_build   (9)
STAMPABLE (roster):  build-gradle:gradle, build-maven:maven, build-npm:npm,
                     build-pyproject:pyproject_build                                             (4)
KNOWN (classifiable): the identical four                                                         (4)
DIVERGENCE:          EMPTY, in both directions
```

That the five non-wrapper scripts register no `run` subcommand (`run` is contributed only by
`script-shared/scripts/build/_build_cli.build_main`, and `js_coverage.py:281` registers `analyze`
only) is therefore not a mitigating footnote — it is the reason they are **outside** the stampable
domain in the first place, so no divergence exists today. The coupling is nonetheless new,
undocumented and untested: before this plan an unclassifiable build notation was harmless; a future
one would make the gate refuse **every** transition in the project.

## Test adequacy

Coverage map, all re-derived by running the files:

| Deliverable / property | Test | Non-vacuity evidence |
|---|---|---|
| D4 refusal direction | `test_unrelated_notation_is_refused`, `test_row_without_a_notation_is_refused`, `test_every_candidate_unrelated_is_refused` | Mutation 1 below → all three red |
| D4 acceptance direction | `test_multi_notation_project_still_passes`, `test_related_row_behind_an_unrelated_one_still_passes` | Cover distinct branches; the second pins the all-candidates scan |
| D3 record names its evidence | `test_fresh_record_names_the_matched_row`, `test_matched_index_addresses_the_parsed_row_not_the_file_line` | Mutation 1 → the live case red |
| Structural stale stays stale | `test_mutated_worktree_stays_stale_with_its_own_reason`, `test_failed_build_for_current_sha_keeps_its_build_status_reason` | Assert the absence of `notation_cross_check`, so a re-labelling regression is caught |
| The comparison target itself (V1-6) | `test_project_build_notations.py` — 8 cases incl. a live-repository control | Mutation 2 below → 5 cases red across both files |

**Mutations run (each byte-restored from a snapshot I took in `/tmp/verify-300-mutsweep/`; `git
status --porcelain` verified empty for all three files afterwards — no `git checkout`/`restore`/
`stash` was used):**

1. `_freshness_crosscheck.cross_check_candidates` final return `REFUTED`/`chosen: None` →
   `CORROBORATED`/`chosen: 0`. Result: **4 failed, 13 passed** — `test_unrelated_notation_is_refused`,
   `test_row_without_a_notation_is_refused`, `test_every_candidate_unrelated_is_refused`,
   `test_the_real_resolution_path_refuses_and_corroborates_against_this_repository`.
2. `resolve_project_build_notations` forced to return the empty set. Result: **5 failed, 20 passed**
   across both new files, including the live-repository anti-vacuity control.

Three real coverage gaps, each proven:

- **The R3-4 fix has no regression test** (G6). Narrowing the import guard back to
  `except ImportError:` — i.e. reverting round 3's reproduced runtime bug — leaves
  `test/plan-marshall/manage-tasks/` + `test_project_build_notations.py` at **504 passed**. The one
  behaviour change round 3 shipped, and the argument for stopping the loop, is unpinned.
- **The R2-12 guard has no test** (G7). Replacing `if not isinstance(notations, (frozenset, set)):`
  with `if False:` also leaves **504 passed**. (This one is documented as future-defence, so it is
  low severity — but it is untested defensive code either way.)
- **The gate-level anti-vacuity control cannot detect the fault it names, in a full-suite run** (G8;
  re-rated **high** by adversarial review, which reproduced the masking directly — the control is
  red when its file runs alone under a by-name import block, and **fully green** when
  `test_project_build_notations.py` is collected ahead of it).
  Its docstring says "an import path … that stopped working is a test failure rather than a silent
  no-op". `resolve_expected_notations` does `from _cmd_client_query import …`, which consults
  `sys.modules` first. Every test file in `test/plan-marshall/manage-architecture/` registers that
  module (directly, or transitively via `_cmd_client.py`) at import time, and pytest collects
  `manage-architecture` (collection line 3521) before `manage-tasks` (line 8713). I demonstrated the
  mechanism directly: with `_cmd_client_query` made unfindable by name, `resolve_expected_notations`
  returns `architecture_resolver_unimportable`; after a `spec_from_file_location` load registered
  under that same name — exactly what `conftest.load_script_module(..., '_cmd_client_query')` does —
  the same call returns `reason: None` and the full notation set. The control only holds when its
  file is run alone.

## Report accuracy

Every load-bearing technical claim I could check held: the pre-fix silent pass, the resolver's exact
output for this repository, the discriminator's line numbers, the ledger row's field list, the
17/8/25 test counts, the 6-production/6-test module split of the `*.py` diff, the `_stale_reason`
deletion (R3-8), the V1-1/R2-10 string-literal fixes, the `_forbid_builds` re-scope, the `test_logging`
comment correction, and the landing of the #1280 contract change (`.claude/skills/cloud-plan-lane/SKILL.md:612,624,682`).

Claims that are **false or stale against the tree now**:

1. **`report-01.md:860` (§ Residue, first row):** *"**A third verification round was not run.**
   Round 2's findings still included a behaviour change (R2-12) … See § Findings → 'two rounds'."*
   A third round **was** run — the same document devotes a titled section and thirteen numbered rows
   to it (`:456-480`) and says the loop "is stopped after round 3". The residue table is the hand-off
   surface, so this is the worst placement for the stale copy.
2. **`report-01.md:766` (contract-check Step 6):** *"✅ **TWO ROUNDS**"*, with a body that stops at
   round 2. Three rounds ran.
3. **`report-01.md:518` (section heading):** *"Verification loop — two rounds, and the residue is
   named rather than assumed"* — the section's own body then describes the third round.
4. **`report-01.md:239-247` vs `report-01.md:472` (R3-2):** R3-2's disposition says the crawl-cost
   range was **"Fixed in both"** sites, "now 'roughly 1 to 5 seconds across four independent
   measurements'". `manage-tasks/SKILL.md:412` does say four. The report's own claim site still reads
   *"Three measurements, each carrying its own population — 3.95 s …, 1.1 s …, 4.85 s"* and never
   names round 3's fourth measurement (4.23 s). R3-2 corrects R2-15 for over-claiming a two-site fix
   and then over-claims a two-site fix.
5. **`report-01.md:212-213`:** *"the live repository resolving its own build notation **through the
   real import path**"*. `test_the_live_repository_resolves_its_own_build_notation` loads the module
   through `conftest.load_script_module` → `spec_from_file_location`, i.e. by absolute path,
   bypassing `sys.path` — its **own docstring says so explicitly** (`test_project_build_notations.py:183-190`,
   the R2-4 fix). Only the sibling gate-level case reaches the resolver by name.

Claims I could not check and did not assume: the `./pw verify` totals (20476 / 20488 passed, 14
skipped), the mypy file counts (411 / 763), the per-commit gate history on a branch that was
squash-merged, the reviewer-participation timeline, and the CodeRabbit/Sourcery quota narrative.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| "A third verification round was not run" | **Moot and self-contradicted** | Round 3 ran (`report-01.md:456-480`). Recorded as a report defect (G10), not as work |
| The gate is still tier-blind — reads `notation`, not `args`/`command` | **Open** | `_freshness_crosscheck.py` reads only `notation` (`:244-247, 322-323`); no consumer of `args`/`command` exists. No plan under `doc/plans/` owns it |
| The resolve path can still raise on a malformed persisted command map | **Open** | `_cmd_client_query.py:652` — `cmd_data if isinstance(cmd_data, str) else cmd_data.get('executable', '')`, unguarded, as documented at `:634-651` |
| Producer-side provenance is unowned | **Open** | `_ledger_core.build_record:135-148` carries no writer field. No test-isolation plan exists in any `doc/plans/` epic |
| Cost on a Maven/Gradle/npm project is unmeasured | **Open — and its premise is wrong** | The crawl does **not** run build-tool discovery verbs. Instrumented twice independently: exactly **one** child process, `git rev-parse --git-common-dir`, and it comes from LSP-binding resolution, not from a build tool. See G2–G5 |
| The polluting consumer test is still unnamed | **Open** | Not identifiable from this clone, as the plan itself states |
| `notation_absent` loses to `notation_unrelated` on a mixed set | **Open by design** | `_freshness_crosscheck.py:342`; documented at `SKILL.md:321-327`. Behaviour matches the doc |

## Out-of-scope and collateral

Every exclusion the plan declared was respected:

- **Test isolation** — untouched. The only test-tree edits are a fixture re-scope
  (`test_build_class_stamp_discriminator.py`), a docstring re-scope (`test_plan31_…`), a comment
  correction (`test_logging.py`) and the two new files.
- **The pollution source** — not fixed, and still unnamed.
- **Doc-only exemption** — not added; refused in shipped source.
- **Re-stamping / relaxing the sha comparison** — neither. Two tests assert the structural-stale case
  stays stale, and mutation 1 shows they are sensitive.

**Collateral beyond the plan's "Expected surface" (labelled HYPOTHESIS there, and disclosed in the
report):** the change added a **new public API in a different skill** —
`manage-architecture`'s `resolve_project_build_notations` and `build_notation_for_executable`, plus a
`_classify_build_executable` refactor and a facade re-export — and edited four further documents
(`phase-5-execute/SKILL.md`, `phase-6-finalize/standards/push.md` and `…/pre-push-quality-gate.md`,
`extension-api/standards/build-systems-common.md`, `ref-code-quality/standards/error-handling.md`).
All are consequential restatements of the changed predicate rather than unrelated work, and all were
declared.

**One undeclared behavioural consequence:** the gate's happy path now runs a live architecture crawl,
paid at phase-5 Step 12a and again at phase-6 `push`. ⚠ **My cost figure for it was wrong.** I
reported **7.6–10.6 s on this machine** and charged the shipped 1–5 s guidance as understated.
Adversarial review re-measured nine times in fresh processes and got **2.99–3.70 s**, entirely inside
the shipped range, then reproduced my original figures (**7.19–11.56 s**) by re-running under
deliberate CPU contention. My four measurements were taken while concurrent agents ran full pytest
suites in this shared tree: I measured load, not the machine. The shipped guidance stands; G1 is
reduced to a request that it name its measurement condition.

## Method and coverage

What I did, in order:

1. Read `plan.md`, `report-01.md` (all 867 lines), and the epic README.
2. Read the landed commit `e2b6665` in full (`git show --stat`, then per-file diffs) and the current
   state of every production file it touched.
3. Ran the two new test files: **25 passed in 7.30 s**. Ran the whole of `test/plan-marshall/manage-tasks/`
   plus `test_project_build_notations.py`: **504 passed**. Ran the three other touched test files:
   **74 passed**.
4. Ran four mutations against production code, each restored from a byte snapshot in
   `/tmp/verify-300-mutsweep/` and each verified clean afterwards with `git status --porcelain`
   (two of the four were deliberate negative controls that stayed green).
5. Reproduced the plan's D5(a) pre-fix proof obligation by extracting the pre-change gate module
   from `e2b6665^` and driving it against an npm-only ledger.
6. Measured the live resolver's output and the crawl's cost and subprocess set on this repository,
   with `subprocess.run`/`Popen`/`check_output` instrumented.
7. Computed the executor's stampable build-class domain against `_BUILD_NOTATIONS` using the
   repository's own `test/_shared/_build_class_roster.py`.
8. Demonstrated the `sys.modules` pre-registration effect on the gate-level anti-vacuity control, and
   confirmed the collection order that makes it bite.

**Not checked, and why:**

- `./pw verify` as a whole — out of scope per the audit brief (many minutes). The report's suite
  totals and mypy file counts are therefore **UNVERIFIABLE** here; I ran the plan's own footprint
  instead.
- The PR/review timeline, per-commit trailers, and merge-queue behaviour — the branch was
  squash-merged, and the GitHub state is not re-derivable from this clone. **UNVERIFIABLE.**
- Cost on a Maven/Gradle/npm project — no such project in this clone. But I *was* able to falsify the
  claimed *mechanism* of that cost by reading the discovery path and instrumenting the crawl.
- The crawl timings I report are from this container; they are not directly comparable to the run's
  own machine. ⛔ **This caveat was not strong enough.** I stated them as a contradiction of the
  shipped range; adversarial review showed they contradict nothing — they were taken under
  concurrent load, and unloaded re-measurement lands inside the shipped range. A timing taken on a
  tree shared with other running agents is not a measurement of the tree.

**Files I wrote:** only `verification.md` and `gaps.md` in this plan's directory. Two files elsewhere
in the tree (`manage-metrics/scripts/manage-metrics.py`, `plan-retrospective/scripts/check-artifact-consistency.py`)
show as modified; they are not mine — concurrent audit agents share this working tree — and I did not
touch them.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | ⛔ **One material false positive: G1.** Its evidence — four `crawl_all_modules` measurements of 7.64 / 10.62 / 10.11 / 8.45 s, "every one outside the stated range" — did not reproduce. Nine fresh-process measurements (five of `resolve_project_build_notations`: 3.70 / 3.41 / 3.12 / 3.09 / 2.99 s; four of `crawl_all_modules`: 3.23 / 3.31 / 3.46 / 3.27 s) all fall **inside** the shipped 1–5 s range. Re-running under deliberate CPU contention on the same container reproduced the audit's figures (11.56 / 7.93 / 7.19 s), identifying them as a concurrency artifact of this shared tree. G1 as filed would have sent a fix plan to rewrite correct documentation. All other cited `path:line` claims were opened and hold; G14's docstring range and G9's template range were off by one and are corrected | G1 rewritten: claim withdrawn, severity `medium` → `low`, evidence replaced with both measurement sets and the contention reproduction, action narrowed to adding a measurement-condition qualifier and explicitly forbidding widening the range. Matching corrections in § Out-of-scope and collateral and § Method. Citations corrected to `test_project_build_notations.py:182-190`, `conftest.py:429-431`/`:564`, `execute-script.py.template:314-319` |
| A2 | False negatives | No new functional defect found. I re-derived D1(a)–(c) from `e2b6665^` first-party (the pre-fix module names `notation` only in prose and in one record field — there is no comparison anywhere, so D5(a)'s silent pass is structurally certain, not merely witnessed); confirmed D2's discriminator at `:329/:334/:1609`; confirmed the three-valued verdict cannot collapse (`resolution_reason is not None` returns `UNVERIFIED` at `:313-320` before the membership loop, and the `REFUTED` branch's `expected` is non-empty by construction); confirmed `chosen` is always a valid position. ⭐ **One hypothesis this audit had not tested, and it exonerates the change:** the cross-check selects the *first* corroborating candidate, so if the pre-fix gate had cited the *last* matching row, `timestamp_iso` in the decision record would silently have changed meaning. Read at `e2b6665^:308-326`: the pre-fix scan `return`s inside the loop on first match. The docstring's "matching the pre-cross-check behaviour" is true and D3's record semantics are unchanged | None needed — recorded here so the negative is distinguishable from an unrun check. D4's PARTIAL and every CONFIRMED verdict stand |
| A3 | Vacuous evidence | Both claimed mutations re-run from byte snapshots in `/tmp/adv-300-…-mutsweep/`, plus both of the audit's test-gap mutations. Mutation 1 (`REFUTED`/`chosen: None` → `CORROBORATED`/`chosen: 0`): **4 failed, 13 passed**, same four test names — reproduced exactly. Mutation 2 (`resolve_project_build_notations` → empty set): **5 failed, 20 passed** including the live-repository control — reproduced exactly. G6 mutation (`except Exception` → `except ImportError`): **504 passed**, gap confirmed. G7 mutation (`if not isinstance(...)` → `if False`): **504 passed**, gap confirmed. No `git checkout`/`restore`/`stash` used; `git status --porcelain` verified clean for every mutated file | None — the audit's non-vacuity evidence is sound and is now independently corroborated. First-party confirmation noted in G6 and G7 |
| A4 | Counts and quotes | Re-derived: 17 / 8 test functions and **25 passed**; **504 passed** baseline; collection lines **3521** and **8713** — all exact. Every quoted line checked verbatim against its file (SKILL.md cost paragraph, `resolve_project_build_notations` § Cost, `_architecture_core.py:543-545`, `_maven_cmd_discover.py:220-224`, the control docstring, report rows 766/518/472/860/212). ⛔ **Three count defects found.** (i) G2's "2 subprocess calls" double-counts one invocation — `subprocess.run` is implemented over `Popen` and both wrappers fired; the true figure is **one** child process. (ii) G9's "stampable domain holds nine … difference is five" is wrong: `build_class_roster()` returns **four**, `_BUILD_NOTATIONS` holds the same four, divergence is **empty**; the nine is the prefix-matching population, which the executor's own comment says is not sufficient to stamp. (iii) This document's summary said "four stale claims inside `report-01.md`" while listing and filing **five** | G2 evidence corrected to one process, with its real call stack named. G9 evidence rewritten with the re-derived sets and the reason the nine was the wrong population; its § Correctness review twin block rewritten. Summary corrected to five |
| A5 | Actionability | Every entry has a concrete `path`, change and observable *Done when*; none is a "review/consider/investigate". ⛔ **Two defects.** G8's *Done when* ("removing the `manage-architecture/scripts` entry from the suite's `sys.path` turns this case red when the whole suite is run") is **unreachable**: I tried it, and that removal makes `test_project_build_notations.py` fail at *collection* with `ModuleNotFoundError: _architecture_core`, so the suite reddens through a different file and never through this control. G2's *Action* instructed a fix plan to describe the crawl's `git` call as fetching "the worktree sha" — false, and it would have shipped a brand-new invented rationale of exactly the class this plan exists to close. G1's *Done when* ("states no numeric range that a fresh measurement on a supported host can fall outside") is unfalsifiable in principle | G8 *Done when* replaced with the by-name `meta_path` reproduction I validated, stated as a two-row before/after table the fixer re-runs. G2 *Action* corrected to name the real provenance and to forbid the worktree-sha wording. G1 *Done when* replaced with a checkable one |
| A6 | Severity and topic | ⭐ **G8 is under-rated at `medium` → raised to `high`.** It is not merely a vacuous test: it is the whole remedy for V1-6, the finding the run itself calls the round's most serious, whose symptom was the cross-check degrading to a permanent `unverified` pass with the suite green. I reproduced the masking — with `_cmd_client_query` blocked by name, the control is **red alone** but the pair runs **25 passed** when the architecture file is collected first — so the guard cannot fire in the only configuration that gates a merge. ⭐ **G5 is under-rated at `low` → raised to `medium`:** it is the authority G2/G3/G4 all quote, it contradicts two independent first-party surfaces (`_cmd_client_query.py:56-58` and `build-maven/SKILL.md:38`), and fixing the copies without it guarantees re-derivation — its own "Why it matters" said so while the severity said otherwise. G2/G3 examined for under-rating as instructed and **left at `medium`**: they are false claims in shipped documentation, which the calibration places at `medium` exactly; no behaviour is wrong and no measurement misreports. G1 lowered to `low` per A1. **One topic error:** G15 was `architecture-core` though its entire action lands in `manage-tasks/SKILL.md` | G8 → `high`, G5 → `medium`, G1 → `low`, G15 topic → `bundle-docs`. Final distribution: 1 high, 5 medium, 9 low |
| A7 | Coverage | Complete. All five deliverables carry a verdict and a per-deliverable section; out-of-scope compliance, collateral beyond the declared surface, report accuracy, the seven-row declared-residue table, and the method/not-checked list are all present. No deliverable is silently unmentioned, and the four plan exclusions are each addressed by name | None |
| A8 | Internal consistency | The overall verdict (CONFIRMED WITH GAPS) follows from four CONFIRMED rows plus one PARTIAL. Every actionable finding traces to a gap and every gap traces back (G1←cost, G2–G5←mechanism, G6–G8←test gaps, G9←latent coupling, G10–G14←the five stale report claims, G15←D4 PARTIAL). ⛔ **Two inconsistencies.** The summary's "four stale claims" against five filed (A4). And § Correctness review labelled a nine-element set "DOMAIN (stampable)" while its very next sentence conceded none of those five can be stamped — the label and the text could not both be true | Both corrected. The G9 block now separates the prefix-matching population from the stampable one and states the divergence is empty |

**Residual doubt:** The likeliest remaining find is in the **report-accuracy** half rather than the
code half. I re-derived the load-bearing technical claims and the five stale-claim findings, but
`report-01.md` is 866 lines and I checked its rows by sampling the ones the audit cited plus the
findings tables; a systematic row-by-row re-derivation of every `V1-*`/`R2-*`/`R3-*` disposition
against the tree was not performed, and this run's own history (R2-15 and R3-2 each corrected a
disposition that claimed a fix at a site it had not swept) says that surface reliably still holds
residue. Second most likely: G9's proposed pin may over-assert if a fifth build wrapper legitimately
ships without a `run` verb — `build_class_roster()` excludes those today, but the exclusion is
structural rather than asserted. The suite totals (20476 / 20488), mypy file counts and the
PR/reviewer timeline remain **UNVERIFIABLE** from this clone, as the audit already stated.

**Verdict on the audit:** SOUND AFTER CORRECTION — the shipped mechanism was assessed correctly and
the non-vacuity evidence fully reproduces, but the audit filed one gap against correct documentation
on a mis-measured figure, under-rated the one gap that lets the plan's headline defect recur with CI
green, and carried three arithmetic errors including a divergence that does not exist.
