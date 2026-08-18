# Verification — 040-generator-fails-open-and-its-fixtures-cannot-see-it

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** `a3a4da6` — `fix(tools-script-executor): fail-open regeneration guard + population-derived surface fixtures + required regen-and-dispatch smoke (#1164)`
**Overall verdict:** CONFIRMED WITH GAPS

All three deliverables are present in the tree and their central mechanisms work. Two of the plan's
literal *Done when* clauses are not met, and the run report states both as met:

- D1's refusal **does not exit non-zero** — it exits `0` with `status: error`. Measured, twice.
- D2's population-derived corpus is **72% tautological**: 1750 of its 2412 checks pass against a
  surface stripped of every attribute. Measured by mutation.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Fail a regeneration that derives zero surfaces where the previous had some; emit the stats line unconditionally | "added a fifth guard … ⇒ `status: error`, **non-zero exit**, nothing written"; line rides both returns | Guard 5 exists (`generate_executor.py:1371-1386`), refuses, writes nothing; stats line present in both the zero and non-zero cases. **But the process exits 0**, and the dry-run path emits no line and publishes `scripts_registered: 0` against 158 registered scripts | PARTIAL |
| D2 | Derive the fixture corpus from the real surface index; publish the population size; no sampling | "derives the real index (`registered=151 derivable=109 …`) … Publishes the population count … Verified by breaking the derivation on purpose — **498 refusals**" | Test exists, enumerates the live `SCRIPTS` registry, is not sampled, is `slow_live` and collected by default. Re-measured today: `registered=158 derivable=114 help_checks=1750 flag_invocation_checks=662`; children-strip → **509 refusals** (red). **But** the published count is swallowed by the repo's default pytest capture, and the 1750 help checks cannot detect any derivation defect at all | PARTIAL |
| D3 | Required regenerate-and-dispatch live smoke incl. a help spelling and a leading top-level flag | "a required step (MUST …) naming the two shapes that bit … All commands self-exercised" | `tools-script-executor/SKILL.md:293-360`. Reads as required on a cold read; both shapes named; **I ran the whole smoke live in this clone and it is clean** | CONFIRMED |

## Per-deliverable detail

### D1 — fail a regeneration that derives zero surfaces where the previous one had surfaces

- **Required (plan):** "*Done when:* a regeneration forced to derive zero against a non-empty previous
  state **exits non-zero**, and the stats line is present in **both** the zero and non-zero cases —
  asserted by a test that would fail if the line were emitted only when non-empty." Plus:
  "⛔ **Emit the surface-stats line UNCONDITIONALLY, including the zero**", and the emission contract
  stated "in the emission surface, not as a code comment."
- **Claimed (report):** guard added, `status: error`, **non-zero exit**, nothing written; stats line
  emitted at the single point the outcome is known; contract stated normatively on
  `format_surface_stats_line`; 7 targeted tests pass.
