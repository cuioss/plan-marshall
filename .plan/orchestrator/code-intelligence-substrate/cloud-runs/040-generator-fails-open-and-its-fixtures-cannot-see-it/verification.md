# Verification — 040-generator-fails-open-and-its-fixtures-cannot-see-it

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`; adversarially
re-reviewed at `38fd31d` on the same branch (see § Adversarial review)
**Landed as:** `a3a4da6` — `fix(tools-script-executor): fail-open regeneration guard + population-derived surface fixtures + required regen-and-dispatch smoke (#1164)`
**Overall verdict:** CONFIRMED WITH GAPS

All three deliverables are present in the tree and their central mechanisms work. Two of the plan's
literal *Done when* clauses are not met, and the run report states both as met:

- **D1 — "exits non-zero".** The refusal exits `0` with `status: error`. Measured live through the
  real CLI, twice, and again independently during adversarial review.
- **D2 — "⛔ publish the population size in the test's output".** The count is `print`ed, and the
  repo's own pytest `addopts` capture and discard it on a pass. Measured: a default
  `uv run python -m pytest <file>` passes in 10.04s and shows the number nowhere.

A third finding is a coverage overstatement rather than an unmet clause: **72.6% of D2's corpus is
surface-insensitive** — 1750 of its 2412 checks pass against a surface stripped of every attribute,
because the validator short-circuits on a help spelling before reading the surface. D2's literal
"fails when an attribute is stripped" clause *is* met (by the declared-flag half, for `flags` and
`children`); what is overstated is how much of the published population that clause covers.

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

  - **Exit-code probe re-taken during adversarial review, with nothing mocked.** A fake previous
    executor carrying one `SCRIPT_SURFACES` entry was staged in a temp dir and the real CLI run
    against the real registry with the derivation budget exhausted:
    `PLAN_TRACKED_CONFIG_DIR=<tmp> PM_SURFACE_BUDGET_SECONDS=0 python3 …/generate_executor.py generate --marketplace --marketplace-root .`
    → `surface-stats: scripts_registered=158 surfaces_derived=0 surfaces_reused=0 surfaces_not_derivable=158`,
    `status: error`, the full fail-open message, the four counts flattened into the TOON — and
    `EXIT=0`. The staged previous executor was byte-identical afterwards and no probe file
    survived, so "writes nothing / preserves the previous" is confirmed on the real path too.

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
  `check=True` — cannot see a `status: error` at all (with the Guard-5 reachability caveat recorded
  in *Correctness review* §1). The unconditional-line requirement is met for real regenerations but
  not for the dry-run and template-skew paths.

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
    refusals over `help_checks=1750 flag_invocation_checks=662`.
  - **Mutation sweep re-run under adversarial review, with the refusals PARTITIONED by half.** The
    original reading inferred the split arithmetically (`622 ≤ 662`), which does not follow — 622
    total is equally consistent with, say, 100 help refusals and 522 flag refusals. The sweep was
    therefore re-run through a standalone driver that replicates the test exactly but counts the two
    halves separately, once per serialized attribute. Every run: `registered=158 derivable=114
    help_checks=1750 flag_checks=662`.

    | `_node_to_dict` mutation | help refusals | flag refusals |
    |---|---|---|
    | none (baseline) | 0 | 0 |
    | drop `flags` | **0** | **622** |
    | drop `children` | **0** | **509** |
    | drop `required_flags` | 0 | 0 |
    | drop `flag_arity` | 0 | 0 |
    | drop `alias_of` | 0 | 0 |
    | drop `flags_confident` + `children_confident` | 0 | 0 |
    | return `{}` (every attribute gone) | **0** | **622** |

    So the conclusion the original inference reached for free is now **measured directly**: not one
    of the 1750 help checks refuses under any attribute strip, including a total one. The table also
    converts the audit's *read* of which attributes are covered (see G13) into a measurement: only
    `flags` and `children` redden anything.
  - The mechanism is visible in the source: `templates/execute-script.py.template:1088-1089` —
    `if _mentions_help(script_args): return None` — short-circuits before any surface content is read,
    and the only preceding surface access (`_surface_for`, lines 800-809 and 1078-1080) returns `None`
    ⇒ "spawn" for a missing root. So no derivation defect whatsoever can redden a help check.
  - Publication visibility: `pyproject.toml:110` sets `addopts = ["-v", "--tb=short", "--strict-markers", "--strict-config", "--durations=25"]`
    — no `-s`, no `-rA`. Under the repo's own invocation the `print` is captured and discarded on a
    green run; I had to pass `-rA` to see it. **Confirmed by execution under adversarial review:**
    `uv run python -m pytest test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py`
    with no extra flags → `1 passed in 10.04s` (warm cache), and the string `surface-guard population`
    appears nowhere in the output.
  - First attempt in this clone **failed outright**: `Failed: no .plan/execute-script.py under /home/user/plan-marshall`
    (test line 77). The root conftest bootstrap had run and produced nothing; see Correctness review.
- **Verdict:** **PARTIAL.** The test is genuinely population-derived, genuinely unsampled, correctly
  tiered, and measurably non-vacuous for the two attributes the flag half exercises — so the *Done
  when*'s "fails when an attribute is stripped from the derivation" clause is met. Two things are
  not. (i) The plan's "⛔ **Publish the population size** in the test's output" is defeated by the
  repo's own default capture — measured, not inferred. (ii) The deliverable's stated purpose — "fails
  the moment the derivation drops an attribute" — holds for `flags` and `children` only, and 1750 of
  the 2412 checks (72.6%) are surface-insensitive by construction. That is a coverage overstatement,
  not an unmet clause, but the test docstring (lines 21-22: "a derivation that drops an attribute
  fails a test here instead of shipping") and report finding F2 both assert the broader reading.

### D3 — required regenerate-and-dispatch live smoke

- **Required (plan):** "*Done when:* the smoke exists as a required step (not a reviewer's judgement)
  and **includes a help spelling and a leading top-level flag**."
- **Claimed (report):** a normative "Required regenerate-and-dispatch smoke" subsection naming both
  shapes; all commands self-exercised.
- **Found:** `marketplace/bundles/plan-marshall/skills/tools-script-executor/SKILL.md:293-360`.
  - Requiredness: "**MUST** be preceded by" (line 298); "a **required step, not a reviewer's
    discretion**" and "it is **not** satisfied by a green unit suite" (lines 299-300); "A change that
    has not run it clean is not ready to ship, regardless of the suite's colour" (lines 303-304); "The
    change does not ship on a red smoke" (lines 353-354). Unambiguous on a cold read.
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
  commands work verbatim against the current tree. Independently re-run under adversarial review:
  `manage-tasks --help` prints usage, `manage-tasks read -h` prints
  `usage: manage-tasks.py read [-h] --plan-id PLAN_ID --task-number TASK_NUMBER`, and the
  leading-`--project-dir` call returns `status: success` / `count: 2686` — the same three readings,
  taken independently.

## Correctness review

Read in full: `generate_executor.py` §§ surface-stats/derivation/guards/`cmd_generate`/`main`
(lines 795-1020, 1140-1450, 1920-2020, 2306-2425), `file_ops.py:1664-1700`,
`argparse_surface.py:380-450, 820-833`, `templates/execute-script.py.template:800-830, 1071-1140`,
`test/conftest.py:83-135`, the three touched test files, and `tools-script-executor/SKILL.md:230-360`.
Defects found:

1. **The refusal exits 0 — the fail-open guard is invisible to any exit-code consumer.**
   `generate_executor.py:2306-2419` — `main()` ends `return 0` with no status branch. Measured above,
   three times including once through the unmocked CLI: the guard trips, prints its stats line and
   error, and the process exits `0`. **The consequence is live in this repository:**
   `test/conftest.py:117-124` bootstraps the executor with
   `subprocess.run([... 'generate'], check=True, timeout=120)` — `check=True` is the *only* failure
   detection it has, nothing afterwards re-checks that the executor now exists, and `check=True`
   can never fire on **any** `status: error` the generator returns. The bootstrap then falls through
   silently with no executor written. This is structurally the same shape the plan set out to close
   ("a green regeneration that quietly stripped the whole set would leave the guard inert while every
   signal reads healthy"), relocated from the generator to its consumer.
   ⚠ **Corrected in adversarial review:** the refusal this bootstrap is blind to is *not* Guard 5's.
   `_ensure_executor_present` returns early when the executor already exists
   (`test/conftest.py:94-96`), so it only ever invokes the generator with no previous executor on
   disk; `read_previous_surfaces` then returns `{}` (`generate_executor.py:993-994`) and Guard 5's
   `if previous_surfaces and …` predicate cannot be true. The blindness is real and covers the
   template-missing return and Guards 1-4 plus `cmd_generate`'s base-path error — but Guard 5 is
   precisely the one refusal it cannot hide, so the "fail-open shape relocated to the consumer"
   reading is rhetorically apt and mechanically wrong.

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

5. **Two stale guard-count enumerations survived the F4 sweep.**
   `marketplace/bundles/plan-marshall/skills/manage-config/standards/provisioning-fail-closed-audit.md:96`
   still reads "Runs **four** deterministic guards (format-version handshake, placeholder-residue,
   `py_compile` self-check, emitted-path provenance)". The fifth (fail-open) guard is absent from both
   the count and the enumeration. A whole-tree sweep for the phrase under adversarial review found a
   **second** site the first pass missed:
   `test/plan-marshall/tools-script-executor/test_generate_executor.py:1906` — "generate_executor()
   runs four deterministic guards on the substituted content BEFORE any write". That one is narrower
   (it heads the shape-guard test section, and Guard 5 does run before substitution rather than on
   the substituted content), but it carries the same stale count in the same words. F4 claimed to
   have corrected every statement the new guard falsified; both of these were missed.

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
| D1 guard | `test_generate_executor_behavior.py:372-393` (adversarial refusal), `:396-412` (empty-previous negative control), `:415-432` (derived-or-reused no-false-trip, parametrised), `test_generate_executor.py:2864-2894` (real-path total collapse, driven by a genuinely broken script) | **Proven red by mutation** (adversarial review): neutralising Guard 5's predicate to `if False and previous_surfaces and …` turned the 7-test selection into `2 failed, 5 passed` — `test_fail_open_guard_refuses_zero_surfaces_against_nonempty_previous` reporting `- error / + success`, exactly the pre-guard behaviour the pre-state at `a3a4da6^` carried. |
| D1 stats line | `test_generate_executor_behavior.py:435-462` asserts the line in the refusal **and** the success case; `:465-473` asserts every bucket is named; `:476-507` asserts the error-path flattening | **The plan's clause tested literally** (adversarial review): guarding the emission as `if surfaces_derived + surfaces_reused: print(...)` — i.e. emitting the line only when non-empty — turns the selection red (`1 failed, 6 passed`) on `assert 'surface-stats:' in ''`. So this is a test that would fail if the line were emitted only when non-empty, measured rather than argued. |
| D1 exit code | `test_generate_executor.py:225-259` — `test_verify_requires_executor`, `test_drift_requires_executor`, `test_paths_requires_executor` each subprocess the CLI and assert `returncode == 0` with the message "Expected exit 0 (error in TOON output)". No such test covers the **fail-open refusal** path. | ⚠ Non-vacuous for the paths they cover — and they pin the OPPOSITE of what the report claims. The suite's own pre-existing contract is exit 0 on an expected error; nobody reconciled the plan's "exits non-zero" clause against it. The gap is a missing assertion on the new path (G2), not an absent exit-code discipline. |
| D2 | `test_population_derived_surface_guard.py:127-210` | Proven red by mutation, twice independently: 509 refusals on a `children` strip, 622 on a `flags` strip. |
| D2 help half | same file, lines 177-182 | **Proven surface-insensitive by partitioned measurement.** Across eight mutations (baseline, six single-attribute strips, and a total strip), help refusals were **0** in every one. These 1750 checks can only detect a regression in `_mentions_help` or in the short-circuit's position — never a derivation defect. |
| D3 | none (documentation) | Verified by execution instead — the smoke was run twice, once per audit round; see D3 above. |

Mutations in the original round were applied **in-process** via throwaway pytest plugins under
`$TMPDIR/.../verify-040/`, never by editing tracked files, because ~13 concurrent pytest runs shared
this working tree at the time and an on-disk mutation would have corrupted them. The adversarial
round re-ran the D2 sweep the same way (a standalone driver patching `argparse_surface._node_to_dict`
in-process) and additionally mutated `generate_executor.py` on disk for the two D1 mutations — taken
only after confirming `ps` showed **0** concurrent pytest processes, from a byte snapshot under
`$TMPDIR/adv-040-mutsweep/`, restored by `cp` (never `git checkout`/`restore`/`stash`) and verified
by md5 (`07df38311e04f2826a551c8cedf9d8fa` before and after). `git status --porcelain` afterwards
lists no file this audit touched.

## Report accuracy

| Claim in `report-01.md` | Status | Correct value |
|---|---|---|
| D1: "⇒ `status: error`, **non-zero exit**, nothing written" (line 31) | **FALSE** | `status: error` at **exit 0**. Measured twice; `main()` returns 0 unconditionally, and `manage-contract.md:34-36` forbids anything else. |
| D1: "the stats line … rides both the refusal and the success return" (lines 33-35) | TRUE | Confirmed at `generate_executor.py:1358` and by the both-cases test. |
| D1: "The emission contract … is stated normatively on `format_surface_stats_line`, not as a code comment" (lines 35-37) | TRUE | `generate_executor.py:855-878`. |
| D1: "7 targeted tests pass" (line 38) | TRUE | Re-measured: `7 passed, 32 deselected`. |
| D1 self-exercise: "`surfaces_derived=2 surfaces_reused=107`" (line 39) | Historical, not re-derivable | Today's live regeneration: `surfaces_derived=100 surfaces_reused=0 surfaces_not_derivable=58` over 158 registered (cold cache, so nothing to reuse). |
| D2: "`registered=151 derivable=109 help_checks=1696 flag_invocation_checks=649`" (line 43) | Historical; tree has grown | Today: `registered=158 derivable=114 help_checks=1750 flag_invocation_checks=662` — eight independent adversarial-review runs, all identical. The report's figures are internally consistent (1696 help checks = 2 × the 848 nodes its claim table names), so they were true of its tree. Not a defect. |
| — (audit's own reading) | **Corrected** | The first audit round recorded a *clean* run at `help_checks=1770 flag_invocation_checks=672` and a *mutated* run at `1750/662`, and reported the spread as a range. Re-measurement pins 1750/662 across all eight runs. The 20/10 spread is 10 extra parser nodes, consistent with a concurrently-edited script in the shared tree changing one notation's derived surface between the two readings — the published population tracks working-tree state, so it is only comparable within a single tree state. |
| D2: "**Publishes the population count**" (line 46) | **OVERSTATED** | It `print`s it, but `pyproject.toml:110` addopts carry no `-s`/`-rA`, so on a green run the count is captured and discarded. Visible only when a reader already passes an extra flag. |
| D2: "stripping `children` … produced **498 refusals**, then reverted clean" (lines 47-49) | TRUE in substance | Reproduced: 509 refusals on today's larger population. |
| F2: "the test catches serializer (`to_dict`) strips … but not an upstream *parse-layer* strip nor a `required_flags` strip" (line 94) | **INCOMPLETE** | Measured per attribute (see the sweep table under D2): of the seven keys `_node_to_dict` serializes, only `flags` (622 refusals) and `children` (509) redden the test. `required_flags`, `flag_arity`, `alias_of`, `flags_confident` and `children_confident` each redden **nothing** — F2 discloses one of those five. And its 1750 help checks catch **no** strip of any kind. |
| F3: "guard count migrated four→five consistently" (line 95) | **FALSE** | Two sites still carry the old count: `manage-config/standards/provisioning-fail-closed-audit.md:96` ("four deterministic guards", enumerating only the shape guards) and `test/plan-marshall/tools-script-executor/test_generate_executor.py:1906` ("runs four deterministic guards on the substituted content"). In fairness to F3, its sentence sits inside a D3 cold-read row and may have been scoped to the diff; as written it is unqualified, and unqualified it is false. |
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
- The exit-code question by **three** independent live measurements (a driver forcing Guard 5; the
  `verify` subcommand on a missing executor; and, in adversarial review, the unmocked CLI against the
  real 158-script registry with `PM_SURFACE_BUDGET_SECONDS=0` and a staged one-surface previous)
  plus a read of `main()`, `safe_main`, and the repo's `manage-contract.md`.
- The D1 test set by execution (`7 passed`) and, in adversarial review, by **two on-disk mutations
  restored from a byte snapshot** — neutralising Guard 5 (2 failed) and making the stats line
  conditional on a non-empty emission (1 failed). Those two convert "structurally adversarial" into a
  measured red.
- The D2 test by execution (green, 131.96s cold under contention; 10.04s warm at repo defaults) and
  by **eight in-process mutations** — baseline, each of the six serialized attribute groups, and a
  total strip — with the refusals **partitioned into the help and declared-flag halves**, which is
  what makes "the help half is surface-insensitive" a measurement rather than an inference from a
  single total.
- The D3 smoke by running its commands live against the tree, twice, in two independent rounds.
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
- The report's **Reviewer participation** table (per-reviewer verdicts on PR #1164) and its cost
  section. Both are records of a past run's external environment — rate-limit windows in particular
  do not reproduce — and neither bears on a deliverable. Named here so the omission is visible rather
  than silent.

**Environment caveat (stated because it affected one observation).** This clone was shared with
roughly a dozen concurrent pytest runs, each triggering its own executor bootstrap. My first D2 run
failed with `no .plan/execute-script.py` because the conftest bootstrap produced nothing. I attribute
that to two compounding causes, one environmental and one structural: host contention pushed the cold
derivation past the bootstrap's `timeout=120` (`test/conftest.py:123`), which is **below** the
generator's own default budget of `180.0` seconds (`generate_executor.py:798`); and the bootstrap's
`check=True` cannot detect a `status: error` generation at all. The timeout mismatch and the
undetectable failure are structural and reportable; the contention that exposed them is not. Once I
generated the executor by hand, D2 passed.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | Every `path:line` in both documents was re-opened against the tree at `38fd31d`. All 15 gap citations resolve to what they claim, and every quoted line is verbatim — including the two in the merged commit message of `a3a4da6` (body lines 27 and 35), `manage-contract.md:34-36`, `file_ops.py:1674-1675`, `generate_executor.py:868 / :1366 / :1964-1965`, `SKILL.md:263-264`, `provisioning-fail-closed-audit.md:96`, `argparse_surface.py:433-444`, and `execute-script.py.template:1078-1089`. **No gap was found to be fabricated.** Three citations had drifted: `SKILL.md` "The change does not ship on a red smoke" is at 353-354, not 355; `report-01.md`'s D1 quote spans 30-32, not 30-31; `test_total_surface_collapse…` starts at 2864, not 2865. | Three line ranges corrected. No gap deleted. |
| A1 | False positives (mechanism) | **G1's central mechanism claim is unreachable.** `_ensure_executor_present` returns early when the executor already exists (`test/conftest.py:94-96`), so it only ever runs the generator with **no** previous executor; `read_previous_surfaces` then returns `{}` (`:993-994`) and Guard 5's `if previous_surfaces and …` cannot be true. The bootstrap is blind to every other expected error — template-missing, Guards 1-4, `cmd_generate`'s base-path error — but Guard 5 is the one refusal it *cannot* hide. | G1 rewritten: the blindness is re-argued over the six reachable refusal paths, with the Guard-5 narrowing stated explicitly so a fix plan is not sold the wrong story. Severity `high` kept — a failure detector that can never fire. *Correctness review* §1 and the D1 verdict paragraph carry the same caveat. |
| A2 | False negatives | D3 (the only CONFIRMED verdict) was re-verified by running all three dispatch shapes live: `--help` prints usage, `read -h` prints `usage: manage-tasks.py read [-h] --plan-id PLAN_ID --task-number TASK_NUMBER`, and the leading `--project-dir` call returns `status: success` / `count: 2686`. D1's substance was re-verified through the **unmocked CLI** (the first round used a mocked driver), which also confirmed "writes nothing, previous preserved" on the real path. A whole-tree sweep for the stale guard count found a **second** site the first round missed: `test_generate_executor.py:1906`. No shipped-code defect was found that is not already filed. | Second stale site added to *Correctness review* §5, to the F3 report-accuracy row, and to G7 (with a scoped remedy — the count there is right once narrowed to the shape guards). |
| A2 | False negatives (clause reading) | D2's literal *Done when* has three clauses; "fails when an attribute is stripped from the derivation" **is** met (measured: `flags` → 622 refusals, `children` → 509). The document's opening bullet presented the 72.6% tautology as the unmet clause, when the unmet clause is the ⛔ publication one. | Opening summary re-written to separate the two unmet clauses (D1 exit code, D2 publication) from the coverage overstatement; the D2 verdict paragraph restructured the same way. |
| A3 | Vacuous evidence | The first round's D1 non-vacuity was **argued structurally, not measured** ("Structurally adversarial: … which a guard-less generator answers with `status: success`"). Re-run as two on-disk mutations: neutralising Guard 5 → `2 failed, 5 passed` with `- error / + success`; making the stats line conditional on a non-empty emission → `1 failed, 6 passed` on `assert 'surface-stats:' in ''`. That second mutation tests the plan's clause *verbatim* ("a test that would fail if the line were emitted only when non-empty"). G12's capture claim was re-measured by an actual default-flags run rather than inferred from `addopts`. | Test-adequacy rows for the D1 guard and the D1 stats line replaced with measured red/green readings. Mutation protocol (byte snapshot to `$TMPDIR/adv-040-mutsweep/`, `cp` restore, md5 `07df38311e04f2826a551c8cedf9d8fa` before and after, `ps` showing 0 concurrent pytest runs) recorded beneath the table. |
| A4 | Counts and quotes | Re-derived at check time: 158 registered (152 marketplace + 6 local), 114 derivable, `help_checks=1750 flag_invocation_checks=662`, 622 / 509 refusals, `7 passed, 32 deselected`, `count: 2686`, `1 passed in 10.04s`, dry run `scripts_discovered: 158` beside `scripts_registered: 0`. All reproduce. **One inference was invalid:** "622 ≤ 662 ⇒ every refusal came from the declared-flag half" does not follow — 622 is equally consistent with a mixed split. The conclusion survives, but only because it was re-measured. **One worked example was wrong:** G12 said a shrink to 58 derivable "would pass unnoticed", but the floor is `158 // 2 = 79`, so 58 fails it; the real blind spot is a shrink to 79. | The `≤` inference replaced by a partitioned eight-row mutation table (help refusals are 0 in every row). G12's example corrected to 79. The first round's 1770/672 vs 1750/662 spread reconciled and explained in a new report-accuracy row. |
| A5 | Actionability | No "review X / consider Y / investigate Z" entries — every gap already named a path, a change and an observable *Done when*. Two were not executable as written: G1's *Done when* stubbed `generate_executor.generate_executor` in-process, which the bootstrap (a `subprocess.run`) cannot see; and G1's Action prescribed `toon_parser.parse_toon`, which is not importable at `test/conftest.py:135` because `_setup_marketplace_pythonpath()` does not run until `:186`. G7's *Done when* ("a whole-tree grep returns nothing") was unachievable given the second site. | G1's *Done when* re-anchored on the subprocess boundary; its Action given a second, import-free mechanism (re-check `executor_path.exists()`) and the sys.path constraint spelled out. G7's *Done when* re-stated as "exactly one hit, the scoped comment". |
| A6 | Severity and topic | Topics re-checked against owning surfaces — all nine correct, no change. Two severities off the calibration: **G9** was `medium` for a payload that publishes `scripts_registered: 0` against 158 registered scripts, which is "a measurement misreports" and "shipped behaviour is wrong" (both `high` triggers); **G15** was `low` for a guard that cannot fire on a real input class, and `low` is defined as report-only/cosmetic/harmless. Considered and left unchanged: G4 `low` (a code comment, its sibling G5 rated `medium` only because it inverts a *named* contract), G8 `low`, G11 `medium`, G12 `medium`. | G9 raised medium → high; G15 raised low → medium. Both carry the calibration reasoning in the entry. |
| A7 | Coverage | All three deliverables have their own section with the literal *Done when* quoted clause-by-clause; out-of-scope compliance is evidenced file-by-file from `git show --stat a3a4da6` (7 files; the forbidden template and `test_execute_script.py` untouched — re-confirmed); report accuracy has a per-claim table; the four declared residue items each have a status. No deliverable is silently unmentioned. The one omission was undeclared: the report's **Reviewer participation** table and cost section were neither checked nor listed as unchecked. | Both added to "Not checked, and why", with the reason (external-environment records that do not reproduce and bear on no deliverable). |
| A8 | Internal consistency | The overall verdict (CONFIRMED WITH GAPS) follows from two PARTIAL and one CONFIRMED. All 13 findings→gap mappings traced in both directions: §1→G1, §2→G3/G4/G5/G6, §3→G9, §4→G10, §5→G7, §6→G15, §7→deliberately no gap (in-contract, stated), D2 publication→G12, D2 tautology→G11, D2 docstring/F2→G13, D1 exit-code test→G2, report falsehood→G8, environment caveat→G14. No orphan gap, no unactioned finding. **One inconsistency:** the opening summary called the tautology an unmet *Done when* clause while the D2 section correctly treats it as a coverage overstatement. | Opening summary corrected (see A2). Nothing else changed. |

**Residual doubt:** the class F2 discloses and this audit could not reach — an **upstream parse-layer
strip** in `argparse_surface`, where truth and installed surface lose the attribute in lockstep, so no
mutation of the serializer can redden the test. Every mutation run here (both rounds) patches
`_node_to_dict`, which is by construction downstream of that class; a further round would need the
live script's own `--help` as an independent oracle. Secondarily, `./pw verify` was not run in either
round, so the report's "18966 passed, 14 skipped" remains unverified, and the D1/D2 mutation readings
were taken on a working tree carrying other agents' uncommitted edits — which is the most likely
explanation for the 1750-vs-1770 population spread between rounds and could in principle shift a
refusal count by a few.

**Verdict on the audit:** SOUND AFTER CORRECTION — every gap is real and every headline measurement
reproduces, but the HIGH gap's mechanism was mis-attributed to a guard the cited consumer cannot
reach, one central inference was arithmetically invalid (though its conclusion holds under direct
measurement), and two severities sat below the calibration.
