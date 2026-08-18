# Verification — 300-freshness-gate-cannot-distinguish-test-authored-evidence

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `2d5da71` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `e2b6665` — *fix(manage-tasks): cross-check freshness-gate evidence against resolved builds (#1279)*
**Overall verdict:** CONFIRMED WITH GAPS

The shipped mechanism is real, correct on every path I could drive, and non-vacuously tested in
both directions — I proved the refusal direction and the comparison target by mutating production
code and watching the suite go red. What is wrong is a cluster of **mechanism and measurement claims
in shipped documentation** (the crawl's cost and what it shells out to), **three test gaps on code
the verification rounds themselves added**, and **four stale claims inside `report-01.md`** — three of
them the very "two rounds vs three rounds" drift the report predicted it would contain.

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

**One latent divergence found, not a live bug** (recorded as G9): the producer's stamp predicate is a
**prefix** allow-list (`_BUILD_CLASS_PREFIXES`, four `plan-marshall:build-*:` prefixes) while the new
consumer's classifier is an **exact-key** map (`_BUILD_NOTATIONS`, four full notations). I computed
the difference from the repository's own roster helper:

```text
DOMAIN (stampable):  build-gradle:extension, build-gradle:gradle, build-maven:extension,
                     build-maven:maven, build-npm:extension, build-npm:js_coverage,
                     build-npm:npm, build-pyproject:extension, build-pyproject:pyproject_build
KNOWN (classifiable): build-gradle:gradle, build-maven:maven, build-npm:npm,
                     build-pyproject:pyproject_build
DIVERGENCE:          build-gradle:extension, build-maven:extension, build-npm:extension,
                     build-npm:js_coverage, build-pyproject:extension
```

None of the five registers a `run` subcommand today (`run` is contributed only by
`script-shared/scripts/build/_build_cli.build_main`, and `js_coverage.py:281` registers `analyze`
only), so nothing stamps a row the cross-check would refuse. But the coupling is new, undocumented
and untested: before this plan an unclassifiable build notation was harmless; now it makes the gate
refuse **every** transition in the project.

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
- **The gate-level anti-vacuity control cannot detect the fault it names, in a full-suite run** (G8).
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
| Cost on a Maven/Gradle/npm project is unmeasured | **Open — and its premise is wrong** | The crawl does **not** run build-tool discovery verbs; see § Out-of-scope and collateral and G2–G5 |
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

**One undeclared behavioural consequence:** the gate's happy path now runs a live architecture crawl
that takes **7.6–10.6 s on this machine** (four measurements, § Method). It is paid at phase-5 Step
12a and again at phase-6 `push`. The shipped budget guidance says 1–5 s (G1).

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
  own machine. I state them as a contradiction of a range presented as a repository property, not as
  proof that the run's four measurements were wrong.

**Files I wrote:** only `verification.md` and `gaps.md` in this plan's directory. Two files elsewhere
in the tree (`manage-metrics/scripts/manage-metrics.py`, `plan-retrospective/scripts/check-artifact-consistency.py`)
show as modified; they are not mine — concurrent audit agents share this working tree — and I did not
touch them.