- **Found:**
  - Guard 5: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py:1371-1386`
    — `emitted_surface_count = surface_stats['surfaces_derived'] + surface_stats['surfaces_reused']`;
    `if previous_surfaces and emitted_surface_count == 0:` → `status: error` carrying `surface_stats`,
    nothing written.
  - Outgoing surfaces read before the probe: `generate_executor.py:1316`.
  - Unconditional line: `generate_executor.py:1358` (`print(format_surface_stats_line(surface_stats))`),
    placed after the derivation and before the guard, so it rides both returns.
  - Normative contract on the emission surface: `generate_executor.py:855-878` — the
    `format_surface_stats_line` docstring, not a code comment. ✔ as specified.
  - Error-path flattening: `generate_executor.py:1969-1977`.
  - Tests: `test/plan-marshall/tools-script-executor/test_generate_executor_behavior.py:372-507`
    (adversarial refusal, empty-previous negative control, no-false-trip parametrisation, the
    both-cases stats-line test, the flattening test) and the real-path end-to-end
    `test/plan-marshall/tools-script-executor/test_generate_executor.py:2865-2894`.
  - Pre-state confirms the guard and the line were genuinely new: `git show a3a4da6^:…generate_executor.py`
    has **0** occurrences of `format_surface_stats_line`/`surface-stats`, and its
    `return {'status': 'success', 'surface_stats': surface_stats}` was reachable with `surfaces == {}`
    (the OSError degradation at its lines 1289-1292 fell straight through to it). The report's
    claim-verification row for arm A is accurate.
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/tools-script-executor/test_generate_executor_behavior.py -o addopts="" -q -k "fail_open or surface_stats or stats_line"` → `7 passed, 32 deselected in 3.31s`.
  - **Exit-code probe (the decisive one).** A driver that pins `read_previous_surfaces` to a
    one-entry map and `derive_script_surfaces` to a zero result, then runs `main()` under the real
    `safe_main`:

    ```text
    surface-stats: scripts_registered=1 surfaces_derived=0 surfaces_reused=0 surfaces_not_derivable=1
    status: error
    error: "Fail-open regeneration refused: the previous executor carried 1 derived surface(s) …"
    EXIT_CODE_FROM_SAFE_MAIN= 0
    ```

  - Independent confirmation on a second error path:
    `python3 …/generate_executor.py verify` with `PLAN_BASE_DIR` pointed at a missing directory →
    `status: error` / `error: Verification failed`, `EXIT=0`.
  - Reading `main()` (`generate_executor.py:2306-2419`): it ends `print(serialize_toon(result)); return 0`
    — **unconditionally 0**, with no branch on `result['status']`.
  - `safe_main` (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py:1664-1700`)
    states the opposite of what `generate_executor.py:1964-1965` claims about it: "`sys.exit(1)` is
    retained, so the exit code still distinguishes a crash (1) from **an operation failure (0)**."
  - The repository contract agrees: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/manage-contract.md:34-36`
    — "**Exit 0**: Normal operation — success OR expected error … **Exit 1**: Unexpected crash —
    reserved for `@safe_main` exception handler only. Never return 1 from `cmd_*` or `main()`."
  - Dry-run behaviour: `generate --dry-run --marketplace --marketplace-root .` emits **no**
    `surface-stats:` line (grep count 0; the same grep matches the line in the live run above, so this
    is not a filtered false negative) and its TOON carries `scripts_discovered: 158` next to
    `scripts_registered: 0`.
- **Verdict:** **PARTIAL.** The refusal is real, loud in the TOON, and preserves the previous
  executor — that is the substance of the deliverable, and it is well tested adversarially. But the
  literal *Done when* ("exits non-zero") is **not met**, and cannot be met without violating
  `manage-contract.md`. The run substituted a defensible mechanism (`status: error` at exit 0) and
  then asserted the unavailable one as fact in four shipped places and in the report. A consumer that
  believes those statements — and one in this very repository does, `test/conftest.py:117-124` with
  `check=True` — cannot see the refusal at all. The unconditional-line requirement is met for real
  regenerations but not for the dry-run and template-skew paths.

### D2 — derive the fixture corpus from the real surface index

- **Required (plan):** a test that "walks **that index**" and "asserts every registered notation's
  `--help`, `-h`, and declared-flag invocation is accepted", is "population-derived, so it fails the
  moment the derivation drops an attribute". "⛔ **Publish the population size** in the test's output."
  "*Done when:* the test enumerates the index rather than a literal list, publishes the count it
  enumerated, and fails when an attribute is stripped from the derivation." "⛔ **Do not sample.**"
- **Claimed (report):** `test_population_derived_surface_guard.py` (`slow_live`) derives the real
  index (`registered=151 derivable=109 help_checks=1696 flag_invocation_checks=649`), installs the
  serialized `to_dict()` while walking the in-memory surface, publishes the count, and was verified
  by stripping `children` → 498 refusals.
- **Found:** `test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py:127-210`.
  - Enumeration, not a literal list: `_registered_notations()` (lines 85-111) `ast.literal_eval`s the
    live executor's `SCRIPTS` map; `surf.build_surface_index(...)` at line 145.
  - Not sampled: the loop at lines 171-195 walks every derivable notation and every node.
  - Tiering: `@pytest.mark.slow_live` (line 127); `pyproject.toml:189-196` states the marker
    deselects nothing by default — "a full run — local or CI — still executes every marked test." ✔
  - Serialized-vs-in-memory split as described: lines 162-165 install `result.to_dict()`; lines
    114-124 walk the in-memory `ParserNode`. ✔
  - Publication: `print(...)` at lines 198-202.
- **Checks run:**
  - Clean run: `uv run python -m pytest …/test_population_derived_surface_guard.py -o addopts="" -q -rA`
    → `1 passed in 131.96s`, captured stdout
    `surface-guard population: registered=158 derivable=114 help_checks=1770 flag_invocation_checks=672`.
  - **Mutation 1 — strip `children` from the serializer** (applied in-process via a pytest plugin, not
    on disk, because ~13 concurrent pytest runs share this working tree): → **FAILED**, "the pre-spawn
    validator refused **509** valid invocation(s) … over a population of 114 derivable notations."
    Reproduces the report's finding (498 at 151/109; 509 at 158/114). **The test is non-vacuous for
    `children`.**
  - **Mutation 2 — serialize every node as `{}`** (every attribute gone: `flags`, `children`,
    `required_flags`, `flag_arity`, `alias_of`, both confidence markers): → FAILED with **622**
    refusals over `help_checks=1750 flag_invocation_checks=662`. **622 ≤ 662 ⇒ every refusal came from
    the declared-flag half; not one of the 1750 help checks refused, against a completely empty
    surface.**
  - The mechanism is visible in the source: `templates/execute-script.py.template:1088-1089` —
    `if _mentions_help(script_args): return None` — short-circuits before any surface content is read,
    and the only preceding surface access (`_surface_for`, lines 800-809 and 1078-1080) returns `None`
    ⇒ "spawn" for a missing root. So no derivation defect whatsoever can redden a help check.
  - Publication visibility: `pyproject.toml:110` sets `addopts = ["-v", "--tb=short", "--strict-markers", "--strict-config", "--durations=25"]`
    — no `-s`, no `-rA`. Under the repo's own invocation the `print` is captured and discarded on a
    green run; I had to pass `-rA` to see it.
  - First attempt in this clone **failed outright**: `Failed: no .plan/execute-script.py under /home/user/plan-marshall`
    (test line 77). The root conftest bootstrap had run and produced nothing; see Correctness review.
- **Verdict:** **PARTIAL.** The test is genuinely population-derived, genuinely unsampled, correctly
  tiered, and demonstrably non-vacuous for the two attributes the flag half exercises. But the plan's
  "⛔ **Publish the population size** in the test's output" is defeated by the repo's own default
  capture, and the deliverable's stated purpose — "fails the moment the derivation drops an
  attribute" — holds for `flags` and `children` only. 72.6% of the corpus is a tautology with respect
  to that purpose, which the test docstring (lines 21-22: "a derivation that drops an attribute fails
  a test here instead of shipping") and report finding F2 both overstate.

### D3 — required regenerate-and-dispatch live smoke

- **Required (plan):** "*Done when:* the smoke exists as a required step (not a reviewer's judgement)
  and **includes a help spelling and a leading top-level flag**."
- **Claimed (report):** a normative "Required regenerate-and-dispatch smoke" subsection naming both
  shapes; all commands self-exercised.
- **Found:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md:293-360`.
  - Requiredness: "**MUST** be preceded by" (line 298); "a **required step, not a reviewer's
    discretion**" and "it is **not** satisfied by a green unit suite" (lines 299-300); "A change that
    has not run it clean is not ready to ship, regardless of the suite's colour" (lines 303-304); "The
    change does not ship on a red smoke" (line 355). Unambiguous on a cold read.
  - Both shapes named and justified: the long `--help` and the short `-h` "on a leaf that carries
    required flags" (lines 327-338); the "leading top-level flag before the verb" (lines 340-349).
  - The D1 shape is folded into step 1: "Confirm it exits `status: success` **and** that the
    `surface-stats` line reports a non-zero `surfaces_derived + surfaces_reused`" (lines 317-320).
- **Checks run — I executed the whole smoke live in this clone:**
  - Step 1: `python3 marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py generate --marketplace --marketplace-root .` →
    `surface-stats: scripts_registered=158 surfaces_derived=100 surfaces_reused=0 surfaces_not_derivable=58`,
    `status: success`, executor written.
  - Step 2a: `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks --help` → usage printed.
  - Step 2b: `python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read -h` →
    `usage: manage-tasks.py read [-h] --plan-id PLAN_ID --task-number TASK_NUMBER` — the required-flag
    leaf accepts the short spelling.
  - Step 2c: `python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture --project-dir . find --pattern "*.py"` →
    `status: success`, `count: 2686` — the value-taking leading flag is stepped over correctly.
  - No pre-spawn refusal on any of the three. Clean smoke.
- **Verdict:** **CONFIRMED.** Present, unambiguously required, both shapes named, and the prescribed
  commands work verbatim against the current tree.

## Correctness review

Read in full: `generate_executor.py` §§ surface-stats/derivation/guards/`cmd_generate`/`main`
(lines 795-1020, 1140-1450, 1920-2020, 2306-2425), `file_ops.py:1664-1700`,
`argparse_surface.py:380-450, 820-833`, `templates/execute-script.py.template:800-830, 1071-1140`,
`test/conftest.py:83-135`, the three touched test files, and `tools-script-executor/SKILL.md:230-360`.
Defects found:

1. **The refusal exits 0 — the fail-open guard is invisible to any exit-code consumer.**
   `generate_executor.py:2306-2419` — `main()` ends `return 0` with no status branch. Measured above:
   the guard trips, prints its stats line and error, and the process exits `0`. **The consequence is
   live in this repository:** `test/conftest.py:117-124` bootstraps the executor with
   `subprocess.run([... 'generate'], check=True, timeout=120)` — `check=True` is the *only* failure
   detection it has, and it can never fire on a guard refusal. The bootstrap then falls through
   silently with no executor written. This is structurally the same shape the plan set out to close
   ("a green regeneration that quietly stripped the whole set would leave the guard inert while every
   signal reads healthy"), relocated from the generator to its consumer.

2. **Four shipped statements assert a non-zero exit that does not happen.**
   `generate_executor.py:868` ("turns that zero into a loud non-zero exit"), `:1366` ("it fails loudly
   (non-zero exit)"), `:1964-1965` ("surfaces here as the command's `status: error` (non-zero exit via
   the safe_main contract)" — `safe_main`'s own docstring says the opposite), and
   `tools-script-executor/SKILL.md:263-264` ("it **fails loudly** (non-zero exit) and writes nothing").
   `:1964-1965` is the most damaging: it names a contract and inverts it, which is exactly what a
   maintainer wiring a new consumer would rely on.

3. **The dry-run path publishes a false `scripts_registered`.** `generate_executor.py:1271-1286`
   returns `dict(_EMPTY_SURFACE_STATS)` — all four counts zero — before `scripts_registered` is ever
   set. Measured: `generate --dry-run` on the live tree emits
   `scripts_discovered: 158` and `scripts_registered: 0` **in the same TOON payload**. This
   contradicts the invariant asserted at `:1987-1989` ("the three buckets always sum to
   `scripts_registered`") and diverges from the sibling degradation path at `:1344-1346`, which does
   set `scripts_registered = len(mappings)`. The emission contract's whole premise is that a consumer
   "establishes the derivation outcome by reading its VALUES"; on this path the value is wrong, not
   merely absent.

4. **"UNCONDITIONALLY" is narrower than the docstring says.** `format_surface_stats_line`'s contract
   (`:855-869`) says the line "is emitted UNCONDITIONALLY on every real regeneration". Two
   `generate` paths return before line 1358 and emit no line at all: the missing-template return
   (`:1218-1219`) and Guard 1's template-format-skew refusal (`:1296-1307`). A consumer that greps for
   the line and finds none is back to inferring from an absence on exactly those paths.

5. **A stale guard-count enumeration survived the F4 sweep.**
   `marketplace/bundles/plan-marshall/skills/manage-config/standards/provisioning-fail-closed-audit.md:96`
   still reads "Runs **four** deterministic guards (format-version handshake, placeholder-residue,
   `py_compile` self-check, emitted-path provenance)". The fifth (fail-open) guard is absent from both
   the count and the enumeration. F4 claimed to have corrected every statement the new guard
   falsified; this one was missed.

6. **`read_previous_surfaces` cannot distinguish "no previous surfaces" from "previous unreadable".**
   `generate_executor.py:983-1017` returns `{}` on an `OSError`, a missing block, a malformed literal,
   or a non-dict parse. Guard 5's predicate is `if previous_surfaces and …`, so an unreadable previous
   executor that in fact carried 158 surfaces makes the guard un-fireable and a surfaces-less write
   proceeds. Narrow and unlikely, but it is a guard that cannot fire on a real input class.

7. **Observed, not a defect but worth recording:** Guard 5 keys on a *total* collapse only. A
   regeneration that drops 158 surfaces to 1 still reports `status: success`. The plan scoped D1 to
   zero explicitly, so this is in-contract; it is named here because the originating incident's
   observable ("surfaces-less") is one point on a spectrum the guard does not otherwise cover.

**Out-of-scope items were respected.** `git show --stat a3a4da6` touched seven files: the plan's own
two documents, `tools-script-executor/SKILL.md`, `generate_executor.py`, and three test files. The
executor template (`templates/execute-script.py.template`) — the shipped pre-spawn guard the plan
forbade changing — is **not** among them. No repair-path hardening, no plugin-registry work, and no
new hand-written fixtures for the four known defects (`test_execute_script.py`, which holds the
flagless fixtures the report cites, was not touched by this PR).

## Test adequacy

| Deliverable | Tests | Non-vacuity evidence |
|---|---|---|
| D1 guard | `test_generate_executor_behavior.py:372-393` (adversarial refusal), `:396-412` (empty-previous negative control), `:415-432` (derived-or-reused no-false-trip, parametrised), `test_generate_executor.py:2865-2894` (real-path total collapse, driven by a genuinely broken script) | Structurally adversarial: 372-393 forces a zero derivation against a non-empty previous, which a guard-less generator answers with `status: success`. The pre-state at `a3a4da6^` confirms that was the behaviour. |
| D1 stats line | `test_generate_executor_behavior.py:435-462` asserts the line in the refusal **and** the success case; `:465-473` asserts every bucket is named; `:476-507` asserts the error-path flattening | Meets the plan's "a test that would fail if the line were emitted only when non-empty" — the zero case asserted is the refusal path. |
| D1 exit code | **none** | ⚠ No test asserts the process exit status on any path. Every assertion is on `result['status']`. That is why the substituted mechanism went unnoticed. |
| D2 | `test_population_derived_surface_guard.py:127-210` | Proven red by mutation (509 refusals on a `children` strip). |
| D2 help half | same file, lines 177-182 | **Proven tautological.** Under a total-strip mutation, 0 of 1750 help checks refused. These 1750 checks can only detect a regression in `_mentions_help` itself, never a derivation defect. |
| D3 | none (documentation) | Verified by execution instead — I ran the smoke; see D3 above. |

Mutations were applied **in-process** via throwaway pytest plugins under
`$TMPDIR/.../verify-040/`, never by editing tracked files, because ~13 concurrent pytest runs share
this working tree and an on-disk mutation would have corrupted them. `git status --porcelain` shows
no modification to any file this audit touched.

## Report accuracy

| Claim in `report-01.md` | Status | Correct value |
|---|---|---|
| D1: "⇒ `status: error`, **non-zero exit**, nothing written" (line 31) | **FALSE** | `status: error` at **exit 0**. Measured twice; `main()` returns 0 unconditionally, and `manage-contract.md:34-36` forbids anything else. |
| D1: "the stats line … rides both the refusal and the success return" (lines 33-35) | TRUE | Confirmed at `generate_executor.py:1358` and by the both-cases test. |
| D1: "The emission contract … is stated normatively on `format_surface_stats_line`, not as a code comment" (lines 35-37) | TRUE | `generate_executor.py:855-878`. |
| D1: "7 targeted tests pass" (line 38) | TRUE | Re-measured: `7 passed, 32 deselected`. |
| D1 self-exercise: "`surfaces_derived=2 surfaces_reused=107`" (line 39) | Historical, not re-derivable | Today's live regeneration: `surfaces_derived=100 surfaces_reused=0 surfaces_not_derivable=58` over 158 registered (cold cache, so nothing to reuse). |
| D2: "`registered=151 derivable=109 help_checks=1696 flag_invocation_checks=649`" (line 43) | Historical; tree has grown | Today: `registered=158 derivable=114 help_checks=1750-1770 flag_invocation_checks=662-672`. Not a defect — the run's numbers were true of its tree. |
| D2: "**Publishes the population count**" (line 46) | **OVERSTATED** | It `print`s it, but `pyproject.toml:110` addopts carry no `-s`/`-rA`, so on a green run the count is captured and discarded. Visible only when a reader already passes an extra flag. |
| D2: "stripping `children` … produced **498 refusals**, then reverted clean" (lines 47-49) | TRUE in substance | Reproduced: 509 refusals on today's larger population. |
| F2: "the test catches serializer (`to_dict`) strips … but not an upstream *parse-layer* strip nor a `required_flags` strip" (line 94) | **INCOMPLETE** | It also cannot catch a `flag_arity`, `alias_of`, `flags_confident` or `children_confident` strip, and — the large one — its 1750 help checks catch **no** strip of any kind. |
| F3: "guard count migrated four→five consistently" (line 95) | **FALSE** | `manage-config/standards/provisioning-fail-closed-audit.md:96` still says "four deterministic guards" and enumerates only the shape guards. |
| F4: "Four statements still described the pre-guard-5 contract … **Fixed** in commit `7738921`" (line 96) | TRUE for the four named; sweep incomplete | The four named statements are corrected in the tree (`:814-819`, `:1041-1043`, `:1979-1989`, and the SKILL.md prose). The sweep missed the audit doc above, and it introduced/retained four *new* false statements about the exit code (`:868`, `:1366`, `:1964-1965`, `SKILL.md:263-264`). |
| F5 reconciliation (lines 97) | TRUE | `test_failed_rederivation_drops_the_entry_rather_than_reusing_the_cached_one` (`:2820-2863`) is the reconciled two-script form and cross-references the new sibling; `test_total_surface_collapse_against_a_populated_previous_fails_open` (`:2865-2894`) exists. |
| Claim table: "Generator … returned `{'status':'success','surface_stats':…}` even when `surfaces` was empty" | TRUE | Verified against `a3a4da6^`: the success return was reachable with `surfaces == {}`, and the OSError degradation fell through to it. |
| Claim table: "Every hand-built fixture declared at least one flag — **Refuted as stated**" | TRUE | `test_execute_script.py:1034` `test_help_flag_always_dispatches_even_on_a_flagless_surface` and `:1225` exist and predate this PR. |
| Claim table: "Part of D1 may already exist … the counts were already computed and published; what did NOT exist: the guard, the counts on the error path, a distinct always-emitted line" | TRUE | `a3a4da6^` has 0 occurrences of `format_surface_stats_line`/`surface-stats` and no fifth guard. |
| Build gate: "18966 passed, 14 skipped" | Historical, not re-derivable | Not re-run (out of audit scope, many minutes). |

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D2 is `slow_live` (~52–87s cold), shares the help cache with the sibling | **Open by design** | `@pytest.mark.slow_live` at test line 127; `pyproject.toml:189-196` confirms it is never deselected by default. Measured cold here: 131.96s under heavy host contention; 7-9s warm. |
| The `manage-invocation-invalid` analyzer does not model the help short-circuit, so a concrete `{notation} --help` example cannot be written as a validated canonical call | **Still open** | `pm-plugin-development/skills/plugin-doctor/scripts/_analyze_manage_invocation.py` has no help exemption anywhere; its `required_flag_missing` check (lines 805-825) is unconditional and leaf-scoped. `SKILL.md:336-337` still uses the `{notation}` placeholder to sidestep it. |
| `license/cla` pending on PR #1164 | **Moot** | The PR landed: `a3a4da6` is an ancestor of `HEAD`. |
| `coderabbitai` review window may reopen and auto-review a later commit | **Moot** | The PR is merged; no further review is possible. |

## Out-of-scope and collateral

Nothing forbidden was built. See the "Out-of-scope items were respected" paragraph in *Correctness
review* for the file-by-file basis. One collateral item is worth recording: the PR body reproduces the
same false "exits `status: error` (non-zero)" claim as the report, so the falsehood is also in the
permanent commit message of `a3a4da6`.

## Method and coverage

**Checked, with the method:**

- Every deliverable's literal *Done when*, clause by clause, against the shipped source at
  `path:line`.
- The exit-code question by two independent live measurements (a driver forcing Guard 5, and the
  `verify` subcommand on a missing executor) plus a read of `main()`, `safe_main`, and the repo's
  `manage-contract.md`.
- The D1 test set by execution (`7 passed`).
- The D2 test by execution (green, 131.96s) and by **two in-process mutations** — a `children` strip
  (red, 509 refusals) and a total attribute strip (red, 622 refusals, help half silent). The second
  mutation is what converts "the help checks look tautological when I read the short-circuit" into a
  measurement.
- The D3 smoke by running all four of its commands live against a freshly regenerated executor.
- The pre-state at `a3a4da6^` for every "this did not exist before" claim.
- The residue items by reading the current analyzer, the marker registry, and git ancestry.
- Counts re-derived at the moment of writing: 158 registered scripts (152 marketplace + 6 local),
  114 derivable surfaces, 100 derived in a cold regeneration.

**Not checked, and why:**

- The full `./pw verify` suite (the report's "18966 passed, 14 skipped"). Out of scope per the audit
  brief; it takes many minutes. **UNVERIFIABLE** here.
- The report's run-time population figures (151/109/848 nodes/199 empty-flag nodes/70 empty-flag
  roots) and its "418 tests" suite size. These are historical measurements of a tree that has since
  grown; they are **UNVERIFIABLE** as stated and are not treated as defects.
- The originating incident's machine-local `.plan/` run log. The plan itself declares it unreachable
  and directs confirmation by reading the generator's success path instead; I did that.

**Environment caveat (stated because it affected one observation).** This clone was shared with
roughly a dozen concurrent pytest runs, each triggering its own executor bootstrap. My first D2 run
failed with `no .plan/execute-script.py` because the conftest bootstrap produced nothing. I attribute
that to two compounding causes, one environmental and one structural: host contention pushed the cold
derivation past the bootstrap's `timeout=120` (`test/conftest.py:123`), which is **below** the
generator's own default budget of `180.0` seconds (`generate_executor.py:798`); and the bootstrap's
`check=True` cannot detect a `status: error` generation at all. The timeout mismatch and the
undetectable failure are structural and reportable; the contention that exposed them is not. Once I
generated the executor by hand, D2 passed.
